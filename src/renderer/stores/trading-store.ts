import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  AuthState, Position, Order, Holding, Margins, AgentState,
  Signal, ActivityLogEntry, WatchlistItem, Tick, AppSettings, DashboardSummary
} from '@shared/types';

interface TradingState {
  auth: AuthState;
  positions: Position[];
  orders: Order[];
  holdings: Holding[];
  margins: Margins | null;
  agentState: AgentState;
  signals: Signal[];
  activityLog: ActivityLogEntry[];
  watchlist: WatchlistItem[];
  ticks: Record<string, Tick>;
  settings: AppSettings | null;
  dashboard: DashboardSummary | null;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';

  setAuth: (auth: Partial<AuthState>) => void;
  setPositions: (positions: Position[]) => void;
  setOrders: (orders: Order[]) => void;
  setHoldings: (holdings: Holding[]) => void;
  setMargins: (margins: Margins | null) => void;
  setAgentState: (state: Partial<AgentState>) => void;
  setSignals: (signals: Signal[]) => void;
  addSignal: (signal: Signal) => void;
  removeSignal: (id: string) => void;
  setActivityLog: (logs: ActivityLogEntry[]) => void;
  addLogEntry: (entry: ActivityLogEntry) => void;
  setWatchlist: (watchlist: WatchlistItem[]) => void;
  updateTick: (symbol: string, tick: Tick) => void;
  setSettings: (settings: AppSettings) => void;
  setDashboard: (dashboard: DashboardSummary) => void;
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
}

export const useTradingStore = create<TradingState>()(
  persist(
    (set) => ({
      auth: { isLoggedIn: false, credentials: null, loginUrl: null, error: null },
      positions: [],
      orders: [],
      holdings: [],
      margins: null,
      agentState: {
        running: false,
        mode: 'confirm',
        enabledStrategies: [],
        tradesToday: 0,
        signalsGenerated: 0,
        currentPnl: 0,
        maxDrawdownToday: 0,
        lastScanTime: null,
        status: 'idle',
        statusMessage: ''
      },
      signals: [],
      activityLog: [],
      watchlist: [],
      ticks: {},
      settings: null,
      dashboard: null,
      connectionStatus: 'disconnected',

      setAuth: (auth) => set((state) => ({ auth: { ...state.auth, ...auth } })),
      setPositions: (positions) => set({ positions }),
      setOrders: (orders) => set({ orders }),
      setHoldings: (holdings) => set({ holdings }),
      setMargins: (margins) => set({ margins }),
      setAgentState: (agentState) => set((state) => ({ agentState: { ...state.agentState, ...agentState } })),
      setSignals: (signals) => set({ signals }),
      addSignal: (signal) => set((state) => {
        const signalWithTime = {
          ...signal,
          timestamp: signal.timestamp || new Date().toISOString()
        };
        // Prevent duplicate signals from same strategy on same symbol
        const existingIdx = state.signals.findIndex(
          s => s.tradingsymbol === signalWithTime.tradingsymbol && s.strategy === signalWithTime.strategy
        );
        
        let newSignals = [...state.signals];
        if (existingIdx >= 0) {
          newSignals[existingIdx] = signalWithTime; // Update existing
        } else {
          newSignals = [signalWithTime, ...state.signals]; // Prepend new
        }
        
        // Keep max 50 signals in memory
        return { signals: newSignals.slice(0, 50) };
      }),
      removeSignal: (id) => set((state) => ({
        signals: state.signals.filter(s => s.id !== id)
      })),
      setActivityLog: (activityLog) => set({ activityLog }),
      addLogEntry: (entry) => set((state) => ({ activityLog: [entry, ...state.activityLog] })),
      setWatchlist: (watchlist) => set({ watchlist }),
      updateTick: (symbol, tick) => set((state) => {
        const cleanSymbol = symbol.replace('-EQ', '').replace('NSE:', '').trim().toUpperCase();
        const tickAny = tick as any;
        const price = Number(tick.lastPrice ?? tickAny?.last_price ?? tickAny?.ltp ?? 0);
        let updatedPositions = state.positions;

        if (price > 0 && state.positions.some((p) => p.quantity !== 0)) {
          updatedPositions = state.positions.map((p) => {
            const pClean = p.tradingsymbol.replace('-EQ', '').replace('NSE:', '').trim().toUpperCase();
            if (pClean === cleanSymbol && p.quantity !== 0) {
              const diff = p.quantity > 0 ? (price - p.averagePrice) : (p.averagePrice - price);
              const unrealised = Math.round(diff * Math.abs(p.quantity) * 100) / 100;
              const pnl = Math.round(((p.realised || 0) + unrealised) * 100) / 100;
              return {
                ...p,
                lastPrice: price,
                unrealised,
                pnl
              };
            }
            return p;
          });
        }

        return {
          ticks: { ...state.ticks, [symbol]: tick },
          positions: updatedPositions
        };
      }),
      setSettings: (settings) => set({ settings }),
      setDashboard: (dashboard) => set({ dashboard }),
      setConnectionStatus: (status) => set({ connectionStatus: status })
    }),
    {
      name: 'smartapi-trading-storage',
      partialize: (state) => ({
        auth: state.auth,
        activityLog: state.activityLog,
        signals: state.signals,
        watchlist: state.watchlist,
        settings: state.settings,
        agentState: {
          ...state.agentState,
          running: false,
          status: 'idle',
          statusMessage: ''
        }
      }),
      onRehydrateStorage: () => (state) => {
        if (state && Array.isArray(state.signals)) {
          const now = Date.now();
          state.signals = state.signals.filter((s) => {
            if (!s.timestamp) return false;
            const age = now - new Date(s.timestamp).getTime();
            return age > 0 && age < 12 * 60 * 60 * 1000;
          });
        }
      }
    }
  )
);
