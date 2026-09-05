import React, { useState } from 'react';
import { usePaperTradingStore } from '../stores/paper-trading-store';
import {
  Play,
  Square,
  RotateCcw,
  Wallet,
  TrendingUp,
  TrendingDown,
  Target,
  ShieldAlert,
  Sparkles,
  FlaskConical,
  XCircle,
  Clock,
  Zap,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  Trash2
} from 'lucide-react';

const PaperTrade: React.FC = () => {
  const {
    dummyBalance,
    initialCapital,
    isRunning,
    positions,
    orders,
    activityLog,
    maxCapitalPerTrade,
    setIsRunning,
    setDummyBalance,
    setMaxCapitalPerTrade,
    resetAccount,
    manualSquareOff,
    clearLogs
  } = usePaperTradingStore();

  const [customBalanceInput, setCustomBalanceInput] = useState<string>('');
  const [showBalanceModal, setShowBalanceModal] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'positions' | 'orders' | 'logs'>('positions');

  // Compute metrics
  const totalMarginUsed = positions.reduce((acc, p) => acc + p.marginUsed, 0);
  const totalUnrealizedPnl = positions.reduce((acc, p) => acc + p.pnl, 0);
  const closedOrders = orders.filter((o) => o.status !== 'OPEN');
  const totalRealizedPnl = closedOrders.reduce((acc, o) => acc + (o.pnl || 0), 0);
  const totalNetPnl = totalRealizedPnl + totalUnrealizedPnl;
  const totalEquity = dummyBalance + totalMarginUsed + totalUnrealizedPnl;
  const totalReturnPct = initialCapital > 0 ? ((totalEquity - initialCapital) / initialCapital) * 100 : 0;

  const targetHitCount = closedOrders.filter((o) => o.status === 'TARGET_HIT').length;
  const slHitCount = closedOrders.filter((o) => o.status === 'STOPLOSS_HIT').length;
  const winRate = closedOrders.length > 0 ? (targetHitCount / closedOrders.length) * 100 : 0;

  const handleUpdateBalance = (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseFloat(customBalanceInput);
    if (!isNaN(val) && val > 0) {
      setDummyBalance(val);
      setShowBalanceModal(false);
      setCustomBalanceInput('');
    }
  };

  const setPresetBalance = (amount: number) => {
    setDummyBalance(amount);
    setShowBalanceModal(false);
  };

  return (
    <div className="p-6 space-y-6 h-full overflow-auto max-w-[1600px] mx-auto animate-fade-in">
      {/* ─── TOP HEADER & ZERO RISK BANNER ───────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-surface-800/80">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-accent/20 text-accent-light flex items-center justify-center border border-accent/30">
              <FlaskConical size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white tracking-tight">Paper Trading Sandbox</h1>
                <span className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  isRunning ? 'bg-profit-dark/20 text-profit-light border border-profit/30' : 'bg-surface-800 text-surface-400 border border-surface-700'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-profit-light animate-ping' : 'bg-surface-500'}`} />
                  {isRunning ? 'SIMULATION RUNNING' : 'SIMULATION IDLE'}
                </span>
              </div>
              <p className="text-xs text-surface-400 mt-0.5">
                Executes automated technical breakout strategies using live market prices, but with 100% simulated dummy money.
              </p>
            </div>
          </div>
        </div>

        {/* Top Controls */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={() => setShowBalanceModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-surface-800 hover:bg-surface-750 text-surface-200 hover:text-white border border-surface-700 rounded-xl text-xs font-semibold transition-all shadow-sm cursor-pointer"
          >
            <Wallet size={14} className="text-accent-light" />
            <span>Set Capital: ₹{initialCapital.toLocaleString('en-IN')}</span>
          </button>

          <button
            onClick={() => resetAccount()}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-surface-800 hover:bg-surface-750 text-surface-400 hover:text-white border border-surface-700 rounded-xl text-xs font-semibold transition-all shadow-sm cursor-pointer"
            title="Reset simulated positions, orders, and restore starting balance"
          >
            <RotateCcw size={14} />
            <span>Reset</span>
          </button>

          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold transition-all shadow-md cursor-pointer ${
              isRunning
                ? 'bg-loss-dark/90 hover:bg-loss text-white border border-loss/40 shadow-loss/20'
                : 'bg-profit-dark/90 hover:bg-profit text-white border border-profit/40 shadow-profit/20'
            }`}
          >
            {isRunning ? (
              <>
                <Square size={13} fill="currentColor" />
                <span>Stop Paper Trading</span>
              </>
            ) : (
              <>
                <Play size={13} fill="currentColor" />
                <span>Start Paper Trading</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ─── ISOLATION SAFETY NOTICE ──────────────────────────────────── */}
      <div className="bg-gradient-to-r from-accent/10 via-surface-850 to-surface-850 border border-accent/30 rounded-2xl p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Sparkles size={20} className="text-accent-light shrink-0" />
          <div className="text-xs">
            <span className="font-bold text-white block">100% Risk-Free Trading Sandbox:</span>
            <span className="text-surface-300">
              Orders placed here are simulated locally and <strong>will NEVER touch your real Angel One broker account</strong> or real money.
              The agent tests strategy triggers and fills against real NSE market prices.
            </span>
          </div>
        </div>
        <span className="text-[10px] uppercase font-mono font-bold tracking-wider px-2 py-1 rounded bg-surface-800 text-surface-300 border border-surface-700 shrink-0">
          Isolated Sandbox
        </span>
      </div>

      {/* ─── TOP 4 METRIC CARDS ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Virtual P&L */}
        <div className={`p-5 rounded-2xl border backdrop-blur-md bg-surface-800/90 shadow-lg ${
          totalNetPnl >= 0 ? 'border-profit/30' : 'border-loss/30'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-400">Virtual Net P&L</span>
            <span className={`flex items-center gap-1 text-xs font-mono font-bold px-2 py-0.5 rounded-full ${
              totalNetPnl >= 0 ? 'bg-profit-dark/20 text-profit-light border border-profit/30' : 'bg-loss-dark/20 text-loss-light border border-loss/30'
            }`}>
              {totalReturnPct >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              <span>{totalReturnPct >= 0 ? '+' : ''}{totalReturnPct.toFixed(2)}%</span>
            </span>
          </div>
          <div className={`text-3xl font-mono font-extrabold tracking-tight ${totalNetPnl >= 0 ? 'text-profit-light' : 'text-loss-light'}`}>
            {totalNetPnl >= 0 ? '+' : ''}₹{totalNetPnl.toFixed(2)}
          </div>
          <div className="flex items-center justify-between text-[11px] text-surface-400 mt-3 pt-2.5 border-t border-surface-700/60">
            <span>Realized: <strong className={totalRealizedPnl >= 0 ? 'text-profit-light' : 'text-loss-light'}>₹{totalRealizedPnl.toFixed(2)}</strong></span>
            <span>Open MTM: <strong className={totalUnrealizedPnl >= 0 ? 'text-profit-light' : 'text-loss-light'}>₹{totalUnrealizedPnl.toFixed(2)}</strong></span>
          </div>
        </div>

        {/* Metric 2: Available Dummy Capital */}
        <div className="p-5 rounded-2xl border border-surface-700/80 bg-surface-800/90 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-surface-400">Dummy Balance</span>
              <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-surface-700 text-surface-300">
                Virtual Cash
              </span>
            </div>
            <div className="text-3xl font-mono font-extrabold text-white tracking-tight">
              ₹{dummyBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-surface-700/60 flex items-center justify-between text-[11px]">
            <span className="text-surface-400">5x Leverage Exposure:</span>
            <span className="font-mono font-bold text-accent-light">₹{(dummyBalance * 5).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
          </div>
        </div>

        {/* Metric 3: Simulation Win Rate */}
        <div className="p-5 rounded-2xl border border-surface-700/80 bg-surface-800/90 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-surface-400">Strategy Hit Rate</span>
              <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                winRate >= 50 ? 'bg-profit-dark/20 text-profit-light border border-profit/30' : 'bg-surface-700 text-surface-300'
              }`}>
                {winRate.toFixed(1)}%
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-mono font-extrabold text-white tracking-tight">{closedOrders.length}</span>
              <span className="text-xs text-surface-400 font-medium">completed trades</span>
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-surface-700/60 flex items-center justify-between text-[11px]">
            <span className="text-profit-light font-medium flex items-center gap-1">
              <Target size={12} /> {targetHitCount} Targets Hit
            </span>
            <span className="text-loss-light font-medium flex items-center gap-1">
              <ShieldAlert size={12} /> {slHitCount} Stops Triggered
            </span>
          </div>
        </div>

        {/* Metric 4: Active Paper Positions */}
        <div className="p-5 rounded-2xl border border-surface-700/80 bg-surface-800/90 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-surface-400">Open Virtual Trades</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-surface-700 text-surface-300">
                {positions.length} Active
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-mono font-extrabold text-white tracking-tight">{positions.length}</span>
              <span className="text-xs text-surface-400 font-medium">in play</span>
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-surface-700/60 flex items-center justify-between text-[11px]">
            <span className="text-surface-400">Utilized Margin:</span>
            <span className="font-mono text-white">₹{totalMarginUsed.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* ─── TABS & MAIN SIMULATOR CONTAINER ─────────────────────────── */}
      <div className="bg-surface-800/90 backdrop-blur-md rounded-2xl border border-surface-700/80 shadow-lg overflow-hidden flex flex-col min-h-[500px]">
        {/* Navigation Tabs */}
        <div className="p-4 border-b border-surface-700/80 flex items-center justify-between bg-surface-850/60">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('positions')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'positions'
                  ? 'bg-accent/20 text-accent-light border border-accent/40 shadow-sm'
                  : 'text-surface-400 hover:text-white hover:bg-surface-700/50'
              }`}
            >
              <span>Active Virtual Positions</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-surface-700 text-surface-200">
                {positions.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('orders')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'orders'
                  ? 'bg-accent/20 text-accent-light border border-accent/40 shadow-sm'
                  : 'text-surface-400 hover:text-white hover:bg-surface-700/50'
              }`}
            >
              <span>Simulated Trade History</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-surface-700 text-surface-200">
                {orders.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('logs')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'logs'
                  ? 'bg-accent/20 text-accent-light border border-accent/40 shadow-sm'
                  : 'text-surface-400 hover:text-white hover:bg-surface-700/50'
              }`}
            >
              <span>Paper Activity Log</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-surface-700 text-surface-200">
                {activityLog.length}
              </span>
            </button>
          </div>

          {activeTab === 'logs' && (
            <button
              onClick={clearLogs}
              className="text-xs text-surface-400 hover:text-loss-light flex items-center gap-1 transition-colors"
            >
              <Trash2 size={13} />
              <span>Clear Log</span>
            </button>
          )}
        </div>

        {/* Tab 1: Active Paper Positions */}
        {activeTab === 'positions' && (
          <div className="p-5 flex-1 overflow-auto">
            {positions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center text-surface-400">
                <FlaskConical size={36} className="opacity-30 mb-3 text-accent-light" />
                <h3 className="text-base font-semibold text-white">No active paper trades</h3>
                <p className="text-xs text-surface-500 max-w-md mt-1">
                  {isRunning
                    ? 'Paper trading agent is actively listening for live breakout setups. When a TA signal triggers, it will automatically enter a simulated trade here.'
                    : 'Click "Start Paper Trading" at the top to let the agent take automated virtual trades on real live market signals.'}
                </p>
                {!isRunning && (
                  <button
                    onClick={() => setIsRunning(true)}
                    className="mt-4 px-5 py-2 bg-profit hover:bg-profit-dark text-white rounded-xl text-xs font-bold transition-all shadow-md"
                  >
                    Start Paper Trading Now
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {positions.map((p) => {
                  const isProf = p.pnl >= 0;
                  return (
                    <div
                      key={p.id}
                      className="bg-surface-900/60 rounded-2xl p-4 border border-surface-700/70 hover:border-surface-600 transition-all flex flex-col justify-between space-y-3"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white text-base">{p.tradingsymbol}</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              p.direction === 'BUY' ? 'bg-profit-dark/20 text-profit-light border border-profit/30' : 'bg-loss-dark/20 text-loss-light border border-loss/30'
                            }`}>
                              {p.direction}
                            </span>
                            <span className="text-[10px] font-mono text-surface-400 bg-surface-800 px-1.5 py-0.5 rounded">
                              {p.strategy}
                            </span>
                          </div>
                          <span className="text-[11px] text-surface-500 font-mono mt-0.5 block">
                            Entered at {new Date(p.entryTime).toLocaleTimeString()}
                          </span>
                        </div>

                        <div className="text-right">
                          <div className={`text-base font-mono font-bold ${isProf ? 'text-profit-light' : 'text-loss-light'}`}>
                            {isProf ? '+' : ''}₹{p.pnl.toFixed(2)}
                          </div>
                          <div className={`text-[11px] font-mono ${isProf ? 'text-profit-light' : 'text-loss-light'}`}>
                            {p.pnlPercent >= 0 ? '+' : ''}{p.pnlPercent.toFixed(2)}%
                          </div>
                        </div>
                      </div>

                      {/* Trade Parameters Box */}
                      <div className="grid grid-cols-4 gap-2 py-2 px-3 rounded-xl bg-surface-800/80 text-xs font-mono">
                        <div>
                          <span className="text-[10px] text-surface-400 block font-sans">Shares</span>
                          <span className="text-white font-bold">{p.quantity}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-surface-400 block font-sans">Entry</span>
                          <span className="text-white">₹{p.entryPrice.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-profit-light block font-sans">Target</span>
                          <span className="text-profit-light">₹{p.target.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-loss-light block font-sans">Stop Loss</span>
                          <span className="text-loss-light">₹{p.stopLoss.toFixed(2)}</span>
                        </div>
                      </div>

                      {/* Live Price & Square Off Button */}
                      <div className="flex items-center justify-between pt-1 border-t border-surface-800">
                        <div className="text-xs font-mono">
                          <span className="text-surface-400">Live LTP: </span>
                          <span className="text-white font-bold">₹{p.currentPrice.toFixed(2)}</span>
                        </div>

                        <button
                          onClick={() => manualSquareOff(p.id)}
                          className="px-3 py-1 rounded-lg text-xs font-medium text-loss-light hover:bg-loss-dark/20 border border-loss/30 transition-colors cursor-pointer"
                        >
                          Manual Square Off
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Simulated Trade History */}
        {activeTab === 'orders' && (
          <div className="flex-1 overflow-auto">
            {orders.length === 0 ? (
              <div className="py-20 text-center text-surface-400 text-xs">
                No simulated trades recorded yet.
              </div>
            ) : (
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] text-surface-400 uppercase bg-surface-900/90 border-b border-surface-700/80 sticky top-0">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Time</th>
                    <th className="px-5 py-3 font-semibold">Symbol</th>
                    <th className="px-5 py-3 font-semibold">Side</th>
                    <th className="px-5 py-3 font-semibold">Strategy</th>
                    <th className="px-5 py-3 font-semibold">Quantity</th>
                    <th className="px-5 py-3 font-semibold">Entry</th>
                    <th className="px-5 py-3 font-semibold">Exit</th>
                    <th className="px-5 py-3 font-semibold">Outcome</th>
                    <th className="px-5 py-3 font-semibold text-right">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700/50">
                  {orders.map((o) => {
                    const isBuy = o.direction === 'BUY';
                    const isProf = (o.pnl || 0) >= 0;

                    return (
                      <tr key={o.orderId} className="hover:bg-surface-700/30 transition-colors">
                        <td className="px-5 py-3 text-surface-400 font-mono">
                          {new Date(o.entryTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </td>
                        <td className="px-5 py-3 font-bold text-white">
                          {o.tradingsymbol}
                        </td>
                        <td className="px-5 py-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isBuy ? 'bg-profit-dark/20 text-profit-light' : 'bg-loss-dark/20 text-loss-light'
                          }`}>
                            {o.direction}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-surface-300 font-mono text-[11px]">
                          {o.strategy}
                        </td>
                        <td className="px-5 py-3 font-mono text-white">
                          {o.quantity}
                        </td>
                        <td className="px-5 py-3 font-mono text-white">
                          ₹{o.entryPrice.toFixed(2)}
                        </td>
                        <td className="px-5 py-3 font-mono text-white">
                          {o.exitPrice ? `₹${o.exitPrice.toFixed(2)}` : '—'}
                        </td>
                        <td className="px-5 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            o.status === 'TARGET_HIT'
                              ? 'bg-profit-dark/20 text-profit-light border border-profit/30'
                              : o.status === 'STOPLOSS_HIT'
                                ? 'bg-loss-dark/20 text-loss-light border border-loss/30'
                                : o.status === 'OPEN'
                                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                  : 'bg-surface-700 text-surface-300'
                          }`}>
                            {o.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-5 py-3 font-mono font-bold text-right">
                          {o.pnl !== undefined ? (
                            <span className={isProf ? 'text-profit-light' : 'text-loss-light'}>
                              {isProf ? '+' : ''}₹{o.pnl.toFixed(2)}
                            </span>
                          ) : (
                            <span className="text-surface-500 font-normal">Active</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Tab 3: Paper Activity Log */}
        {activeTab === 'logs' && (
          <div className="p-4 flex-1 overflow-auto space-y-2 font-mono text-xs">
            {activityLog.length === 0 ? (
              <div className="py-20 text-center text-surface-400">No log entries.</div>
            ) : (
              activityLog.map((l) => (
                <div key={l.id} className="p-2.5 rounded-xl bg-surface-900/50 border border-surface-800/80 flex items-start gap-3">
                  <span className="text-surface-500 text-[11px] shrink-0 pt-0.5">
                    {new Date(l.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={`px-2 py-0.2 rounded text-[10px] font-bold shrink-0 ${
                    l.type === 'EXECUTE'
                      ? 'bg-accent/20 text-accent-light'
                      : l.type === 'TARGET'
                        ? 'bg-profit-dark/20 text-profit-light'
                        : l.type === 'STOPLOSS'
                          ? 'bg-loss-dark/20 text-loss-light'
                          : l.type === 'EXIT'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-surface-700 text-surface-300'
                  }`}>
                    {l.type}
                  </span>
                  <span className="text-surface-200 font-sans text-xs flex-1">{l.message}</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* ─── MODAL: SET DUMMY CAPITAL ───────────────────────────────── */}
      {showBalanceModal && (
        <div className="fixed inset-0 bg-surface-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-900 border border-surface-700/90 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-5 animate-scale-in">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wallet size={18} className="text-accent-light" />
                <h3 className="text-base font-bold text-white">Set Dummy Capital</h3>
              </div>
              <button
                onClick={() => setShowBalanceModal(false)}
                className="text-surface-400 hover:text-white"
              >
                <XCircle size={18} />
              </button>
            </div>

            <p className="text-xs text-surface-400">
              Choose or type any starting virtual balance to test sizing and risk simulation.
            </p>

            {/* Presets */}
            <div className="grid grid-cols-2 gap-2">
              {[50000, 100000, 200000, 500000].map((amt) => (
                <button
                  key={amt}
                  type="button"
                  onClick={() => setPresetBalance(amt)}
                  className="py-2 px-3 rounded-xl bg-surface-800 hover:bg-surface-700 border border-surface-700 text-white font-mono text-xs font-semibold transition-colors text-center"
                >
                  ₹{amt.toLocaleString('en-IN')}
                </button>
              ))}
            </div>

            {/* Custom Input */}
            <form onSubmit={handleUpdateBalance} className="space-y-3 pt-2">
              <label className="block text-xs text-surface-300 font-medium">Custom Amount (₹)</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400 font-mono">₹</span>
                <input
                  type="number"
                  min="1000"
                  step="1000"
                  placeholder="e.g. 75000"
                  value={customBalanceInput}
                  onChange={(e) => setCustomBalanceInput(e.target.value)}
                  className="w-full bg-surface-950 border border-surface-700 rounded-xl pl-8 pr-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-accent-light"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowBalanceModal(false)}
                  className="px-4 py-2 bg-surface-800 text-surface-300 rounded-xl text-xs font-medium hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-accent hover:bg-accent-light text-surface-950 font-bold rounded-xl text-xs transition-colors"
                >
                  Apply Balance
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaperTrade;
