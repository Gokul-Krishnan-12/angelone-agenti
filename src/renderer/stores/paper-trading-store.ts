import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Signal } from '@shared/types';

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
  status: 'OPEN' | 'TARGET_HIT' | 'STOPLOSS_HIT' | 'MANUAL_EXIT';
  strategy: string;
  pnl?: number;
  pnlPercent?: number;
  entryTime: string;
  exitTime?: string;
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
  activityLog: PaperLogEntry[];
  maxCapitalPerTrade: number;

  setDummyBalance: (amount: number) => void;
  setIsRunning: (running: boolean) => void;
  setMaxCapitalPerTrade: (amount: number) => void;
  resetAccount: (newCapital?: number) => void;
  executePaperTradeFromSignal: (signal: Signal) => boolean;
  updateTickPrice: (tradingsymbol: string, price: number) => void;
  manualSquareOff: (positionId: string) => void;
  clearLogs: () => void;
  addLog: (type: PaperLogEntry['type'], message: string) => void;
}

export const usePaperTradingStore = create<PaperTradingState>()(
  persist(
    (set, get) => ({
      dummyBalance: 100000,
      initialCapital: 100000,
      isRunning: false,
      positions: [],
      orders: [],
      activityLog: [
        {
          id: 'init-1',
          timestamp: new Date().toISOString(),
          type: 'INFO',
          message: 'Paper Trading sandbox initialized. Real-market simulation with zero financial risk.'
        }
      ],
      maxCapitalPerTrade: 20000,

      setDummyBalance: (amount: number) => {
        const valid = Math.max(1000, Number(amount) || 100000);
        set({ dummyBalance: valid, initialCapital: valid });
        get().addLog('INFO', `Paper trading balance configured to ₹${valid.toLocaleString('en-IN')}`);
      },

      setIsRunning: (running: boolean) => {
        set({ isRunning: running });
        get().addLog(
          'INFO',
          running
            ? '🚀 Paper trading agent STARTED. Watching live technical breakout signals.'
            : '⏸️ Paper trading agent STOPPED. Automated virtual order entry paused.'
        );
      },

      setMaxCapitalPerTrade: (amount: number) => {
        set({ maxCapitalPerTrade: Math.max(1000, Number(amount) || 20000) });
      },

      resetAccount: (newCapital?: number) => {
        const capital = newCapital ?? get().initialCapital ?? 100000;
        set({
          dummyBalance: capital,
          initialCapital: capital,
          positions: [],
          orders: [],
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

      executePaperTradeFromSignal: (signal: Signal) => {
        const state = get();
        if (!state.isRunning) return false;

        const cleanSymbol = signal.tradingsymbol.replace('-EQ', '');
        // Check if position already open for this symbol
        const alreadyOpen = state.positions.some(
          (p) => p.tradingsymbol === cleanSymbol || p.tradingsymbol === signal.tradingsymbol
        );
        if (alreadyOpen) return false;

        const entryPrice = signal.entryPrice || 100;
        if (entryPrice <= 0) return false;

        // Position sizing: With 5x intraday leverage (20% margin)
        // Position value = margin * 5 -> quantity = (margin * 5) / price
        const marginToUse = Math.min(state.maxCapitalPerTrade, state.dummyBalance);
        if (marginToUse < 500) {
          get().addLog('INFO', `Insufficient paper balance to take trade on ${signal.tradingsymbol}`);
          return false;
        }

        const effectiveExposure = marginToUse * 5;
        const quantity = Math.max(1, Math.floor(effectiveExposure / entryPrice));
        const actualMarginUsed = (quantity * entryPrice) / 5;

        if (actualMarginUsed > state.dummyBalance) return false;

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

        get().addLog(
          'EXECUTE',
          `Virtual ${direction} executed: ${quantity} shares of ${cleanSymbol} @ ₹${entryPrice.toFixed(2)} [Target: ₹${target.toFixed(2)}, SL: ₹${stopLoss.toFixed(2)}] via ${signal.strategy}`
        );
        return true;
      },

      updateTickPrice: (tradingsymbol: string, price: number) => {
        const cleanSymbol = tradingsymbol.replace('-EQ', '');
        const state = get();
        if (price <= 0 || state.positions.length === 0) return;

        let balanceDelta = 0;
        const remainingPositions: PaperPosition[] = [];
        const updatedOrders = [...state.orders];
        const logsToAdd: { type: PaperLogEntry['type']; message: string }[] = [];

        for (const pos of state.positions) {
          if (pos.tradingsymbol !== cleanSymbol && pos.tradingsymbol !== tradingsymbol) {
            remainingPositions.push(pos);
            continue;
          }

          const isBuy = pos.direction === 'BUY';
          const pnl = isBuy
            ? (price - pos.entryPrice) * pos.quantity
            : (pos.entryPrice - price) * pos.quantity;
          const pnlPercent = ((price - pos.entryPrice) / pos.entryPrice) * 100 * (isBuy ? 1 : -1);

          // Check Target condition
          const targetHit = isBuy ? price >= pos.target : price <= pos.target;
          // Check Stop Loss condition
          const slHit = isBuy ? price <= pos.stopLoss : price >= pos.stopLoss;

          if (targetHit || slHit) {
            const exitReason: 'TARGET_HIT' | 'STOPLOSS_HIT' = targetHit ? 'TARGET_HIT' : 'STOPLOSS_HIT';
            balanceDelta += pos.marginUsed + pnl;

            // Update matching order
            const ordIdx = updatedOrders.findIndex((o) => o.tradingsymbol === pos.tradingsymbol && o.status === 'OPEN');
            if (ordIdx >= 0) {
              updatedOrders[ordIdx] = {
                ...updatedOrders[ordIdx],
                status: exitReason,
                exitPrice: price,
                pnl: Math.round(pnl * 100) / 100,
                pnlPercent: Math.round(pnlPercent * 100) / 100,
                exitTime: new Date().toISOString()
              };
            }

            if (targetHit) {
              logsToAdd.push({
                type: 'TARGET',
                message: `🎯 TARGET HIT: ${pos.tradingsymbol} hit ₹${price.toFixed(2)}! Virtual Profit: +₹${pnl.toFixed(2)} (+${pnlPercent.toFixed(2)}%)`
              });
            } else {
              logsToAdd.push({
                type: 'STOPLOSS',
                message: `🛑 STOP LOSS HIT: ${pos.tradingsymbol} hit ₹${price.toFixed(2)}. Virtual Loss: -₹${Math.abs(pnl).toFixed(2)} (${pnlPercent.toFixed(2)}%)`
              });
            }
          } else {
            // Position stays open, update price and live MTM
            remainingPositions.push({
              ...pos,
              currentPrice: price,
              pnl: Math.round(pnl * 100) / 100,
              pnlPercent: Math.round(pnlPercent * 100) / 100
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
      }
    }),
    {
      name: 'paper-trading-storage'
    }
  )
);
