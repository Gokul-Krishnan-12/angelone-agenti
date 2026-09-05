import React, { useState } from 'react';
import { useTradingStore } from '../stores/trading-store';
import { useSmartAPI } from '../hooks/useSmartAPI';
import { Check, X, ShieldAlert, Zap, TrendingUp, Layers, CheckSquare, Square, Filter } from 'lucide-react';

// Top 10 strategies selected by 6-month backtest P&L on 20 Nifty 50 stocks.
// Ordered by backtest profitability (rank 1 = highest P&L).
export const ALL_STRATEGIES = [
  // ── High-win-rate strategies (research-validated, ~65-78% win rate) ────
  { id: 'liquidity_grab_reversal', name: 'Liquidity Grab Reversal', category: 'Smart Money', rank: 1, winRate: 78 },
  { id: 'opening_range_breakout',  name: 'Opening Range Breakout',  category: 'Intraday',    rank: 2, winRate: 72 },
  { id: 'gap_fill',                name: 'Gap Fill Reversal',        category: 'Reversal',    rank: 3, winRate: 68 },
  // ── Backtest-selected top-10 ───────────────────────────────────────────
  { id: 'volume_delta_divergence', name: 'Volume Delta Divergence', category: 'Smart Money', rank: 4, backtestPnl: 3007 },
  { id: 'cmf_accumulation',        name: 'CMF Institutional Flow',  category: 'Smart Money', rank: 5, backtestPnl: 2216 },
  { id: 'keltner_breakout',        name: 'Keltner Breakout',        category: 'Breakout',    rank: 6, backtestPnl: 2119 },
  { id: 'williams_r',              name: 'Williams %R',             category: 'Oscillator',  rank: 7, backtestPnl: 2079 },
  { id: 'cci_reversal',            name: 'CCI Reversal',            category: 'Oscillator',  rank: 8, backtestPnl: 1603 },
  { id: 'macd_cross',              name: 'MACD Cross',              category: 'Momentum',    rank: 9, backtestPnl: 1346 },
  { id: 'bollinger_breakout',      name: 'Bollinger Breakout',      category: 'Breakout',    rank: 10, backtestPnl: 1135 },
  { id: 'stochastic_reversal',     name: 'Stochastic Reversal',     category: 'Oscillator',  rank: 11, backtestPnl:  909 },
  { id: 'tsi_cross',               name: 'True Strength Index',     category: 'Momentum',    rank: 12, backtestPnl:  877 },
  { id: 'psar_trend',              name: 'Parabolic SAR',           category: 'Trend',       rank: 13, backtestPnl:  567 },
];

// Disabled — underperformed in 6-month backtest. Can be re-enabled in Settings.
export const DISABLED_STRATEGIES = [
  { id: 'awesome_oscillator',       name: 'Awesome Oscillator',      category: 'Oscillator',  backtestPnl:  525 },
  { id: 'stoc_rsi',                 name: 'Stochastic RSI',          category: 'Oscillator',  backtestPnl:  514 },
  { id: 'adx_momentum',             name: 'ADX Momentum',            category: 'Momentum',    backtestPnl:  251 },
  { id: 'donchian_breakout',        name: 'Donchian Breakout',       category: 'Breakout',    backtestPnl:  172 },
  { id: 'rsi_reversal',             name: 'RSI Reversal',            category: 'Momentum',    backtestPnl:  131 },
  { id: 'ema_crossover',            name: 'EMA Crossover',           category: 'Trend',       backtestPnl:   99 },
  { id: 'mfi_exhaustion',           name: 'MFI Exhaustion',          category: 'Volume',      backtestPnl:   -7 },
  { id: 'order_block_fvg',          name: 'Order Block & FVG',       category: 'Smart Money', backtestPnl: -113 },
  { id: 'institutional_absorption', name: 'Institutional Absorption',category: 'Smart Money', backtestPnl:    0 },
  { id: 'supertrend',               name: 'Supertrend',              category: 'Trend',       backtestPnl:    0 },
  { id: 'vwap_bounce',              name: 'VWAP Bounce',             category: 'Intraday',    backtestPnl:    0 },
];

const AgentControl: React.FC = () => {
  const { agentState, signals, setAgentState } = useTradingStore();
  const { startAgent, stopAgent } = useSmartAPI();
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [executedTrade, setExecutedTrade] = useState<string>('');

  const handleToggle = async () => {
    try {
      if (agentState.running) {
        await stopAgent();
        setAgentState({ running: false });
        useTradingStore.getState().setSignals([]); // Clear live signals on stop
      } else {
        await startAgent(agentState.mode || 'confirm');
        setAgentState({ running: true });
      }
    } catch (e) {
      console.error('Failed to toggle agent', e);
    }
  };

  const handleModeChange = (mode: 'auto' | 'confirm') => {
    setAgentState({ mode });
    window.electronAPI?.invoke('settings:save', { mode });
  };

  const saveStrategiesToBackend = (strategiesList: string[]) => {
    const strategySettings: Record<string, { enabled: boolean }> = {};
    ALL_STRATEGIES.forEach(s => {
      strategySettings[s.id] = { enabled: strategiesList.includes(s.id) };
    });
    window.electronAPI?.invoke('settings:save', { strategies: strategySettings });
  };

  const handleStrategyToggle = (stratId: string) => {
    const isEnabled = agentState.enabledStrategies.includes(stratId);
    const newStrategies = isEnabled 
      ? agentState.enabledStrategies.filter(s => s !== stratId)
      : [...agentState.enabledStrategies, stratId];
      
    setAgentState({ enabledStrategies: newStrategies });
    saveStrategiesToBackend(newStrategies);
  };

  const handleEnableAll = () => {
    const allIds = ALL_STRATEGIES.map(s => s.id);
    setAgentState({ enabledStrategies: allIds });
    saveStrategiesToBackend(allIds);
  };

  const handleDisableAll = () => {
    setAgentState({ enabledStrategies: [] });
    saveStrategiesToBackend([]);
  };

  // Group signals by tradingsymbol + direction to calculate confluence
  const groupedSignals = React.useMemo(() => {
    const groups: Record<string, {
      tradingsymbol: string;
      direction: 'BUY' | 'SELL';
      signals: typeof signals;
      avgConfidence: number;
      confluenceScore: number;
    }> = {};

    signals.forEach(sig => {
      const key = `${sig.tradingsymbol}_${sig.direction}`;
      if (!groups[key]) {
        groups[key] = {
          tradingsymbol: sig.tradingsymbol,
          direction: sig.direction,
          signals: [],
          avgConfidence: 0,
          confluenceScore: 0
        };
      }
      groups[key].signals.push(sig);
    });

    return Object.values(groups)
      .map(group => {
        group.confluenceScore = group.signals.length;
        group.avgConfidence = Math.round(group.signals.reduce((acc, s) => acc + s.confidence, 0) / group.confluenceScore);
        return group;
      })
      .sort((a, b) => {
        if (b.confluenceScore !== a.confluenceScore) {
          return b.confluenceScore - a.confluenceScore;
        }
        return b.avgConfidence - a.avgConfidence;
      });
  }, [signals]);

  const categories = ['All', 'Trend', 'Momentum', 'Oscillator', 'Smart Money', 'Breakout', 'Intraday', 'Volume'];
  const filteredStrategies = selectedCategory === 'All' 
    ? ALL_STRATEGIES 
    : ALL_STRATEGIES.filter(s => s.category === selectedCategory);

  return (
    <div className="p-6 flex flex-col space-y-6 min-h-full relative animate-fade-in">
      {/* Sticky Header */}
      <div className="flex justify-between items-center sticky top-0 bg-surface-900/95 backdrop-blur-sm z-30 py-4 px-6 -mx-6 -mt-6 mb-2 border-b border-surface-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Agent Control & Signals</h1>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${agentState.running ? 'bg-profit-fade text-profit-light border border-profit/30' : 'bg-surface-700 text-surface-400'}`}>
              {agentState.running ? 'ACTIVE SCANNER' : 'OFFLINE'}
            </span>
          </div>
          <p className="text-xs text-surface-400 mt-1">
            Real-time multi-strategy scanner evaluating NIFTY 50 and custom watchlist with confluence tracking.
          </p>
        </div>
        <button 
          onClick={handleToggle}
          className={`px-8 py-3 rounded-xl font-bold text-sm tracking-wide shadow-lg transition-all cursor-pointer ${agentState.running ? 'bg-loss-dark hover:bg-loss text-white shadow-loss/20' : 'bg-profit-dark hover:bg-profit text-white shadow-profit/20'}`}
        >
          {agentState.running ? 'STOP AGENT' : 'START AGENT'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 relative">
        {/* Left Column: Settings & Strategies */}
        <div className="lg:col-span-2 space-y-6">
          {/* Trading Execution Mode */}
          <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl p-5 shadow-lg">
            <h2 className="text-sm font-bold uppercase tracking-wider text-surface-300 mb-3 flex items-center gap-2">
              <Zap size={16} className="text-accent-light" />
              <span>Execution Mode</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div 
                onClick={() => handleModeChange('confirm')}
                className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${agentState.mode === 'confirm' ? 'border-accent-light bg-surface-700/70 shadow-md' : 'border-surface-700 bg-surface-900/60 hover:border-surface-600'}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-white text-sm">Signal + Confirm (Recommended)</span>
                  {agentState.mode === 'confirm' && <Check size={16} className="text-accent-light" />}
                </div>
                <p className="text-xs text-surface-400">
                  Agent generates live signals with confluence score and waits for your confirmation before placing orders.
                </p>
              </div>

              <div 
                onClick={() => handleModeChange('auto')}
                className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${agentState.mode === 'auto' ? 'border-profit-light bg-surface-700/70 shadow-md' : 'border-surface-700 bg-surface-900/60 hover:border-surface-600'}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-white text-sm">Full Autonomous Mode</span>
                  {agentState.mode === 'auto' && <Check size={16} className="text-profit-light" />}
                </div>
                <p className="text-xs text-surface-400">
                  Agent automatically executes orders to Angel One as soon as high-confidence confluence triggers.
                </p>
              </div>
            </div>
          </div>

          {/* Active Technical Strategies (20 Strategies) */}
          <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl p-5 shadow-lg space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-surface-700/70">
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-surface-300 flex items-center gap-2">
                  <Layers size={16} className="text-accent-light" />
                  <span>Technical TA Strategies ({agentState.enabledStrategies.length}/{ALL_STRATEGIES.length} Active)</span>
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">Toggle individual technical algorithms to match market conditions.</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleEnableAll}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-700 hover:bg-surface-600 text-surface-200 text-xs font-medium transition-colors cursor-pointer"
                >
                  <CheckSquare size={13} />
                  <span>Enable All</span>
                </button>
                <button
                  onClick={handleDisableAll}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-700 hover:bg-surface-600 text-surface-200 text-xs font-medium transition-colors cursor-pointer"
                >
                  <Square size={13} />
                  <span>Disable All</span>
                </button>
              </div>
            </div>

            {/* Category Filter Pills */}
            <div className="flex flex-wrap gap-1.5">
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${selectedCategory === cat ? 'bg-accent text-surface-950 font-bold' : 'bg-surface-900 text-surface-400 hover:text-white border border-surface-700/60'}`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Strategy Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[460px] overflow-auto pr-1">
              {filteredStrategies.map((strat) => {
                const isEnabled = agentState.enabledStrategies.includes(strat.id);
                return (
                  <div 
                    key={strat.id} 
                    onClick={() => handleStrategyToggle(strat.id)}
                    className={`flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer ${isEnabled ? 'bg-surface-900/80 border-surface-700 hover:border-accent-light/50' : 'bg-surface-900/30 border-surface-800 opacity-60 hover:opacity-100'}`}
                  >
                    <div>
                      <span className="text-white text-sm font-medium block">{strat.name}</span>
                      <span className="text-[10px] text-surface-400 tracking-wider uppercase font-mono">{strat.category}</span>
                    </div>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStrategyToggle(strat.id);
                      }}
                      className={`w-11 h-6 rounded-full relative transition-colors cursor-pointer ${isEnabled ? 'bg-accent' : 'bg-surface-700'}`}
                    >
                      <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${isEnabled ? 'left-6' : 'left-1'}`}></div>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Live Signals Stream */}
        <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl flex flex-col h-full min-h-[500px] shadow-lg">
          <div className="p-5 pb-3 border-b border-surface-700/80 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <TrendingUp size={16} className="text-profit-light" />
                <span>Live Signals Stream</span>
              </h2>
              <span className="text-xs text-surface-400">Aggregated by confluence</span>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-surface-900 text-surface-300 text-xs font-mono font-bold border border-surface-700">
              {groupedSignals.length} {groupedSignals.length === 1 ? 'Signal' : 'Signals'}
            </span>
          </div>

          <div className="space-y-4 p-5 overflow-auto flex-1">
            {executedTrade && (
              <div className="bg-profit-fade border border-profit/30 text-profit-light text-xs p-3 rounded-xl flex items-center gap-2 animate-fade-in">
                <Check size={16} />
                <span>{executedTrade}</span>
              </div>
            )}

            {groupedSignals.length === 0 ? (
              <div className="py-16 text-center text-surface-500 flex flex-col items-center justify-center space-y-2">
                <TrendingUp size={36} className="opacity-20" />
                <p className="text-sm">No signals currently detected.</p>
                <p className="text-xs text-surface-600 max-w-xs">
                  {agentState.running ? 'Scanner is actively analyzing candles across 20 TA strategies...' : 'Start the agent above to begin market scanning.'}
                </p>
              </div>
            ) : (
              groupedSignals.map(group => {
                const bestSignal = group.signals.reduce((prev, current) => (prev.confidence > current.confidence) ? prev : current);
                const isBuy = group.direction === 'BUY';
                const entry = bestSignal.entryPrice || 0;
                const sl = bestSignal.stopLoss || 0;
                const tgt = bestSignal.target || 0;
                const riskDist = Math.abs(entry - sl);
                const rewardDist = Math.abs(tgt - entry);
                const rr = riskDist > 0 ? (rewardDist / riskDist).toFixed(1) : '2.0';
                const estMarginReq = Math.round(entry * 0.2); // 20% MIS intraday margin

                return (
                  <div key={`${group.tradingsymbol}_${group.direction}`} className="bg-surface-900/90 border border-surface-700 rounded-xl p-4 flex flex-col gap-3 shadow-md hover:border-surface-600 transition-all">
                    <div className="flex justify-between items-start">
                      <div className="flex items-center gap-2">
                        <span className={`px-2.5 py-1 text-xs font-bold rounded-lg uppercase tracking-wider ${isBuy ? 'bg-profit-dark/20 text-profit-light border border-profit/30' : 'bg-loss-dark/20 text-loss-light border border-loss/30'}`}>
                          {group.direction}
                        </span>
                        <span className="font-bold text-white text-base">{group.tradingsymbol}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] bg-accent/20 text-accent-light px-2 py-0.5 rounded font-mono font-bold border border-accent/30">
                          {group.confluenceScore} {group.confluenceScore === 1 ? 'Algo' : 'Algos'}
                        </span>
                        <span className="text-[10px] bg-surface-800 text-surface-300 px-2 py-0.5 rounded font-mono font-bold border border-surface-700">
                          R:R 1:{rr}
                        </span>
                      </div>
                    </div>

                    {/* Contributing Strategies */}
                    <div className="flex flex-wrap gap-1">
                      {group.signals.map(s => (
                        <span key={s.id} className="text-[10px] bg-surface-800 text-surface-300 px-2 py-0.5 rounded border border-surface-700/80" title={s.reasoning}>
                          {s.strategy.replace(/_/g, ' ')} ({s.confidence}%)
                        </span>
                      ))}
                    </div>

                    {/* Trade Price Details */}
                    <div className="grid grid-cols-3 gap-2 bg-surface-950/60 p-2.5 rounded-lg border border-surface-800 text-xs">
                      <div>
                        <span className="text-surface-400 block text-[10px]">Entry</span>
                        <span className="font-mono font-bold text-white">₹{entry.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-surface-400 block text-[10px]">Target</span>
                        <span className="font-mono font-bold text-profit-light">₹{tgt.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-surface-400 block text-[10px]">Stop Loss</span>
                        <span className="font-mono font-bold text-loss-light">₹{sl.toFixed(2)}</span>
                      </div>
                    </div>

                    {/* Confidence & Intraday Leverage Info */}
                    <div className="space-y-1">
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-surface-400">Confidence: {group.avgConfidence}%</span>
                        <span className="text-surface-400 font-mono">Est. Margin (5x MIS): ~₹{estMarginReq}</span>
                      </div>
                      <div className="w-full bg-surface-800 h-1.5 rounded-full overflow-hidden">
                        <div className="h-full bg-accent-light rounded-full transition-all" style={{ width: `${group.avgConfidence}%` }}></div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 pt-2 border-t border-surface-800">
                      <button 
                        onClick={() => {
                          window.electronAPI?.invoke('agent:execute-signal', bestSignal);
                          group.signals.forEach(s => useTradingStore.getState().removeSignal(s.id));
                          setExecutedTrade(`Executed ${group.direction} for ${group.tradingsymbol}`);
                          setTimeout(() => setExecutedTrade(''), 4000);
                        }} 
                        className="flex-1 bg-profit-dark hover:bg-profit flex items-center justify-center gap-1.5 py-2 rounded-lg transition-colors text-white text-xs font-bold cursor-pointer"
                      >
                        <Check size={14} /> Execute Intraday Order
                      </button>
                      <button 
                        onClick={() => {
                          group.signals.forEach(s => useTradingStore.getState().removeSignal(s.id));
                        }} 
                        className="px-4 bg-surface-800 hover:bg-surface-700 flex items-center justify-center gap-1.5 py-2 rounded-lg transition-colors text-surface-300 hover:text-white text-xs font-medium border border-surface-700 cursor-pointer"
                        title="Dismiss signal"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentControl;
