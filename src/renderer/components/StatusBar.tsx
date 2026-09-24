import React, { useEffect, useState } from 'react';
import { useTradingStore } from '../stores/trading-store';
import { getMarketStatus, syncMarketHolidaysFromAPI, MarketStatus } from '../utils/market-hours';

const StatusBar: React.FC = () => {
  const { auth, connectionStatus, agentState, dashboard } = useTradingStore();
  const pnl = dashboard?.totalPnl || 0;

  const [marketStatus, setMarketStatus] = useState<MarketStatus>(() => getMarketStatus());

  useEffect(() => {
    // Initial sync from API
    syncMarketHolidaysFromAPI().then(() => {
      setMarketStatus(getMarketStatus());
    });

    // Refresh every 15 seconds
    const interval = setInterval(() => {
      setMarketStatus(getMarketStatus());
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  // If we are logged in, assume connected to SmartAPI unless explicitly disconnected
  const isConnected = auth.isLoggedIn && connectionStatus !== 'disconnected';

  return (
    <div className="h-8 bg-surface-950 border-t border-surface-800 flex items-center justify-between px-4 text-xs font-mono">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${auth.isCheckingAuth ? 'bg-warning-light animate-pulse' : isConnected ? 'bg-profit-light' : 'bg-loss-light'}`} />
          <span className="text-surface-300 capitalize">{auth.isCheckingAuth ? 'checking session...' : isConnected ? 'connected' : 'disconnected'}</span>
        </div>
        <div className={marketStatus.isOpen ? 'text-profit-light font-semibold' : marketStatus.reason === 'HOLIDAY' ? 'text-warning-light font-semibold' : 'text-surface-400'}>
          Market: {marketStatus.isOpen ? 'OPEN' : marketStatus.reason === 'HOLIDAY' ? `CLOSED (${marketStatus.holidayName})` : marketStatus.displayText}
        </div>
      </div>
      <div className="flex items-center gap-2 text-surface-400">
        Agent Status: <span className="text-white">
          {!agentState.running ? 'STOPPED' : agentState.status === 'idle' ? 'SCANNING' : agentState.status.toUpperCase()}
        </span>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-surface-400">Balance:</span>
          <span className="font-bold text-profit-light">
            ₹{(dashboard?.availableMargin || 0).toFixed(2)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-surface-400">Today's P&L:</span>
          <span className={`font-bold ${pnl >= 0 ? 'text-profit-light' : 'text-loss-light'}`}>
            ₹{pnl.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default StatusBar;
