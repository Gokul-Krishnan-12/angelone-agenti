import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Signal } from '@shared/types';
import { TELEGRAM_SEND_EXIT, TELEGRAM_SEND_SUMMARY } from '@shared/ipc-channels';

export interface PaperPosition {
  id: string;
  tradingsymbol: string;
  exchange: string;
  direction: 'BUY' | 'SELL';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  stopLoss: number;
  target: number;
  target1?: number;
  target2?: number;
  partialBooked?: boolean;
  originalQuantity?: number;
  strategy: string;
  entryTime: string;
  marginUsed: number;
  pnl: number;
  pnlPercent: number;
}

export interface PaperOrder {
  orderId: string;
  tradingsymbol: string;
  direction: 'BUY' | 'SELL';
  quantity: number;
  entryPrice: number;
  exitPrice?: number;
  status: 'OPEN' | 'TARGET_HIT' | 'STOPLOSS_HIT' | 'MANUAL_EXIT' | 'AUTO_SQUARE_OFF';
  strategy: string;
  pnl?: number;
  pnlPercent?: number;
  entryTime: string;
  exitTime?: string;
}

export interface PaperRejectedTrade {
  id: string;
  tradingsymbol: string;
  direction: 'BUY' | 'SELL';
  strategy: string;
  confidence: number;
  confluenceScore?: number;
  price: number;
  reason: string;
  timestamp: string;
}

export interface PaperLogEntry {
  id: string;
  timestamp: string;
  type: 'INFO' | 'SIGNAL' | 'EXECUTE' | 'TARGET' | 'STOPLOSS' | 'EXIT';
  message: string;
}

interface PaperTradingState {
  dummyBalance: number;
  initialCapital: number;
  isRunning: boolean;
  positions: PaperPosition[];
  orders: PaperOrder[];
  rejectedTrades: PaperRejectedTrade[];
  activityLog: PaperLogEntry[];
  maxCapitalPerTrade: number;
  maxDailyTrades: number;
  lastPaperSummaryDate: string | null;

  setDummyBalance: (amount: number) => void;
  setIsRunning: (running: boolean) => void;
  setMaxCapitalPerTrade: (amount: number) => void;
  setMaxDailyTrades: (amount: number) => void;
  resetAccount: (newCapital?: number) => void;
  executePaperTradeFromSignal: (signal: Signal) => boolean;
  updateTickPrice: (tradingsymbol: string, price: number) => void;
  manualSquareOff: (positionId: string) => void;
  autoSquareOffIntraday: () => boolean;
  sendDailyPaperSummary: (force?: boolean) => boolean;
  clearOrders: () => void;
  repairOrders: () => void;
  clearLogs: () => void;
  clearRejectedTrades: () => void;
  syncRunningStatus: () => Promise<void>;
  addLog: (type: PaperLogEntry['type'], message: string) => void;
}

export const isIndianMarketHours = (): boolean => {
  const now = new Date();
  const istString = now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' });
  const istDate = new Date(istString);
  const day = istDate.getDay();
  // 0 is Sunday, 6 is Saturday
  if (day === 0 || day === 6) return false;

  const hours = istDate.getHours();
  const minutes = istDate.getMinutes();
  const timeInMinutes = hours * 60 + minutes;

  const marketOpen = 9 * 60 + 15; // 09:15 IST
  const intradayCutoff = 15 * 60 + 15; // 15:15 IST (No intraday entries after 3:15 PM)

  return timeInMinutes >= marketOpen && timeInMinutes <= intradayCutoff;
};

export const usePaperTradingStore = create<PaperTradingState>()(
  persist(
    (set, get) => ({
      dummyBalance: 100000,
      initialCapital: 100000,
      isRunning: false,
      positions: [],
      orders: [],
      rejectedTrades: [],
      lastPaperSummaryDate: null,
      activityLog: [
        {
          id: 'init-1',
          timestamp: new Date().toISOString(),
          type: 'INFO',
          message: 'Paper Trading sandbox initialized. Real-market simulation with zero financial risk.'
        }
      ],
      maxCapitalPerTrade: 4000,
      maxDailyTrades: 8,

      setDummyBalance: (amount: number) => {
        const valid = Math.max(1000, Number(amount) || 100000);
        set({ dummyBalance: valid, initialCapital: valid });
        get().addLog('INFO', `Paper trading balance configured to ₹${valid.toLocaleString('en-IN')}`);
      },

      setIsRunning: (running: boolean) => {
        set({ isRunning: running });
        if (window.electronAPI?.paperTrade?.setStatus) {
          window.electronAPI.paperTrade.setStatus(running).catch(() => {});
        }
        get().addLog(
          'INFO',
          running
            ? '🚀 Paper trading agent STARTED. Watching live technical breakout signals.'
            : '⏸️ Paper trading agent STOPPED. Automated virtual order entry paused.'
        );
      },

      syncRunningStatus: async () => {
        try {
          if (window.electronAPI?.paperTrade?.getStatus) {
            const status = await window.electronAPI.paperTrade.getStatus();
            set({ isRunning: Boolean(status) });
          }
        } catch {
          // ignore
        }
      },

      setMaxCapitalPerTrade: (amount: number) => {
        set({ maxCapitalPerTrade: Math.max(1000, Number(amount) || 4000) });
      },

      setMaxDailyTrades: (amount: number) => {
        set({ maxDailyTrades: Math.max(1, Math.min(50, Number(amount) || 8)) });
      },

      resetAccount: (newCapital?: number) => {
        const capital = newCapital ?? get().initialCapital ?? 100000;
        set({
          dummyBalance: capital,
          initialCapital: capital,
          positions: [],
          orders: [],
          rejectedTrades: [],
          activityLog: [
            {
              id: `reset-${Date.now()}`,
              timestamp: new Date().toISOString(),
              type: 'INFO',
              message: `Simulator reset. Starting balance restored to ₹${capital.toLocaleString('en-IN')}.`
            }
          ]
        });
      },

      addLog: (type, message) => {
        const newEntry: PaperLogEntry = {
          id: `log-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
          timestamp: new Date().toISOString(),
          type,
          message
        };
        set((state) => ({
          activityLog: [newEntry, ...state.activityLog].slice(0, 100)
        }));
      },

      clearLogs: () => set({ activityLog: [] }),

      clearRejectedTrades: () => set({ rejectedTrades: [] }),

      executePaperTradeFromSignal: (signal: Signal) => {
        const state = get();
        const cleanSymbol = (signal.tradingsymbol || 'UNKNOWN').replace('-EQ', '').replace('NSE:', '').trim().toUpperCase();
        const entryPrice = Number(signal.entryPrice || (signal as any).price || 0);

        const recordRejection = (reason: string) => {
          const rejectedItem: PaperRejectedTrade = {
            id: `rej-${Date.now()}-${cleanSymbol}-${Math.random().toString(36).substring(2, 6)}`,
            tradingsymbol: cleanSymbol,
            direction: signal.direction === 'SELL' ? 'SELL' : 'BUY',
            strategy: signal.strategy || 'Multi-Strategy',
            confidence: Number(signal.confidence || 0),
            confluenceScore: Number(signal.confluenceScore || 0),
            price: entryPrice,
            reason,
            timestamp: new Date().toISOString()
          };
          set((s) => ({
            rejectedTrades: [rejectedItem, ...s.rejectedTrades].slice(0, 150)
          }));
          get().addLog('SIGNAL', `❌ Trade rejected for ${cleanSymbol}: ${reason}`);
        };

        if (!state.isRunning) {
          recordRejection('Simulation Paused (Start Paper Trading to execute)');
          return false;
        }

        // Gate simulated paper executions: No intraday trades before 09:15 or after 15:15 IST (Mon-Fri)
        if (!isIndianMarketHours()) {
          recordRejection('Outside Trading Window (Active 09:15–15:15 IST, Mon–Fri)');
          return false;
        }

        // High quality filter: require minimum confluence score of 3 independent families
        const confluenceScore = Number(signal.confluenceScore || 1);
        if (confluenceScore < 3) {
          recordRejection(`Confluence Too Low (${confluenceScore}/3 independent families required)`);
          return false;
        }

        const todayIst = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
        const todayOrders = state.orders.filter(
          (o) => o.entryTime && new Date(o.entryTime).toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' }) === todayIst
        );

        // Daily trade cap (8 to 10 trades per day to prevent overtrading and brokerage drain)
        const maxDailyTrades = state.maxDailyTrades || 8;
        if (todayOrders.length >= maxDailyTrades) {
          recordRejection(`Max Daily Trade Cap Reached (${todayOrders.length}/${maxDailyTrades} trades)`);
          return false;
        }

        // Anti-whipsaw cooldown: Max 1 trade per symbol per day
        const alreadyTradedToday = todayOrders.some(
          (o) => o.tradingsymbol === cleanSymbol || o.tradingsymbol === signal.tradingsymbol
        );
        if (alreadyTradedToday) {
          recordRejection('Symbol Cooldown: Max 1 trade per symbol per day');
          return false;
        }

        // Check if position already open for this symbol
        const alreadyOpen = state.positions.some(
          (p) => p.tradingsymbol === cleanSymbol || p.tradingsymbol === signal.tradingsymbol
        );
        if (alreadyOpen) {
          recordRejection('Position Already Open for this symbol');
          return false;
        }

        if (entryPrice <= 0) {
          recordRejection('Invalid Entry Price');
          return false;
        }

        // Position sizing: With 5x intraday leverage (20% margin)
        // Position value = margin * 5 -> quantity = (margin * 5) / price
        const marginToUse = Math.min(state.maxCapitalPerTrade, state.dummyBalance);
        if (marginToUse < 500) {
          recordRejection(`Insufficient Balance: ₹${state.dummyBalance.toLocaleString('en-IN')} available (min ₹500 required)`);
          return false;
        }

        const effectiveExposure = marginToUse * 5;
        const quantity = Math.max(1, Math.floor(effectiveExposure / entryPrice));
        const actualMarginUsed = (quantity * entryPrice) / 5;

        if (actualMarginUsed > state.dummyBalance) {
          recordRejection(`Required Margin (₹${Math.round(actualMarginUsed).toLocaleString('en-IN')}) exceeds available balance`);
          return false;
        }

        const posId = `paper-pos-${Date.now()}-${cleanSymbol}`;
        const orderId = `paper-ord-${Date.now()}-${cleanSymbol}`;
        const direction: 'BUY' | 'SELL' = signal.direction === 'SELL' ? 'SELL' : 'BUY';

        // Calculate default target/stoploss if not provided
        const target = signal.target > 0
          ? signal.target
          : direction === 'BUY'
            ? entryPrice * 1.03
            : entryPrice * 0.97;

        const stopLoss = signal.stopLoss > 0
          ? signal.stopLoss
          : direction === 'BUY'
            ? entryPrice * 0.985
            : entryPrice * 1.015;

        // Calculate Target 1 (1:2 R:R) & Target 2 for partial profit booking on asymmetric setups
        const riskDist = Math.abs(entryPrice - stopLoss);
        const rewardDist = Math.abs(target - entryPrice);
        const rrRatio = riskDist > 0 ? rewardDist / riskDist : 0;

        let target1: number | undefined;
        const target2 = target;
        // If high R:R (> 2.2), set Target 1 at 1:2 R:R and Target 2 at full target
        if (rrRatio > 2.2 && riskDist > 0) {
          target1 = direction === 'BUY'
            ? Math.round((entryPrice + riskDist * 2.0) * 100) / 100
            : Math.round((entryPrice - riskDist * 2.0) * 100) / 100;
        }

        const newPosition: PaperPosition = {
          id: posId,
          tradingsymbol: cleanSymbol,
          exchange: signal.exchange || 'NSE',
          direction,
          quantity,
          entryPrice,
          currentPrice: entryPrice,
          stopLoss,
          target,
          target1,
          target2,
          partialBooked: false,
          originalQuantity: quantity,
          strategy: signal.strategy,
          entryTime: new Date().toISOString(),
          marginUsed: actualMarginUsed,
          pnl: 0,
          pnlPercent: 0
        };

        const newOrder: PaperOrder = {
          orderId,
          tradingsymbol: cleanSymbol,
          direction,
          quantity,
          entryPrice,
          status: 'OPEN',
          strategy: signal.strategy,
          entryTime: new Date().toISOString()
        };

        set({
          dummyBalance: state.dummyBalance - actualMarginUsed,
          positions: [newPosition, ...state.positions],
          orders: [newOrder, ...state.orders]
        });

        // Auto-subscribe the new paper position to live ticker stream
        if (window.electronAPI?.ticker?.subscribe) {
          window.electronAPI.ticker.subscribe([cleanSymbol as any]);
        }

        get().addLog(
          'EXECUTE',
          `Virtual ${direction} executed: ${quantity} shares of ${cleanSymbol} @ ₹${entryPrice.toFixed(2)} [Target: ₹${target.toFixed(2)}, SL: ₹${stopLoss.toFixed(2)}] via ${signal.strategy}`
        );
        return true;
      },

      updateTickPrice: (tradingsymbol: string, price: number) => {
        if (!tradingsymbol || price <= 0) return;
        // Intraday cutoff: If past 3:15 PM IST, square off all open positions immediately
        if (get().autoSquareOffIntraday()) return;

        const cleanSymbol = tradingsymbol.replace('-EQ', '').replace('NSE:', '').trim().toUpperCase();
        const state = get();
        if (state.positions.length === 0) return;

        let balanceDelta = 0;
        const remainingPositions: PaperPosition[] = [];
        const updatedOrders = [...state.orders];
        const logsToAdd: { type: PaperLogEntry['type']; message: string }[] = [];

        for (const pos of state.positions) {
          const posClean = pos.tradingsymbol.replace('-EQ', '').replace('NSE:', '').trim().toUpperCase();
          if (posClean !== cleanSymbol) {
            remainingPositions.push(pos);
            continue;
          }

          let effectivePrice = price;
          // Defensive guard against paise anomaly (e.g. tick in paise ~100x entry price)
          if (pos.entryPrice > 0 && effectivePrice > pos.entryPrice * 20) {
            effectivePrice = Math.round((effectivePrice / 100) * 100) / 100;
          }

          const isBuy = pos.direction === 'BUY';
          const pnl = isBuy
            ? (effectivePrice - pos.entryPrice) * pos.quantity
            : (pos.entryPrice - effectivePrice) * pos.quantity;
          const pnlPercent = ((effectivePrice - pos.entryPrice) / pos.entryPrice) * 100 * (isBuy ? 1 : -1);

          let currentPos = { ...pos };

          // ── Check Target 1 (Partial Profit Booking) ───────────
          if (currentPos.target1 && !currentPos.partialBooked && currentPos.quantity >= 2) {
            const hitTarget1 = isBuy
              ? effectivePrice >= currentPos.target1
              : effectivePrice <= currentPos.target1;

            if (hitTarget1) {
              const exitQty = Math.floor(currentPos.quantity / 2);
              const partialPnl = isBuy
                ? (effectivePrice - currentPos.entryPrice) * exitQty
                : (currentPos.entryPrice - effectivePrice) * exitQty;

              // Brokerage safeguard: ensure partial profit >= ₹250 to justify extra transaction
              if (partialPnl >= 250 && exitQty >= 1) {
                const releasedMargin = (exitQty * currentPos.entryPrice) / 5;
                balanceDelta += releasedMargin + partialPnl;

                const remainingQty = currentPos.quantity - exitQty;
                currentPos = {
                  ...currentPos,
                  quantity: remainingQty,
                  marginUsed: Math.max(0, currentPos.marginUsed - releasedMargin),
                  stopLoss: currentPos.entryPrice, // Move SL to Breakeven!
                  target: currentPos.target2 || currentPos.target,
                  partialBooked: true
                };

                logsToAdd.push({
                  type: 'TARGET',
                  message: `🎯 PARTIAL TARGET 1 HIT: ${currentPos.tradingsymbol} hit ₹${effectivePrice.toFixed(2)}! Booked 50% (${exitQty} shares, +₹${partialPnl.toFixed(2)}). SL moved to Breakeven @ ₹${currentPos.entryPrice.toFixed(2)}.`
                });
              }
            }
          }

          const currentPnl = isBuy
            ? (effectivePrice - currentPos.entryPrice) * currentPos.quantity
            : (currentPos.entryPrice - effectivePrice) * currentPos.quantity;
          const currentPnlPercent = ((effectivePrice - currentPos.entryPrice) / currentPos.entryPrice) * 100 * (isBuy ? 1 : -1);

          // Check Target condition (Target 2 or full target)
          const targetHit = isBuy ? effectivePrice >= currentPos.target : effectivePrice <= currentPos.target;
          // Check Stop Loss condition (Breakeven SL if partial booked, else initial SL)
          const slHit = isBuy ? effectivePrice <= currentPos.stopLoss : effectivePrice >= currentPos.stopLoss;

          if (targetHit || slHit) {
            const exitReason: 'TARGET_HIT' | 'STOPLOSS_HIT' = targetHit ? 'TARGET_HIT' : 'STOPLOSS_HIT';
            balanceDelta += currentPos.marginUsed + currentPnl;

            // Update matching order
            const ordIdx = updatedOrders.findIndex((o) => o.tradingsymbol === currentPos.tradingsymbol && o.status === 'OPEN');
            if (ordIdx >= 0) {
              updatedOrders[ordIdx] = {
                ...updatedOrders[ordIdx],
                status: exitReason,
                exitPrice: effectivePrice,
                pnl: Math.round(currentPnl * 100) / 100,
                pnlPercent: Math.round(currentPnlPercent * 100) / 100,
                exitTime: new Date().toISOString()
              };
            }

            if (targetHit) {
              logsToAdd.push({
                type: 'TARGET',
                message: `🎯 TARGET HIT: ${currentPos.tradingsymbol} hit ₹${effectivePrice.toFixed(2)}! Virtual Profit: +₹${currentPnl.toFixed(2)} (+${currentPnlPercent.toFixed(2)}%)`
              });
            } else {
              const isBreakeven = currentPos.partialBooked && Math.abs(effectivePrice - currentPos.entryPrice) < currentPos.entryPrice * 0.002;
              logsToAdd.push({
                type: 'STOPLOSS',
                message: isBreakeven
                  ? `🛡 BREAKEVEN EXIT: ${currentPos.tradingsymbol} closed at ₹${effectivePrice.toFixed(2)} with zero loss on remaining runner.`
                  : `🛑 STOP LOSS HIT: ${currentPos.tradingsymbol} hit ₹${effectivePrice.toFixed(2)}. Virtual Loss: -₹${Math.abs(currentPnl).toFixed(2)} (${currentPnlPercent.toFixed(2)}%)`
              });
            }

            // Trigger Telegram exit notification
            const exitTradeData = {
              tradingsymbol: currentPos.tradingsymbol,
              direction: currentPos.direction,
              entryPrice: currentPos.entryPrice,
              exitPrice: effectivePrice,
              quantity: currentPos.quantity,
              pnl: Math.round(currentPnl * 100) / 100,
              pnlPercent: Math.round(currentPnlPercent * 100) / 100,
              exitReason: targetHit ? 'TARGET' : (currentPos.partialBooked ? 'BREAKEVEN' : 'STOPLOSS'),
              mode: 'Paper Trading'
            };
            if (window.electronAPI?.telegram?.sendExit) {
              window.electronAPI.telegram.sendExit(exitTradeData).catch(() => {});
            } else if (window.electronAPI?.invoke) {
              window.electronAPI.invoke(TELEGRAM_SEND_EXIT, { trade: exitTradeData }).catch(() => {});
            }
          } else {
            // Position stays open, update price and live MTM
            remainingPositions.push({
              ...currentPos,
              currentPrice: effectivePrice,
              pnl: Math.round(currentPnl * 100) / 100,
              pnlPercent: Math.round(currentPnlPercent * 100) / 100
            });
          }
        }

        if (balanceDelta !== 0 || remainingPositions.length !== state.positions.length) {
          set({
            dummyBalance: state.dummyBalance + balanceDelta,
            positions: remainingPositions,
            orders: updatedOrders
          });
          for (const l of logsToAdd) {
            get().addLog(l.type, l.message);
          }
        } else {
          // Just update positions with current price
          set({ positions: remainingPositions });
        }
      },

      manualSquareOff: (positionId: string) => {
        const state = get();
        const pos = state.positions.find((p) => p.id === positionId);
        if (!pos) return;

        const isBuy = pos.direction === 'BUY';
        const pnl = isBuy
          ? (pos.currentPrice - pos.entryPrice) * pos.quantity
          : (pos.entryPrice - pos.currentPrice) * pos.quantity;
        const pnlPercent = ((pos.currentPrice - pos.entryPrice) / pos.entryPrice) * 100 * (isBuy ? 1 : -1);

        const returnedBalance = pos.marginUsed + pnl;

        const updatedOrders = state.orders.map((o) => {
          if (o.tradingsymbol === pos.tradingsymbol && o.status === 'OPEN') {
            return {
              ...o,
              status: 'MANUAL_EXIT' as const,
              exitPrice: pos.currentPrice,
              pnl: Math.round(pnl * 100) / 100,
              pnlPercent: Math.round(pnlPercent * 100) / 100,
              exitTime: new Date().toISOString()
            };
          }
          return o;
        });

        set({
          dummyBalance: state.dummyBalance + returnedBalance,
          positions: state.positions.filter((p) => p.id !== positionId),
          orders: updatedOrders
        });

        get().addLog(
          'EXIT',
          `Manual square off: Closed ${pos.tradingsymbol} @ ₹${pos.currentPrice.toFixed(2)}. Realized P&L: ${pnl >= 0 ? '+' : ''}₹${pnl.toFixed(2)} (${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%)`
        );

        // Trigger Telegram exit notification
        const exitTradeData = {
          tradingsymbol: pos.tradingsymbol,
          direction: pos.direction,
          entryPrice: pos.entryPrice,
          exitPrice: pos.currentPrice,
          quantity: pos.quantity,
          pnl: Math.round(pnl * 100) / 100,
          pnlPercent: Math.round(pnlPercent * 100) / 100,
          exitReason: 'MANUAL',
          mode: 'Paper Trading'
        };
        if (window.electronAPI?.telegram?.sendExit) {
          window.electronAPI.telegram.sendExit(exitTradeData).catch(() => {});
        } else if (window.electronAPI?.invoke) {
          window.electronAPI.invoke(TELEGRAM_SEND_EXIT, { trade: exitTradeData }).catch(() => {});
        }
      },

      sendDailyPaperSummary: (force = false): boolean => {
        const state = get();
        const now = new Date();
        const todayIst = now.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });

        if (!force && state.lastPaperSummaryDate === todayIst) {
          return false;
        }

        // Filter paper orders placed today in IST
        const todayOrders = state.orders.filter((o) => {
          if (!o.entryTime) return false;
          const orderDate = new Date(o.entryTime).toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
          return orderDate === todayIst;
        });

        // Only dispatch the paper performance report if ANY paper trade was taken today
        if (todayOrders.length === 0) {
          if (!force) {
            set({ lastPaperSummaryDate: todayIst });
          }
          return false;
        }

        const totalTrades = todayOrders.length;
        const executedOrders = totalTrades * 2;
        const winningTrades = todayOrders.filter((o) => (o.pnl || 0) > 0).length;
        const losingTrades = todayOrders.filter((o) => (o.pnl || 0) < 0).length;
        const winRate = (winningTrades / totalTrades) * 100;
        const grossPnl = todayOrders.reduce((acc, o) => acc + (o.pnl || 0), 0);
        const brokerage = executedOrders * 20.0;
        const netPnl = grossPnl - brokerage;

        const payload = {
          totalTrades,
          executedOrders,
          winningTrades,
          losingTrades,
          winRate: Math.round(winRate * 10) / 10,
          grossPnl: Math.round(grossPnl * 100) / 100,
          brokerage: Math.round(brokerage * 100) / 100,
          netPnl: Math.round(netPnl * 100) / 100,
          realisedPnl: Math.round(netPnl * 100) / 100,
          endingBalance: Math.round(state.dummyBalance * 100) / 100,
          mode: 'Paper Trading'
        };

        if (window.electronAPI?.telegram?.sendSummary) {
          window.electronAPI.telegram.sendSummary(payload).catch(() => {});
        } else if (window.electronAPI?.invoke) {
          window.electronAPI.invoke(TELEGRAM_SEND_SUMMARY, { summary: payload }).catch(() => {});
        }

        set({ lastPaperSummaryDate: todayIst });
        get().addLog('INFO', `📊 Dispatched Daily Paper Session Performance Report to Telegram (${totalTrades} trades, Net: ₹${netPnl.toFixed(2)}).`);
        return true;
      },

      autoSquareOffIntraday: (): boolean => {
        const state = get();
        const now = new Date();
        const istString = now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' });
        const istDate = new Date(istString);
        const day = istDate.getDay();
        // Skip weekend checks
        if (day === 0 || day === 6) return false;

        const hours = istDate.getHours();
        const minutes = istDate.getMinutes();
        const timeInMinutes = hours * 60 + minutes;

        // NSE Intraday MIS auto square-off cutoff: 15:15 IST (3:15 PM)
        const autoSquareOffCutoff = 15 * 60 + 15;
        if (timeInMinutes < autoSquareOffCutoff) return false;

        let hasSquaredOff = false;

        if (state.positions.length > 0) {
          let balanceDelta = 0;
          const updatedOrders = [...state.orders];
          const logsToAdd: { type: PaperLogEntry['type']; message: string }[] = [];

          for (const pos of state.positions) {
            const isBuy = pos.direction === 'BUY';
            const effectiveExitPrice = (pos.currentPrice && pos.currentPrice > 0) ? pos.currentPrice : pos.entryPrice;
            const pnl = isBuy
              ? (effectiveExitPrice - pos.entryPrice) * pos.quantity
              : (pos.entryPrice - effectiveExitPrice) * pos.quantity;
            const pnlPercent = ((effectiveExitPrice - pos.entryPrice) / pos.entryPrice) * 100 * (isBuy ? 1 : -1);

            balanceDelta += pos.marginUsed + pnl;

            const ordIdx = updatedOrders.findIndex((o) => o.tradingsymbol === pos.tradingsymbol && o.status === 'OPEN');
            if (ordIdx >= 0) {
              updatedOrders[ordIdx] = {
                ...updatedOrders[ordIdx],
                status: 'AUTO_SQUARE_OFF',
                exitPrice: effectiveExitPrice,
                pnl: Math.round(pnl * 100) / 100,
                pnlPercent: Math.round(pnlPercent * 100) / 100,
                exitTime: new Date().toISOString()
              };
            }

            logsToAdd.push({
              type: 'EXIT',
              message: `⏰ 3:15 PM Intraday MIS Auto Square-Off: Closed ${pos.tradingsymbol} (${pos.direction}) @ ₹${effectiveExitPrice.toFixed(2)}. Realized P&L: ${pnl >= 0 ? '+' : ''}₹${pnl.toFixed(2)} (${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%)`
            });

            // Trigger Telegram exit notification
            const exitTradeData = {
              tradingsymbol: pos.tradingsymbol,
              direction: pos.direction,
              entryPrice: pos.entryPrice,
              exitPrice: effectiveExitPrice,
              quantity: pos.quantity,
              pnl: Math.round(pnl * 100) / 100,
              pnlPercent: Math.round(pnlPercent * 100) / 100,
              exitReason: 'INTRADAY_AUTO_SQUARE_OFF (3:15 PM Cutoff)',
              mode: 'Paper Trading'
            };
            if (window.electronAPI?.telegram?.sendExit) {
              window.electronAPI.telegram.sendExit(exitTradeData).catch(() => {});
            } else if (window.electronAPI?.invoke) {
              window.electronAPI.invoke(TELEGRAM_SEND_EXIT, { trade: exitTradeData }).catch(() => {});
            }
          }

          set({
            dummyBalance: state.dummyBalance + balanceDelta,
            positions: [],
            orders: updatedOrders
          });

          for (const l of logsToAdd) {
            get().addLog(l.type, l.message);
          }
          hasSquaredOff = true;
        }

        // Check and dispatch daily paper session performance report (if any trade taken today)
        get().sendDailyPaperSummary(false);

        return hasSquaredOff;
      },

      clearOrders: () => set({ orders: [] }),

      repairOrders: () => {
        set((state) => ({
          orders: state.orders.map(sanitizePaperOrder)
        }));
        get().autoSquareOffIntraday();
      }
    }),
    {
      name: 'paper-trading-storage',
      partialize: (state) => ({
        dummyBalance: state.dummyBalance,
        initialCapital: state.initialCapital,
        positions: state.positions,
        orders: state.orders,
        rejectedTrades: state.rejectedTrades,
        activityLog: state.activityLog,
        maxCapitalPerTrade: state.maxCapitalPerTrade,
        lastPaperSummaryDate: state.lastPaperSummaryDate
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Sync running status with Electron main process so state survives page reloads
          if (window.electronAPI?.paperTrade?.getStatus) {
            window.electronAPI.paperTrade.getStatus().then((running) => {
              state.isRunning = Boolean(running);
            }).catch(() => {
              state.isRunning = false;
            });
          } else {
            state.isRunning = false;
          }
          if (Array.isArray(state.orders)) {
            state.orders = state.orders.map(sanitizePaperOrder);
          }
          if (typeof state.autoSquareOffIntraday === 'function') {
            state.autoSquareOffIntraday();
          }
        }
      }
    }
  )
);

export const sanitizePaperOrder = (o: PaperOrder): PaperOrder => {
  // If exitPrice is corrupted by paise (> 20x entryPrice), divide by 100
  if (o.exitPrice && o.entryPrice && o.exitPrice > o.entryPrice * 20) {
    const correctedExit = Math.round((o.exitPrice / 100) * 100) / 100;
    const isBuy = o.direction === 'BUY';
    const pnl = isBuy
      ? (correctedExit - o.entryPrice) * o.quantity
      : (o.entryPrice - correctedExit) * o.quantity;
    const pnlPercent = ((correctedExit - o.entryPrice) / o.entryPrice) * 100 * (isBuy ? 1 : -1);
    return {
      ...o,
      exitPrice: correctedExit,
      pnl: Math.round(pnl * 100) / 100,
      pnlPercent: Math.round(pnlPercent * 100) / 100
    };
  }
  return o;
};
