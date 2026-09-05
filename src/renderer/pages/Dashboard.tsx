import React, { useState, useEffect, useRef } from 'react';
import { useTradingStore } from '../stores/trading-store';
import { useSmartAPI } from '../hooks/useSmartAPI';
import {
  Activity,
  RefreshCw,
  Play,
  Square,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  Cpu,
  Zap,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle
} from 'lucide-react';

const Dashboard: React.FC = () => {
  const {
    dashboard,
    positions,
    agentState,
    activityLog,
    auth,
    setDashboard,
    setPositions,
    setAgentState
  } = useTradingStore();

  const { startAgent, stopAgent } = useSmartAPI();
  const [refreshing, setRefreshing] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [lastSynced, setLastSynced] = useState<string>('Just now');
  const [positionTab, setPositionTab] = useState<'open' | 'all'>('open');
  const [exitConfirmSymbol, setExitConfirmSymbol] = useState<string | null>(null);

  const isFetchingRef = useRef(false);

  // Market open check (NSE 09:15 - 15:30 IST Mon-Fri)
  const isMarketOpen = () => {
    const now = new Date();
    const istOffset = 5.5 * 60 * 60 * 1000;
    const utc = now.getTime() + now.getTimezoneOffset() * 60000;
    const istTime = new Date(utc + istOffset);
    const day = istTime.getDay();
    const minutes = istTime.getHours() * 60 + istTime.getMinutes();
    if (day === 0 || day === 6) return false;
    return minutes >= 555 && minutes <= 930;
  };
  const marketOpen = isMarketOpen();

  const handleToggleAgent = async () => {
    try {
      if (agentState.running) {
        await stopAgent();
        setAgentState({ running: false });
      } else {
        await startAgent();
        setAgentState({ running: true });
      }
    } catch (e) {
      console.error('Failed to toggle agent from dashboard', e);
    }
  };

  const handleScanNow = async () => {
    try {
      setScanning(true);
      await window.electronAPI?.agent.scanNow();
    } catch (e) {
      console.error('Manual scan failed:', e);
    } finally {
      setTimeout(() => setScanning(false), 800);
    }
  };

  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      // Parallelize requests with force=true so SmartAPI fetches fresh live data
      const [summary, posResponse] = await Promise.all([
        window.electronAPI?.dashboard.summary({ force: true }),
        window.electronAPI?.portfolio.positions({ force: true })
      ]);
      if (summary) setDashboard(summary);
      if (posResponse && posResponse.net) {
        setPositions(posResponse.net);
      }
      setLastSynced(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch (err) {
      console.error('Failed to refresh dashboard:', err);
    } finally {
      setRefreshing(false);
    }
  };

  // Background non-blocking poll with guard
  useEffect(() => {
    const fetchData = async () => {
      if (isFetchingRef.current) return;
      isFetchingRef.current = true;
      try {
        const [summary, posResponse] = await Promise.all([
          window.electronAPI?.dashboard.summary(),
          window.electronAPI?.portfolio.positions()
        ]);
        if (summary) setDashboard(summary);
        if (posResponse && posResponse.net) {
          setPositions(posResponse.net);
        }
        setLastSynced(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
      } finally {
        isFetchingRef.current = false;
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 12000);
    return () => clearInterval(interval);
  }, [setDashboard, setPositions]);

  const handleExitPosition = async (symbol: string) => {
    try {
      const pos = positions.find((p) => p.tradingsymbol === symbol);
      if (!pos || pos.quantity === 0) return;
      
      const orderParams = {
        tradingsymbol: pos.tradingsymbol,
        exchange: pos.exchange || 'NSE',
        transactionType: pos.quantity > 0 ? 'SELL' : 'BUY',
        quantity: Math.abs(pos.quantity),
        orderType: 'MARKET',
        product: pos.product || 'INTRADAY',
        price: 0,
        triggerPrice: 0
      };
      
      await window.electronAPI?.orders.place(orderParams);
      setExitConfirmSymbol(null);
      // Refresh positions immediately
      handleRefresh();
    } catch (e) {
      console.error('Failed to exit position:', e);
      setExitConfirmSymbol(null);
    }
  };

  const openPositions = positions.filter((p) => p.quantity !== 0);
  const totalPnl = dashboard?.totalPnl || 0;
  const isPnlPositive = totalPnl >= 0;
  const availableCash = dashboard?.availableMargin || 0;
  const usedMargin = dashboard?.usedMargin || 0;
  const totalCapital = availableCash + usedMargin;
  const intradayBuyingPower = availableCash * 5; // 5x Angel One MIS leverage
  const pnlPct = totalCapital > 0 ? (totalPnl / totalCapital) * 100 : 0;
  const winRate = dashboard?.winRate || 0;
  const tradesToday = dashboard?.tradesToday || 0;
  const winningTrades = dashboard?.winningTrades || 0;
  const losingTrades = dashboard?.losingTrades || (tradesToday - winningTrades > 0 ? tradesToday - winningTrades : 0);

  return (
    <div className="p-6 space-y-6 h-full overflow-auto max-w-[1600px] mx-auto animate-fade-in">
      {/* ─── TOP COMMAND HEADER ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-1 border-b border-surface-800/80">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Trading Command Center</h1>
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-800 border border-surface-700 text-surface-300">
              <span className={`w-2 h-2 rounded-full ${auth.isLoggedIn ? 'bg-profit-light animate-pulse' : 'bg-loss-light'}`} />
              {auth.isLoggedIn ? 'Angel One Connected' : 'Disconnected'}
            </span>
          </div>
          <p className="text-xs text-surface-400 mt-1 flex items-center gap-2">
            <span>Market: <strong className={marketOpen ? 'text-profit-light' : 'text-surface-400'}>{marketOpen ? 'OPEN (Live)' : 'CLOSED (After Hours)'}</strong></span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock size={12} className="text-surface-500" />
              <span>Synced {lastSynced}</span>
            </span>
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleScanNow}
            disabled={scanning}
            className="flex items-center gap-2 px-3.5 py-2 bg-surface-800 hover:bg-surface-750 text-surface-200 hover:text-white border border-surface-700 rounded-xl text-xs font-semibold transition-all shadow-sm cursor-pointer disabled:opacity-50"
            title="Scan market universe for technical breakout setups"
          >
            <Zap size={14} className={scanning ? 'animate-bounce text-accent-light' : 'text-accent-light'} />
            <span>{scanning ? 'Scanning...' : 'Scan Now'}</span>
          </button>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 bg-surface-800 hover:bg-surface-750 text-surface-200 hover:text-white border border-surface-700 rounded-xl text-xs font-semibold transition-all shadow-sm cursor-pointer disabled:opacity-50"
            title="Fetch live balance and positions from Angel One"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin text-accent-light' : 'text-surface-400'} />
            <span>{refreshing ? 'Updating...' : 'Refresh'}</span>
          </button>

          <button
            onClick={handleToggleAgent}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md cursor-pointer ${
              agentState.running
                ? 'bg-loss-dark/90 hover:bg-loss text-white border border-loss/40 shadow-loss/20'
                : 'bg-profit-dark/90 hover:bg-profit text-white border border-profit/40 shadow-profit/20'
            }`}
          >
            {agentState.running ? (
              <>
                <Square size={13} fill="currentColor" />
                <span>Stop Agent</span>
              </>
            ) : (
              <>
                <Play size={13} fill="currentColor" />
                <span>Start Agent</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ─── TOP 4 METRICS CARDS ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Net P&L */}
        <div className={`p-5 rounded-2xl border backdrop-blur-md bg-surface-800/90 transition-all ${
          isPnlPositive ? 'border-profit/30 shadow-lg shadow-profit-dark/10' : 'border-loss/30 shadow-lg shadow-loss-dark/10'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-400">Total Net P&L</span>
            <div className={`flex items-center gap-1 text-xs font-mono font-bold px-2 py-0.5 rounded-full ${
              isPnlPositive ? 'bg-profit-dark/20 text-profit-light border border-profit/30' : 'bg-loss-dark/20 text-loss-light border border-loss/30'
            }`}>
              {isPnlPositive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              <span>{pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%</span>
            </div>
          </div>
          <div className={`text-3xl font-mono font-extrabold tracking-tight ${isPnlPositive ? 'text-profit-light' : 'text-loss-light'}`}>
            {isPnlPositive ? '+' : ''}₹{totalPnl.toFixed(2)}
          </div>
          <div className="flex items-center justify-between text-[11px] text-surface-400 mt-3 pt-2.5 border-t border-surface-700/60">
            <span>Realized: <strong className={dashboard?.realisedPnl && dashboard.realisedPnl >= 0 ? 'text-profit-light' : 'text-surface-300'}>₹{(dashboard?.realisedPnl || 0).toFixed(2)}</strong></span>
            <span>Unrealized: <strong className={dashboard?.unrealisedPnl && dashboard.unrealisedPnl >= 0 ? 'text-profit-light' : 'text-surface-300'}>₹{(dashboard?.unrealisedPnl || 0).toFixed(2)}</strong></span>
          </div>
        </div>

        {/* Metric 2: Live Capital & 5x Buying Power */}
        <div className="p-5 rounded-2xl border border-surface-700/80 bg-surface-800/90 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-surface-400">Available Capital</span>
              <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-accent/20 text-accent-light border border-accent/30">
                Angel Live
              </span>
            </div>
            <div className="text-3xl font-mono font-extrabold text-white tracking-tight">
              ₹{availableCash.toFixed(2)}
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-surface-700/60 flex items-center justify-between text-[11px]">
            <span className="text-surface-400 flex items-center gap-1">
              <Sparkles size={12} className="text-accent-light" />
              <span>5x Buying Power:</span>
            </span>
            <span className="font-mono font-bold text-accent-light">₹{intradayBuyingPower.toFixed(2)}</span>
          </div>
        </div>

        {/* Metric 3: Trade Performance & Win Rate */}
        <div className="p-5 rounded-2xl border border-surface-700/80 bg-surface-800/90 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-surface-400">Today's Win Rate</span>
              <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                winRate >= 50 ? 'bg-profit-dark/20 text-profit-light border-profit/30' : 'bg-surface-700 text-surface-300 border-surface-600'
              }`}>
                {winRate.toFixed(1)}%
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-mono font-extrabold text-white tracking-tight">{tradesToday}</span>
              <span className="text-xs text-surface-400 font-medium">trades executed</span>
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-surface-700/60 flex items-center justify-between text-[11px]">
            <span className="text-profit-light font-medium flex items-center gap-1">
              <CheckCircle2 size={12} /> {winningTrades} Won
            </span>
            <span className="text-loss-light font-medium flex items-center gap-1">
              <XCircle size={12} /> {losingTrades} Lost
            </span>
          </div>
        </div>

        {/* Metric 4: Agent & Strategy Engine */}
        <div className="p-5 rounded-2xl border border-surface-700/80 bg-surface-800/90 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-surface-400">Trading Agent</span>
              <span className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider ${
                agentState.running ? 'bg-profit-dark/20 text-profit-light border border-profit/30' : 'bg-surface-700 text-surface-400'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${agentState.running ? 'bg-profit-light animate-ping' : 'bg-surface-500'}`} />
                {agentState.running ? 'ACTIVE' : 'IDLE'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold text-white capitalize">{agentState.mode} Mode</div>
                <div className="text-xs text-surface-400">
                  {agentState.mode === 'auto' ? 'Auto Order Execution' : 'User Confirms Signals'}
                </div>
              </div>
              <div className="w-9 h-9 rounded-xl bg-surface-700/60 flex items-center justify-center text-accent-light border border-surface-600">
                <Cpu size={18} />
              </div>
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-surface-700/60 flex items-center justify-between text-[11px]">
            <span className="text-surface-400">Active Strategies</span>
            <span className="font-semibold text-white">20 TA Strategies</span>
          </div>
        </div>
      </div>

      {/* ─── MAIN CONTENT AREA (2-COLUMN LAYOUT) ────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT COLUMN: Open Positions & Live Universe (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* POSITIONS SECTION */}
          <div className="bg-surface-800/90 backdrop-blur-md rounded-2xl border border-surface-700/80 shadow-lg overflow-hidden">
            <div className="p-5 border-b border-surface-700/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold text-white">Open Positions</h2>
                <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-surface-700 text-surface-300">
                  {openPositions.length}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPositionTab('open')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                    positionTab === 'open' ? 'bg-surface-700 text-white' : 'text-surface-400 hover:text-white'
                  }`}
                >
                  Active Only
                </button>
                <button
                  onClick={() => setPositionTab('all')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                    positionTab === 'all' ? 'bg-surface-700 text-white' : 'text-surface-400 hover:text-white'
                  }`}
                >
                  All ({positions.length})
                </button>
              </div>
            </div>

            <div className="p-5">
              {(positionTab === 'open' ? openPositions : positions).length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-surface-700/50 flex items-center justify-center text-surface-500 mb-3 border border-surface-700">
                    <Activity size={26} className="opacity-60" />
                  </div>
                  <h3 className="text-base font-semibold text-white">No active positions</h3>
                  <p className="text-xs text-surface-400 max-w-sm mt-1">
                    The trading agent is actively scanning Nifty 50 constituents for breakout opportunities based on your 20 strategies.
                  </p>
                  <button
                    onClick={handleScanNow}
                    className="mt-4 px-4 py-1.5 bg-surface-700 hover:bg-surface-600 text-surface-200 hover:text-white rounded-lg text-xs font-medium transition-colors"
                  >
                    Trigger Market Scan
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(positionTab === 'open' ? openPositions : positions).map((p) => {
                    const isProf = (p.pnl || 0) >= 0;
                    const pnlPercent = p.averagePrice > 0 ? ((p.lastPrice - p.averagePrice) / p.averagePrice) * 100 * (p.quantity > 0 ? 1 : -1) : 0;
                    return (
                      <div
                        key={p.tradingsymbol}
                        className="bg-surface-900/60 rounded-xl p-4 border border-surface-700/70 hover:border-surface-600 transition-all flex flex-col justify-between space-y-3"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-white text-base">{p.tradingsymbol}</span>
                              <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-surface-800 text-surface-300 border border-surface-700">
                                {p.product || 'MIS'}
                              </span>
                            </div>
                            <span className="text-[11px] text-surface-400">{p.exchange || 'NSE'}</span>
                          </div>
                          <div className="text-right">
                            <div className={`text-base font-mono font-bold ${isProf ? 'text-profit-light' : 'text-loss-light'}`}>
                              {isProf ? '+' : ''}₹{(p.pnl || 0).toFixed(2)}
                            </div>
                            <div className={`text-[11px] font-mono ${isProf ? 'text-profit-light' : 'text-loss-light'}`}>
                              {pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-2 py-2 px-3 rounded-lg bg-surface-800/80 text-xs font-mono">
                          <div>
                            <span className="text-[10px] text-surface-400 block font-sans">Qty</span>
                            <span className={`font-bold ${p.quantity > 0 ? 'text-profit-light' : p.quantity < 0 ? 'text-loss-light' : 'text-surface-300'}`}>
                              {p.quantity > 0 ? `+${p.quantity}` : p.quantity}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-surface-400 block font-sans">Avg Price</span>
                            <span className="text-white">₹{p.averagePrice.toFixed(2)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-surface-400 block font-sans">LTP</span>
                            <span className="text-white">₹{p.lastPrice.toFixed(2)}</span>
                          </div>
                        </div>

                        {p.quantity !== 0 && (
                          <div className="pt-1 flex justify-end">
                            {exitConfirmSymbol === p.tradingsymbol ? (
                              <div className="flex items-center gap-2">
                                <span className="text-[11px] text-loss-light">Square off?</span>
                                <button
                                  onClick={() => handleExitPosition(p.tradingsymbol)}
                                  className="px-2.5 py-1 rounded bg-loss hover:bg-loss-dark text-white text-xs font-bold transition-colors"
                                >
                                  Confirm Exit
                                </button>
                                <button
                                  onClick={() => setExitConfirmSymbol(null)}
                                  className="px-2 py-1 rounded bg-surface-700 text-surface-300 text-xs"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setExitConfirmSymbol(p.tradingsymbol)}
                                className="px-3 py-1 rounded-lg text-xs font-medium text-loss-light hover:bg-loss-dark/20 border border-loss/30 transition-colors"
                              >
                                Square Off
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Live Activity Feed (1 Col) */}
        <div className="space-y-6">
          <div className="bg-surface-800/90 backdrop-blur-md rounded-2xl border border-surface-700/80 shadow-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-accent-light" />
                <h2 className="text-base font-bold text-white">Live Activity Stream</h2>
              </div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-surface-700 text-surface-300">
                Real-Time
              </span>
            </div>

            <div className="space-y-2 max-h-[520px] overflow-auto pr-1">
              {activityLog.length === 0 ? (
                <div className="text-center py-12 text-xs text-surface-400">No activity logged yet.</div>
              ) : (
                activityLog.slice(0, 10).map((log, index) => {
                  const level = log.level || 'info';
                  return (
                    <div
                      key={log.id || index}
                      className="p-3 rounded-xl bg-surface-900/50 border border-surface-800/80 text-xs flex gap-3 items-start hover:bg-surface-750/30 transition-colors"
                    >
                      <div className="mt-0.5 shrink-0">
                        {level === 'error' ? (
                          <AlertCircle size={15} className="text-loss-light" />
                        ) : level === 'signal' ? (
                          <Zap size={15} className="text-accent-light" />
                        ) : level === 'order' ? (
                          <CheckCircle2 size={15} className="text-profit-light" />
                        ) : (
                          <Activity size={15} className="text-surface-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between text-[10px] text-surface-500 mb-0.5">
                          <span className="uppercase font-semibold text-surface-400">[{level}]</span>
                          <span className="font-mono">{new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                        </div>
                        <div className="text-surface-200 leading-relaxed break-words">{log.message}</div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
