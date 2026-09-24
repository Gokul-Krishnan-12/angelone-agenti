import { useEffect } from 'react';
import { useTradingStore } from '../stores/trading-store';
import { usePaperTradingStore } from '../stores/paper-trading-store';
import * as IPC from '@shared/ipc-channels';
import { OrderRequest, SmartApiCredentials } from '@shared/types';

let globalListenersRegistered = false;
let globalLogsHydrated = false;

export const useSmartAPI = () => {
  const store = useTradingStore();

  useEffect(() => {
    if (!window.electronAPI) return;

    if (!globalListenersRegistered) {
      globalListenersRegistered = true;

      window.electronAPI.on(IPC.TICKER_TICK, (event: any, data: any) => {
        const item = data || event;
        if (item) {
          const symbol = item.tradingsymbol || item.symbol;
          const price = Number(item.lastPrice ?? item.last_price ?? item.ltp ?? 0);
          if (symbol) {
            useTradingStore.getState().updateTick(symbol, { ...item, lastPrice: price });
          }
          if (price > 0 && symbol) {
            usePaperTradingStore.getState().updateTickPrice(symbol, price);
          }
        }
      });

      window.electronAPI.on(IPC.AGENT_SIGNAL, (event: any, data: any) => {
        const sig = data || event;
        if (sig) {
          useTradingStore.getState().addSignal(sig);
          if (sig.tradingsymbol && window.electronAPI?.ticker?.subscribe) {
            const clean = sig.tradingsymbol.replace('-EQ', '').replace('NSE:', '').trim().toUpperCase();
            window.electronAPI.ticker.subscribe([clean as any]).catch(() => {});
          }
          usePaperTradingStore.getState().executePaperTradeFromSignal(sig);
        }
      });

      window.electronAPI.on(IPC.LOG_ENTRY, (event: any, data: any) => {
        const entry = (data && data.message) ? data : (event && event.message ? event : data);
        if (entry) {
          useTradingStore.getState().addLogEntry(entry);
        }
      });

      window.electronAPI.on(IPC.AGENT_STATE_UPDATE, (event: any, data: any) => {
        const st = data || event;
        if (st) {
          useTradingStore.getState().setAgentState(st);
        }
      });
    }

    const init = async () => {
      try {
        const authStat = await window.electronAPI?.invoke(IPC.AUTH_STATUS);
        if (authStat !== undefined && authStat !== null) {
          const isAuthed = typeof authStat === 'object' ? Boolean(authStat.isValid || authStat.is_valid) : Boolean(authStat);
          const creds = typeof authStat === 'object' && authStat.credentials ? authStat.credentials : undefined;
          store.setAuth({
            isLoggedIn: isAuthed,
            isCheckingAuth: false,
            ...(creds ? { credentials: creds } : {})
          });
          store.setConnectionStatus(isAuthed ? 'connected' : 'disconnected');
        } else {
          store.setAuth({ isLoggedIn: false, isCheckingAuth: false });
          store.setConnectionStatus('disconnected');
        }
        const agentStat = await window.electronAPI?.invoke(IPC.AGENT_STATUS);
        if (agentStat) {
          store.setAgentState({ running: agentStat.running, mode: agentStat.mode || 'confirm' });
        }
        const settings = await window.electronAPI?.invoke(IPC.SETTINGS_GET);
        if (settings) {
          if (settings.strategies) {
            const enabledStrats = Object.keys(settings.strategies).filter(
              (s) => settings.strategies[s]?.enabled
            );
            store.setAgentState({ enabledStrategies: enabledStrats });
          }
          store.setSettings(settings);

          // Synchronize global risk settings to Paper Trading sandbox
          if (settings.risk) {
            if (settings.risk.riskPerTrade) {
              usePaperTradingStore.getState().setRiskPerTrade(Number(settings.risk.riskPerTrade));
            }
            if (settings.risk.maxCapitalPerTrade) {
              usePaperTradingStore.getState().setMaxCapitalPerTrade(Number(settings.risk.maxCapitalPerTrade));
            }
            if (settings.risk.maxDailyTrades) {
              usePaperTradingStore.getState().setMaxDailyTrades(Number(settings.risk.maxDailyTrades));
            }
            if (settings.risk.pullbackEntryEnabled !== undefined) {
              usePaperTradingStore.getState().setPullbackEntryEnabled(Boolean(settings.risk.pullbackEntryEnabled));
            }
            const ci = settings.risk.candleInterval || settings.candleInterval;
            if (ci === '5minute' || ci === '15minute') {
              usePaperTradingStore.getState().setCandleInterval(ci);
            }
          }
        }
        if (authStat === true) {
          const summary = await window.electronAPI?.dashboard.summary({ force: false });
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

        // Retrieve and hydrate existing recent logs from Python backend so autonomous scan entries are always visible
        if (!globalLogsHydrated) {
          globalLogsHydrated = true;
          try {
            const recentLogs = await window.electronAPI?.log?.getAll();
            if (Array.isArray(recentLogs) && recentLogs.length > 0) {
              store.setActivityLog(recentLogs);
            }
          } catch (_) {}
        }
      } catch (e) {
        console.error('Init Error', e);
        store.setAuth({ isLoggedIn: false, isCheckingAuth: false });
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
        const quotes = await window.electronAPI.market.ltp(allOpenSymbols);
        if (quotes && typeof quotes === 'object') {
          for (const [sym, val] of Object.entries(quotes as Record<string, any>)) {
            const clean = sym.replace('NSE:', '').replace('-EQ', '');
            const price = Number(val.last_price ?? val.lastPrice ?? val.ltp ?? 0);
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
