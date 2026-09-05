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
      if (data && data.tradingsymbol) {
        store.updateTick(data.tradingsymbol, data);
        if (data.lastPrice) {
          usePaperTradingStore.getState().updateTickPrice(data.tradingsymbol, data.lastPrice);
        }
      }
    });
    const unsubSignal = window.electronAPI.on(IPC.AGENT_SIGNAL, (event: any, data: any) => {
      store.addSignal(data);
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
          const summary = await window.electronAPI?.dashboard.summary();
          if (summary) {
            store.setDashboard(summary);
          }
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
        const summary = await window.electronAPI?.dashboard.summary();
        if (summary) {
          store.setDashboard(summary);
        }
      } catch (e) {
        // Background summary poll error ignored
      } finally {
        isPolling = false;
      }
    }, 10000);

    return () => {
      clearInterval(summaryInterval);
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

export const useKiteAPI = useSmartAPI;
