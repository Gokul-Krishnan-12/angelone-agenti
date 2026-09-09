import { useEffect } from 'react';
import { useTradingStore } from '../stores/trading-store';
import { usePaperTradingStore } from '../stores/paper-trading-store';
import * as IPC from '@shared/ipc-channels';
import { OrderRequest, SmartApiCredentials } from '@shared/types';

export const useSmartAPI = () => {
  const store = useTradingStore();

  useEffect(() => {
    if (!window.electronAPI) return;

    const unsubTick = window.electronAPI.on(IPC.TICKER_TICK, (event: any, data: any) => {
      if (data) {
        const symbol = data.tradingsymbol || data.symbol;
        const price = Number(data.lastPrice ?? data.last_price ?? data.ltp ?? 0);
        if (symbol) {
          store.updateTick(symbol, { ...data, lastPrice: price });
        }
        if (price > 0 && symbol) {
          usePaperTradingStore.getState().updateTickPrice(symbol, price);
        }
      }
    });
    const unsubSignal = window.electronAPI.on(IPC.AGENT_SIGNAL, (event: any, data: any) => {
      store.addSignal(data);
      if (data?.tradingsymbol && window.electronAPI?.ticker?.subscribe) {
        const clean = data.tradingsymbol.replace('-EQ', '').replace('NSE:', '').trim().toUpperCase();
        window.electronAPI.ticker.subscribe([clean as any]).catch(() => {});
      }
      usePaperTradingStore.getState().executePaperTradeFromSignal(data);
    });
    const unsubLog = window.electronAPI.on(IPC.LOG_ENTRY, (event: any, data: any) => {
      store.addLogEntry(data);
    });
    const unsubAgentState = window.electronAPI.on(IPC.AGENT_STATE_UPDATE, (event: any, data: any) => {
      store.setAgentState(data);
    });

    const init = async () => {
      try {
        const authStat = await window.electronAPI?.invoke(IPC.AUTH_STATUS);
        if (authStat !== undefined) {
          store.setAuth({ isLoggedIn: authStat === true });
          store.setConnectionStatus(authStat === true ? 'connected' : 'disconnected');
        }
        const agentStat = await window.electronAPI?.invoke(IPC.AGENT_STATUS);
        if (agentStat) {
          store.setAgentState({ running: agentStat.running, mode: agentStat.mode || 'confirm' });
        }
        const settings = await window.electronAPI?.invoke(IPC.SETTINGS_GET);
        if (settings && settings.strategies) {
          const enabledStrats = Object.keys(settings.strategies).filter(
            (s) => settings.strategies[s]?.enabled
          );
          store.setAgentState({ enabledStrategies: enabledStrats });
          store.setSettings(settings);
        }
        if (authStat === true) {
          const summary = await window.electronAPI?.dashboard.summary({ force: true });
          if (summary) {
            store.setDashboard(summary);
          }
        }

        // Clean out stale signals persisted from previous sessions (older than 12 hours)
        const currentSignals = useTradingStore.getState().signals;
        if (currentSignals.length > 0) {
          const now = Date.now();
          const freshSignals = currentSignals.filter((s) => {
            if (!s.timestamp) return false;
            const diff = now - new Date(s.timestamp).getTime();
            return diff > 0 && diff < 12 * 60 * 60 * 1000;
          });
          if (freshSignals.length !== currentSignals.length) {
            useTradingStore.getState().setSignals(freshSignals);
          }
        }

        // Auto-subscribe any existing open paper positions to the ticker
        const openPaperPositions = usePaperTradingStore.getState().positions;
        if (openPaperPositions.length > 0 && window.electronAPI?.ticker?.subscribe) {
          const symsToSub = openPaperPositions.map((p) => p.tradingsymbol);
          window.electronAPI.ticker.subscribe(symsToSub as any).catch(() => {});
        }

        // Auto-subscribe any existing live open positions to the ticker
        const livePositions = useTradingStore.getState().positions.filter((p) => p.quantity !== 0);
        if (livePositions.length > 0 && window.electronAPI?.ticker?.subscribe) {
          const liveSyms = livePositions.map((p) => p.tradingsymbol);
          window.electronAPI.ticker.subscribe(liveSyms as any).catch(() => {});
        }

        // Auto-subscribe active signals to ticker
        const activeSignals = useTradingStore.getState().signals;
        if (activeSignals.length > 0 && window.electronAPI?.ticker?.subscribe) {
          const sigSyms = activeSignals.map((s) => s.tradingsymbol);
          window.electronAPI.ticker.subscribe(sigSyms as any).catch(() => {});
        }
      } catch (e) {
        console.error('Init Error', e);
      }
    };
    init();

    let isPolling = false;
    const summaryInterval = setInterval(async () => {
      if (isPolling) return;
      if (!useTradingStore.getState().auth.isLoggedIn) return;
      isPolling = true;
      try {
        const summary = await window.electronAPI?.dashboard.summary({ force: true });
        if (summary) {
          store.setDashboard(summary);
        }
      } catch (e) {
        // Background summary poll error ignored
      } finally {
        isPolling = false;
      }
    }, 10000);

    // Fallback periodic LTP poller for ALL open positions (live + paper) and active signals every 3 seconds
    let isRealtimeLtpPolling = false;
    const realtimeLtpInterval = setInterval(async () => {
      // Periodic check for 3:15 PM intraday auto-square-off for paper trading
      usePaperTradingStore.getState().autoSquareOffIntraday();

      if (isRealtimeLtpPolling) return;
      const paperPositions = usePaperTradingStore.getState().positions;
      const livePositions = useTradingStore.getState().positions.filter((p) => p.quantity !== 0);
      const activeSignals = useTradingStore.getState().signals;

      const allOpenSymbols = Array.from(
        new Set([
          ...(paperPositions?.map((p) => p.tradingsymbol) || []),
          ...(livePositions?.map((p) => p.tradingsymbol) || []),
          ...(activeSignals?.map((s) => s.tradingsymbol) || [])
        ])
      );
      if (allOpenSymbols.length === 0) return;
      if (!window.electronAPI?.market?.ltp) return;

      isRealtimeLtpPolling = true;
      try {
        const ltpData = await window.electronAPI.market.ltp(allOpenSymbols);
        if (ltpData && typeof ltpData === 'object') {
          for (const sym of allOpenSymbols) {
            const clean = sym.replace('-EQ', '').replace('NSE:', '').trim().toUpperCase();
            const val = ltpData[sym] || ltpData[clean] || ltpData[`NSE:${clean}`] || ltpData[`${clean}-EQ`];
            const price = Number(val?.lastPrice ?? val?.last_price ?? val?.ltp ?? (typeof val === 'number' ? val : 0));
            if (price > 0) {
              store.updateTick(clean, { ...val, lastPrice: price });
              usePaperTradingStore.getState().updateTickPrice(clean, price);
            }
          }
        }
      } catch (e) {
        // Fallback LTP polling error ignored
      } finally {
        isRealtimeLtpPolling = false;
      }
    }, 3000);

    const handleFocusSync = () => {
      if (useTradingStore.getState().auth.isLoggedIn && window.electronAPI?.dashboard?.summary) {
        window.electronAPI.dashboard.summary({ force: true }).then((summary: any) => {
          if (summary) store.setDashboard(summary);
        }).catch(() => {});
      }
    };
    window.addEventListener('focus', handleFocusSync);

    return () => {
      clearInterval(summaryInterval);
      clearInterval(realtimeLtpInterval);
      window.removeEventListener('focus', handleFocusSync);
      window.electronAPI?.removeAllListeners(IPC.TICKER_TICK);
      window.electronAPI?.removeAllListeners(IPC.AGENT_SIGNAL);
      window.electronAPI?.removeAllListeners(IPC.LOG_ENTRY);
      window.electronAPI?.removeAllListeners(IPC.AGENT_STATE_UPDATE);
    };
  }, []);

  const login = async (creds: SmartApiCredentials | any) => {
    try {
      const res = await window.electronAPI?.invoke(IPC.AUTH_LOGIN, creds);
      return res;
    } catch (e: any) {
      throw new Error(e.message);
    }
  };

  const logout = async () => {
    await window.electronAPI?.invoke(IPC.AUTH_LOGOUT);
    store.setAuth({ isLoggedIn: false });
    store.setConnectionStatus('disconnected');
  };

  const placeOrder = async (order: OrderRequest) => {
    return await window.electronAPI?.invoke(IPC.ORDERS_PLACE, order);
  };

  const cancelOrder = async (orderId: string) => {
    return await window.electronAPI?.invoke(IPC.ORDERS_CANCEL, orderId);
  };

  const startAgent = async (mode: string = 'confirm') => {
    return await window.electronAPI?.invoke(IPC.AGENT_START, { mode });
  };

  const stopAgent = async () => {
    return await window.electronAPI?.invoke(IPC.AGENT_STOP);
  };

  return { login, logout, placeOrder, cancelOrder, startAgent, stopAgent };
};
