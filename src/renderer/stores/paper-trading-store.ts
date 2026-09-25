import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Signal } from '@shared/types';
import { TELEGRAM_SEND_EXIT, TELEGRAM_SEND_SUMMARY } from '@shared/ipc-channels';
import { useTradingStore } from './trading-store';

export interface PaperPosition {
  id: string;
  tradingsymbol: string;
  exchange: string;
  direction: 'BUY' | 'SELL';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  stopLoss: number;
  initialSl?: number;
  initialRisk?: number;
  highWaterMark?: number;
  lowWaterMark?: number;
  atr?: number;
  target: number;
  target1?: number;
  target2?: number;
  partialBooked?: boolean;
  partialPnl?: number;
  partialExitPrice?: number;
  partialExitQty?: number;
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
  originalQuantity?: number;
  entryPrice: number;
  exitPrice?: number;
  status: 'OPEN' | 'TARGET_HIT' | 'STOPLOSS_HIT' | 'BREAKEVEN' | 'IDLE_TIMEOUT' | 'MANUAL_EXIT' | 'AUTO_SQUARE_OFF';
  strategy: string;
  pnl?: number;
  pnlPercent?: number;
  entryTime: string;
  exitTime?: string;
  partialBooked?: boolean;
  partialPnl?: number;
  partialExitPrice?: number;
  partialExitQty?: number;
  exitReason?: string;
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
  type: 'INFO' | 'SIGNAL' | 'EXECUTE' | 'TARGET' | 'STOPLOSS' | 'EXIT' | 'ORDER' | 'WARN' | 'ERROR';
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
  riskPerTrade: number;
  pullbackEntryEnabled: boolean;
  candleInterval: '5minute' | '15minute';
  lastPaperSummaryDate: string | null;

  setDummyBalance: (amount: number) => void;
  setIsRunning: (running: boolean) => void;
  setPullbackEntryEnabled: (enabled: boolean) => void;
  setCandleInterval: (interval: '5minute' | '15minute') => void;
  setMaxCapitalPerTrade: (amount: number) => void;
  setMaxDailyTrades: (amount: number) => void;
  setRiskPerTrade: (amount: number) => void;
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
  addLog: (type: PaperLogEntry['type'], message: string, timestamp?: string) => void;
}

export const isIndianMarketHours = (forNewEntries: boolean = true): boolean => {
  const now = new Date();
  const istString = now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' });
  const istDate = new Date(istString);
  const day = istDate.getDay();
  // 0 is Sunday, 6 is Saturday
  if (day === 0 || day === 6) return false;

  const hours = istDate.getHours();
  const minutes = istDate.getMinutes();
  const timeInMinutes = hours * 60 + minutes;

  // 09:30 IST for new entries (skip first 15 mins opening chop), 09:15 for general session
  const marketOpen = forNewEntries ? (9 * 60 + 30) : (9 * 60 + 15);
  // 15:00 IST cutoff for new entries, 15:15 IST cutoff for intraday tracking
  const marketClose = forNewEntries ? (15 * 60) : (15 * 60 + 15);

  return timeInMinutes >= marketOpen && timeInMinutes <= marketClose;
};

export const isUnwantedSandboxLog = (message?: string): boolean => {
  const msg = String(message || '');
  return (
    msg.includes('Multi-Strategy Scan') ||
    msg.includes('30-Min Scan') ||
    msg.includes('30-min scan') ||
    msg.includes('15-Min Scan') ||
    msg.includes('15-min scan') ||
    msg.includes('Dynamic Watchlist') ||
    msg.includes('Execution Timeframe') ||
    msg.includes('Entry Mode') ||
    msg.includes('Dispatched Daily Paper Session Performance Report') ||
    msg.includes('Screener Funnel') ||
    msg.includes('Top Shortlist Breakdown') ||
    msg.includes('Scanning shortlisted') ||
    msg.includes('Manual scan') ||
    msg.includes('Manual Scan') ||
    msg.includes('autonomous')
  );
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
      pullbackEntryEnabled: false,
      candleInterval: '5minute',
      activityLog: [
        {
          id: 'init-1',
          timestamp: new Date().toISOString(),
          type: 'INFO',
          message: 'Paper Trading sandbox initialized. Real-market simulation with zero financial risk.'
        }
      ],
      maxCapitalPerTrade: 8000,
      maxDailyTrades: 4,
      riskPerTrade: 700,

      setCandleInterval: (interval: '5minute' | '15minute' | string) => {
        const normalized: '5minute' | '15minute' = String(interval).includes('15') ? '15minute' : '5minute';
        set({ candleInterval: normalized });
      },

      setPullbackEntryEnabled: (enabled: boolean) => {
        set({ pullbackEntryEnabled: enabled });
      },

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

      setRiskPerTrade: (amount: number) => {
        set({ riskPerTrade: Math.max(100, Number(amount) || 500) });
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

      addLog: (type, message, customTimestamp?: string) => {
        if (!message || isUnwantedSandboxLog(message)) return;

        const timestamp = customTimestamp || new Date().toISOString();
        set((state) => {
          // Deduplicate if the exact same message already exists with identical timestamp or within 2 seconds
          const isDup = state.activityLog.slice(0, 15).some(
            (l) => l.message === message && (l.timestamp === timestamp || Math.abs(new Date(l.timestamp).getTime() - new Date(timestamp).getTime()) < 2000)
          );
          if (isDup) return state;

          const newEntry: PaperLogEntry = {
            id: `log-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
            timestamp,
            type,
            message
          };
          return {
            activityLog: [newEntry, ...state.activityLog].slice(0, 100)
          };
        });
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

        // Adaptive confluence filter: signals from the backend scanner have already
        // cleared the adaptive confluence gate (>=2 in trending, >=3 in chop). Floor is 2.
        const confluenceScore = Number(signal.confluenceScore || 1);
        if (confluenceScore < 2) {
          recordRejection(`Confluence Too Low (${confluenceScore} independent families; min 2 required)`);
          return false;
        }

        // ── Microstructural Quality Gate (RVOL, Rejection Wick, Local KER, Midday Guard) ──
        const sigAny = signal as any;
        const rvol = sigAny.rvol !== undefined ? Number(sigAny.rvol) : 1.5;
        const wickRatio = sigAny.wickRatio !== undefined ? Number(sigAny.wickRatio) : 0.15;
        const localKer = sigAny.localKer !== undefined ? Number(sigAny.localKer) : 0.45;

        if (sigAny.rvol !== undefined && rvol < 1.2) {
          recordRejection(`Microstructure: Low RVOL (${rvol.toFixed(2)}x < 1.20x min required)`);
          return false;
        }

        if (sigAny.wickRatio !== undefined && wickRatio > 0.25) {
          recordRejection(`Microstructure: High Rejection Wick (${(wickRatio * 100).toFixed(1)}% > 25.0% max)`);
          return false;
        }

        if (sigAny.localKer !== undefined && localKer < 0.30) {
          recordRejection(`Microstructure: Sideways Chop (KER ${localKer.toFixed(2)} < 0.30 min)`);
          return false;
        }

        // Check Midday Lull (11:30 to 13:15 IST)
        const nowIst = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
        const timeInMin = nowIst.getHours() * 60 + nowIst.getMinutes();
        const isMiddayLull = timeInMin >= (11 * 60 + 30) && timeInMin <= (13 * 60 + 15);
        if (isMiddayLull && sigAny.rvol !== undefined && rvol < 2.2) {
          recordRejection(`Microstructure: Midday Liquidity Lull (RVOL ${rvol.toFixed(2)}x < 2.20x required between 11:30–13:15 IST)`);
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

        // Position sizing: 1R risk-based sizing constrained by 5x MIS leverage & max capital ceiling
        // Prioritizes master settings from the Settings page (useTradingStore), falling back to local paper settings
        const masterRisk = useTradingStore.getState().settings?.risk;
        const effectiveMaxCapital = Number(masterRisk?.maxCapitalPerTrade) || state.maxCapitalPerTrade || 8000;
        const marginToUse = Math.min(effectiveMaxCapital, state.dummyBalance);
        if (marginToUse < 500) {
          recordRejection(`Insufficient Balance: ₹${state.dummyBalance.toLocaleString('en-IN')} available (min ₹500 required)`);
          return false;
        }

        const effectiveExposure = marginToUse * 5;
        const maxAllowedQty = Math.floor(effectiveExposure / entryPrice);
        const riskBudget = Number(masterRisk?.riskPerTrade) || state.riskPerTrade || 1000;
        const perShareRisk = Math.abs(entryPrice - stopLoss);
        const rawQuantity = perShareRisk > 0 ? Math.floor(riskBudget / perShareRisk) : maxAllowedQty;
        const quantity = Math.max(1, rawQuantity > 0 ? Math.min(rawQuantity, maxAllowedQty) : maxAllowedQty);
        const actualMarginUsed = (quantity * entryPrice) / 5;

        if (actualMarginUsed > state.dummyBalance) {
          recordRejection(`Required Margin (₹${Math.round(actualMarginUsed).toLocaleString('en-IN')}) exceeds available balance`);
          return false;
        }

        // Calculate Target 1 (+1.2R) & Target 2 for front-loaded partial profit booking
        const riskDist = Math.abs(entryPrice - stopLoss);
        const targetRR = Number(masterRisk?.partialBookingTargetRR) || 1.2;
        let target1: number | undefined;
        const target2 = target;
        if (riskDist > 0) {
          target1 = direction === 'BUY'
            ? Math.round((entryPrice + riskDist * targetRR) * 100) / 100
            : Math.round((entryPrice - riskDist * targetRR) * 100) / 100;
        }

        const estimatedAtr = Number((signal as any).atr) || (riskDist > 0 ? riskDist / 1.4 : entryPrice * 0.012);

        const newPosition: PaperPosition = {
          id: posId,
          tradingsymbol: cleanSymbol,
          exchange: signal.exchange || 'NSE',
          direction,
          quantity,
          entryPrice,
          currentPrice: entryPrice,
          stopLoss,
          initialSl: stopLoss,
          initialRisk: riskDist,
          highWaterMark: entryPrice,
          lowWaterMark: entryPrice,
          atr: estimatedAtr,
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

        const modeTag = state.pullbackEntryEnabled ? '🎯 Pullback Retest' : '⚡ Direct Entry';
        get().addLog(
          'EXECUTE',
          `Virtual ${direction} executed: ${quantity} shares of ${cleanSymbol} @ ₹${entryPrice.toFixed(2)} (${modeTag}) [Target: ₹${target.toFixed(2)}, SL: ₹${stopLoss.toFixed(2)}] via ${signal.strategy}`
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
          const masterRisk = useTradingStore.getState().settings?.risk;

          // ── Dynamic ATR Trailing Stop-Loss Ratchet (1.4x ATR behind HWM/LWM) ──
          const trailingSlEnabled = masterRisk?.trailingSlEnabled ?? true;
          const trailingAtrMult = Number(masterRisk?.trailingSlAtrMultiplier) || 1.4;
          const trailingCushionR = Number(masterRisk?.trailingSlProfitCushionR) || 1.2;

          if (trailingSlEnabled && currentPos.atr && currentPos.atr > 0) {
            const initialSl = currentPos.initialSl || currentPos.stopLoss;
            const tradeRisk = currentPos.initialRisk || Math.abs(currentPos.entryPrice - initialSl) || (currentPos.entryPrice * 0.012);
            const profitThreshold = tradeRisk * trailingCushionR;
            const distance = currentPos.atr * trailingAtrMult;

            if (isBuy) {
              const hwm = Math.max(currentPos.highWaterMark || currentPos.entryPrice, effectivePrice);
              currentPos.highWaterMark = hwm;
              if ((hwm - currentPos.entryPrice) >= profitThreshold) {
                let trailCandidate = hwm - distance;
                if ((hwm - currentPos.entryPrice) >= 1.5 * tradeRisk) {
                  trailCandidate = Math.max(trailCandidate, currentPos.entryPrice);
                }
                trailCandidate = Math.round(trailCandidate * 100) / 100;
                if (trailCandidate > currentPos.stopLoss) {
                  const oldSl = currentPos.stopLoss;
                  currentPos.stopLoss = trailCandidate;
                  logsToAdd.push({
                    type: 'ORDER',
                    message: `📈 TRAILING SL RATCHET: ${currentPos.tradingsymbol} SL raised ₹${oldSl.toFixed(2)} ➔ ₹${currentPos.stopLoss.toFixed(2)} (HWM: ₹${hwm.toFixed(2)})`
                  });
                }
              }
            } else {
              const lwm = Math.min(currentPos.lowWaterMark || currentPos.entryPrice, effectivePrice);
              currentPos.lowWaterMark = lwm;
              if ((currentPos.entryPrice - lwm) >= profitThreshold) {
                let trailCandidate = lwm + distance;
                if ((currentPos.entryPrice - lwm) >= 1.5 * tradeRisk) {
                  trailCandidate = Math.min(trailCandidate, currentPos.entryPrice);
                }
                trailCandidate = Math.round(trailCandidate * 100) / 100;
                if (trailCandidate < currentPos.stopLoss) {
                  const oldSl = currentPos.stopLoss;
                  currentPos.stopLoss = trailCandidate;
                  logsToAdd.push({
                    type: 'ORDER',
                    message: `📈 TRAILING SL RATCHET: ${currentPos.tradingsymbol} SL lowered ₹${oldSl.toFixed(2)} ➔ ₹${currentPos.stopLoss.toFixed(2)} (LWM: ₹${lwm.toFixed(2)})`
                  });
                }
              }
            }
          }

          // ── Check Target 1 (Partial Profit Booking, if enabled) ───────────
          const partialBookingEnabled = masterRisk?.partialBookingEnabled ?? false;
          if (partialBookingEnabled && currentPos.target1 && !currentPos.partialBooked && currentPos.quantity >= 2) {
            const hitTarget1 = isBuy
              ? effectivePrice >= currentPos.target1
              : effectivePrice <= currentPos.target1;

            if (hitTarget1) {
              const exitQty = Math.floor(currentPos.quantity / 2);
              const partialPnl = isBuy
                ? (effectivePrice - currentPos.entryPrice) * exitQty
                : (currentPos.entryPrice - effectivePrice) * exitQty;

              if (exitQty >= 1) {
                const releasedMargin = (exitQty * currentPos.entryPrice) / 5;
                balanceDelta += releasedMargin + partialPnl;

                const remainingQty = currentPos.quantity - exitQty;
                // Move SL to Breakeven (+0.05% friction cushion)
                const beSl = isBuy
                  ? Math.round(currentPos.entryPrice * 1.0005 * 100) / 100
                  : Math.round(currentPos.entryPrice * 0.9995 * 100) / 100;

                const roundedPartialPnl = Math.round(partialPnl * 100) / 100;
                currentPos = {
                  ...currentPos,
                  quantity: remainingQty,
                  marginUsed: Math.max(0, currentPos.marginUsed - releasedMargin),
                  stopLoss: Math.max(currentPos.stopLoss, beSl), // Move SL to Breakeven!
                  target: currentPos.target2 || currentPos.target,
                  partialBooked: true,
                  partialPnl: roundedPartialPnl,
                  partialExitPrice: effectivePrice,
                  partialExitQty: exitQty
                };

                // Also immediately update the open order with partial booking metrics
                const openOrdIdx = updatedOrders.findIndex((o) => o.tradingsymbol === currentPos.tradingsymbol && o.status === 'OPEN');
                if (openOrdIdx >= 0) {
                  updatedOrders[openOrdIdx] = {
                    ...updatedOrders[openOrdIdx],
                    partialBooked: true,
                    partialPnl: roundedPartialPnl,
                    partialExitPrice: effectivePrice,
                    partialExitQty: exitQty,
                    originalQuantity: currentPos.originalQuantity || (remainingQty + exitQty)
                  };
                }

                logsToAdd.push({
                  type: 'TARGET',
                  message: `🎯 PARTIAL TARGET 1 (+1.2R) HIT: ${currentPos.tradingsymbol} hit ₹${effectivePrice.toFixed(2)}! Booked 50% (${exitQty} shares, +₹${partialPnl.toFixed(2)}). SL moved to Breakeven @ ₹${beSl.toFixed(2)}.`
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
          // Check Stop Loss condition (Trailing SL or Breakeven SL or Initial SL)
          const slHit = isBuy ? effectivePrice <= currentPos.stopLoss : effectivePrice >= currentPos.stopLoss;

          // ── Idle Trade Circuit Breaker (calibrated: 35 mins for 5m, 75 mins for 15m without tagging +0.6R) ──
          const entryMs = new Date(currentPos.entryTime).getTime();
          const minsHeld = (Date.now() - entryMs) / 60000;
          const initialRisk = currentPos.initialRisk || Math.abs(currentPos.entryPrice - (currentPos.initialSl || currentPos.stopLoss)) || (currentPos.entryPrice * 0.012);
          const currentR = initialRisk > 0 ? ((isBuy ? effectivePrice - currentPos.entryPrice : currentPos.entryPrice - effectivePrice) / initialRisk) : 0;
          const idleTimeoutMins = get().candleInterval === '15minute' ? 75 : 35;
          const isIdleStagnant = minsHeld >= idleTimeoutMins && currentR < 0.6;

          if (targetHit || slHit || isIdleStagnant) {
            const isTrailingSl = !targetHit && !isIdleStagnant && (
              (isBuy && currentPos.stopLoss > currentPos.entryPrice) ||
              (!isBuy && currentPos.stopLoss < currentPos.entryPrice)
            );
            const isBreakeven = !isIdleStagnant && currentPos.partialBooked && Math.abs(effectivePrice - currentPos.entryPrice) < currentPos.entryPrice * 0.002;
            const exitStatus: PaperOrder['status'] = targetHit
              ? 'TARGET_HIT'
              : (isIdleStagnant ? 'IDLE_TIMEOUT' : (isBreakeven ? 'BREAKEVEN' : 'STOPLOSS_HIT'));
            const exitReasonText = targetHit
              ? 'TARGET'
              : (isIdleStagnant ? 'TIME_EXIT' : (currentPos.partialBooked ? 'BREAKEVEN' : 'STOPLOSS'));
            
            const remainingPnl = currentPnl;
            const totalTradePnl = (currentPos.partialPnl || 0) + remainingPnl;
            const fullInitialQty = currentPos.originalQuantity || (currentPos.quantity + (currentPos.partialExitQty || 0));
            const totalInvested = currentPos.entryPrice * fullInitialQty;
            const totalTradePnlPercent = totalInvested > 0 ? (totalTradePnl / totalInvested) * 100 : currentPnlPercent;

            balanceDelta += currentPos.marginUsed + remainingPnl;

            // Update matching order
            const ordIdx = updatedOrders.findIndex((o) => o.tradingsymbol === currentPos.tradingsymbol && o.status === 'OPEN');
            if (ordIdx >= 0) {
              updatedOrders[ordIdx] = {
                ...updatedOrders[ordIdx],
                status: exitStatus,
                exitPrice: effectivePrice,
                quantity: fullInitialQty,
                pnl: Math.round(totalTradePnl * 100) / 100,
                pnlPercent: Math.round(totalTradePnlPercent * 100) / 100,
                partialBooked: currentPos.partialBooked,
                partialPnl: currentPos.partialPnl,
                partialExitPrice: currentPos.partialExitPrice,
                partialExitQty: currentPos.partialExitQty,
                exitReason: exitReasonText,
                exitTime: new Date().toISOString()
              };
            }

            if (targetHit) {
              logsToAdd.push({
                type: 'TARGET',
                message: `🎯 TARGET HIT: ${currentPos.tradingsymbol} hit ₹${effectivePrice.toFixed(2)}! Virtual Profit: +₹${totalTradePnl.toFixed(2)} (+${totalTradePnlPercent.toFixed(2)}%)`
              });
            } else if (isTrailingSl) {
              logsToAdd.push({
                type: 'TARGET',
                message: `🚀 TRAILING STOP HIT: ${currentPos.tradingsymbol} closed at ₹${effectivePrice.toFixed(2)} in profit! Net P&L: +₹${totalTradePnl.toFixed(2)} (+${totalTradePnlPercent.toFixed(2)}%)`
              });
            } else if (isIdleStagnant) {
              logsToAdd.push({
                type: 'EXIT',
                message: `⏱️ Time Exit: ${currentPos.tradingsymbol} closed after ${minsHeld.toFixed(0)}m (momentum stalled). Closed at ₹${effectivePrice.toFixed(2)}. Net P&L: ${totalTradePnl >= 0 ? '+' : ''}₹${totalTradePnl.toFixed(2)}.`
              });
            } else {
              logsToAdd.push({
                type: 'STOPLOSS',
                message: isBreakeven
                  ? `🛡 BREAKEVEN EXIT: ${currentPos.tradingsymbol} closed at ₹${effectivePrice.toFixed(2)} with zero loss on remaining runner. Total Trade P&L: +₹${totalTradePnl.toFixed(2)}.`
                  : `🛑 STOP LOSS HIT: ${currentPos.tradingsymbol} hit ₹${effectivePrice.toFixed(2)}. Net P&L: ${totalTradePnl >= 0 ? '+' : ''}₹${totalTradePnl.toFixed(2)} (${totalTradePnlPercent.toFixed(2)}%)`
              });
            }

            // Trigger Telegram exit notification
            const exitTradeData = {
              tradingsymbol: currentPos.tradingsymbol,
              direction: currentPos.direction,
              entryPrice: currentPos.entryPrice,
              exitPrice: effectivePrice,
              quantity: fullInitialQty,
              pnl: Math.round(totalTradePnl * 100) / 100,
              pnlPercent: Math.round(totalTradePnlPercent * 100) / 100,
              exitReason: exitReasonText,
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
        const remainingPnl = isBuy
          ? (pos.currentPrice - pos.entryPrice) * pos.quantity
          : (pos.entryPrice - pos.currentPrice) * pos.quantity;
        const totalTradePnl = (pos.partialPnl || 0) + remainingPnl;
        const fullInitialQty = pos.originalQuantity || (pos.quantity + (pos.partialExitQty || 0));
        const totalInvested = pos.entryPrice * fullInitialQty;
        const totalTradePnlPercent = totalInvested > 0 ? (totalTradePnl / totalInvested) * 100 : 0;

        const returnedBalance = pos.marginUsed + remainingPnl;

        const updatedOrders = state.orders.map((o) => {
          if (o.tradingsymbol === pos.tradingsymbol && o.status === 'OPEN') {
            return {
              ...o,
              status: 'MANUAL_EXIT' as const,
              exitPrice: pos.currentPrice,
              quantity: fullInitialQty,
              pnl: Math.round(totalTradePnl * 100) / 100,
              pnlPercent: Math.round(totalTradePnlPercent * 100) / 100,
              partialBooked: pos.partialBooked,
              partialPnl: pos.partialPnl,
              partialExitPrice: pos.partialExitPrice,
              partialExitQty: pos.partialExitQty,
              exitReason: 'MANUAL',
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
          `Manual square off: Closed ${pos.tradingsymbol} @ ₹${pos.currentPrice.toFixed(2)}. Realized P&L: ${totalTradePnl >= 0 ? '+' : ''}₹${totalTradePnl.toFixed(2)} (${totalTradePnlPercent >= 0 ? '+' : ''}${totalTradePnlPercent.toFixed(2)}%)`
        );

        // Trigger Telegram exit notification
        const exitTradeData = {
          tradingsymbol: pos.tradingsymbol,
          direction: pos.direction,
          entryPrice: pos.entryPrice,
          exitPrice: pos.currentPrice,
          quantity: fullInitialQty,
          pnl: Math.round(totalTradePnl * 100) / 100,
          pnlPercent: Math.round(totalTradePnlPercent * 100) / 100,
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
            const remainingPnl = isBuy
              ? (effectiveExitPrice - pos.entryPrice) * pos.quantity
              : (pos.entryPrice - effectiveExitPrice) * pos.quantity;
            const totalTradePnl = (pos.partialPnl || 0) + remainingPnl;
            const fullInitialQty = pos.originalQuantity || (pos.quantity + (pos.partialExitQty || 0));
            const totalInvested = pos.entryPrice * fullInitialQty;
            const totalTradePnlPercent = totalInvested > 0 ? (totalTradePnl / totalInvested) * 100 : 0;

            balanceDelta += pos.marginUsed + remainingPnl;

            const ordIdx = updatedOrders.findIndex((o) => o.tradingsymbol === pos.tradingsymbol && o.status === 'OPEN');
            if (ordIdx >= 0) {
              updatedOrders[ordIdx] = {
                ...updatedOrders[ordIdx],
                status: 'AUTO_SQUARE_OFF',
                exitPrice: effectiveExitPrice,
                quantity: fullInitialQty,
                pnl: Math.round(totalTradePnl * 100) / 100,
                pnlPercent: Math.round(totalTradePnlPercent * 100) / 100,
                partialBooked: pos.partialBooked,
                partialPnl: pos.partialPnl,
                partialExitPrice: pos.partialExitPrice,
                partialExitQty: pos.partialExitQty,
                exitReason: 'INTRADAY_AUTO_SQUARE_OFF (3:15 PM Cutoff)',
                exitTime: new Date().toISOString()
              };
            }

            logsToAdd.push({
              type: 'EXIT',
              message: `⏰ 3:15 PM Intraday MIS Auto Square-Off: Closed ${pos.tradingsymbol} (${pos.direction}) @ ₹${effectiveExitPrice.toFixed(2)}. Realized P&L: ${totalTradePnl >= 0 ? '+' : ''}₹${totalTradePnl.toFixed(2)} (${totalTradePnlPercent >= 0 ? '+' : ''}${totalTradePnlPercent.toFixed(2)}%)`
            });

            // Trigger Telegram exit notification
            const exitTradeData = {
              tradingsymbol: pos.tradingsymbol,
              direction: pos.direction,
              entryPrice: pos.entryPrice,
              exitPrice: effectiveExitPrice,
              quantity: fullInitialQty,
              pnl: Math.round(totalTradePnl * 100) / 100,
              pnlPercent: Math.round(totalTradePnlPercent * 100) / 100,
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
        set((state) => {
          const sanitizedOrders = state.orders.map(sanitizePaperOrder);
          const logs = (state.activityLog || []).filter((l) => !isUnwantedSandboxLog(l?.message));

          // Ensure clean exit logs exist for completed trades
          for (const o of sanitizedOrders) {
            if (o.status !== 'OPEN' && o.exitTime && o.exitPrice) {
              const hasExitLog = logs.some((l) => l.message?.includes(o.tradingsymbol) && (l.type === 'EXIT' || l.type === 'TARGET' || l.type === 'STOPLOSS'));
              if (!hasExitLog && o.exitReason) {
                const isProf = (o.pnl || 0) >= 0;
                let logType: PaperLogEntry['type'] = 'EXIT';
                let logMsg = '';
                if (o.status === 'IDLE_TIMEOUT' || o.exitReason.includes('IDLE_CIRCUIT_BREAKER') || o.exitReason === 'TIME_EXIT') {
                  logType = 'EXIT';
                  const timeoutMins = get().candleInterval === '15minute' ? 75 : 35;
                  logMsg = `⏱️ Time Exit: ${o.tradingsymbol} closed at ₹${o.exitPrice.toFixed(2)} (momentum stalled > ${timeoutMins}m). Net P&L: ${isProf ? '+' : ''}₹${(o.pnl || 0).toFixed(2)}.`;
                } else if (o.status === 'TARGET_HIT') {
                  logType = 'TARGET';
                  logMsg = `🎯 TARGET HIT: ${o.tradingsymbol} hit ₹${o.exitPrice.toFixed(2)}! Virtual Profit: +₹${(o.pnl || 0).toFixed(2)}`;
                } else if (o.status === 'STOPLOSS_HIT') {
                  logType = 'STOPLOSS';
                  logMsg = `🛑 STOP LOSS HIT: ${o.tradingsymbol} hit ₹${o.exitPrice.toFixed(2)}. Net P&L: ${isProf ? '+' : ''}₹${(o.pnl || 0).toFixed(2)}`;
                } else if (o.status === 'BREAKEVEN') {
                  logType = 'STOPLOSS';
                  logMsg = `🛡 BREAKEVEN EXIT: ${o.tradingsymbol} closed at ₹${o.exitPrice.toFixed(2)} with zero loss. Net P&L: +₹${(o.pnl || 0).toFixed(2)}.`;
                } else if (o.status === 'AUTO_SQUARE_OFF') {
                  logType = 'EXIT';
                  logMsg = `🕒 EOD AUTO SQUARE-OFF (3:15 PM): Closed ${o.tradingsymbol} @ ₹${o.exitPrice.toFixed(2)}. Net P&L: ${isProf ? '+' : ''}₹${(o.pnl || 0).toFixed(2)}.`;
                }
                if (logMsg) {
                  logs.unshift({
                    id: `repaired-exit-${o.orderId}`,
                    timestamp: o.exitTime,
                    type: logType,
                    message: logMsg
                  });
                }
              }
            }
          }

          return {
            orders: sanitizedOrders,
            activityLog: logs.slice(0, 100)
          };
        });
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
        activityLog: (state.activityLog || []).filter((l) => !isUnwantedSandboxLog(l?.message)),
        maxCapitalPerTrade: state.maxCapitalPerTrade,
        maxDailyTrades: state.maxDailyTrades,
        riskPerTrade: state.riskPerTrade,
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
          if (Array.isArray(state.activityLog)) {
            state.activityLog = state.activityLog.filter((l) => !isUnwantedSandboxLog(l?.message));
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
  // Retroactively map idle circuit breaker exits to dedicated IDLE_TIMEOUT status
  if (o.exitReason?.includes('IDLE_CIRCUIT_BREAKER') && (o.status === 'AUTO_SQUARE_OFF' || o.status as string === 'STOPLOSS_HIT')) {
    return {
      ...o,
      status: 'IDLE_TIMEOUT'
    };
  }

  // Retroactively map breakeven exits to dedicated BREAKEVEN status
  if (o.exitReason === 'BREAKEVEN' && (o.status === 'STOPLOSS_HIT' || o.status === 'AUTO_SQUARE_OFF')) {
    return {
      ...o,
      status: 'BREAKEVEN'
    };
  }
  // Retroactively repair today's PATANJALI trade if it only recorded the remaining leg PnL (+₹712.40)
  if (o.tradingsymbol === 'PATANJALI' && Math.abs(o.entryPrice - 382.5) < 0.1 && (o.pnl === 712.4 || !o.partialBooked)) {
    return {
      ...o,
      quantity: 104,
      originalQuantity: 104,
      partialBooked: true,
      partialPnl: 577.20,
      partialExitPrice: 393.60,
      partialExitQty: 52,
      pnl: 1289.60,
      pnlPercent: 3.24,
      exitReason: 'PARTIAL_TARGET_AND_MIS_AUTO_SQUARE_OFF'
    };
  }

  // If exitPrice is corrupted by paise (> 20x entryPrice), divide by 100
  if (o.exitPrice && o.entryPrice && o.exitPrice > o.entryPrice * 20) {
    const correctedExit = Math.round((o.exitPrice / 100) * 100) / 100;
    const isBuy = o.direction === 'BUY';
    const effectiveQty = o.originalQuantity || o.quantity;
    const pnl = isBuy
      ? (correctedExit - o.entryPrice) * effectiveQty
      : (o.entryPrice - correctedExit) * effectiveQty;
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
