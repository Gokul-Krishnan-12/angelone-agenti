import React, { useState } from 'react';
import {
  Compass,
  Cpu,
  Layers,
  ShieldCheck,
  Percent,
  Search,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BarChart3,
  Split,
  Info
} from 'lucide-react';

interface StrategyItem {
  id: string;
  name: string;
  category: string;
  family: 'Smart Money' | 'Breakout' | 'Trend' | 'Momentum' | 'Oscillator' | 'Intraday';
  winRateOrRank: string;
  rrRatio: string;
  triggerRules: string;
  indicators: string;
  whyItWorks: string;
}

const STRATEGIES_LIST: StrategyItem[] = [
  {
    id: 'keltner_breakout',
    name: 'Keltner Channel Breakout',
    category: 'Volatility Breakout',
    family: 'Breakout',
    winRateOrRank: 'Rank 6 (₹2,119 P&L)',
    rrRatio: '1 : 4.0 (High Asymmetry)',
    triggerRules: 'Candle closes strictly outside Upper Band (BUY) or Lower Band (SELL) after previous bar was inside.',
    indicators: '20 EMA midline + 10 ATR envelope (Upper & Lower bands)',
    whyItWorks: 'Volatility breakouts out of compressed Keltner channels exhibit extreme directional momentum. Sets a tight 0.5% native SL and 2.0% target (1:4), which the Confluence Gate expands to 1.0% SL and 4.0% Target.'
  },
  {
    id: 'cmf_accumulation',
    name: 'CMF Institutional Flow',
    category: 'Institutional Smart Money',
    family: 'Smart Money',
    winRateOrRank: 'Rank 5 (₹2,216 P&L)',
    rrRatio: '1 : 2.0 (Standard Flow)',
    triggerRules: 'CMF > +0.10 with volume > 1.2x 20-bar average and price > 20 EMA (BUY). CMF < -0.10 with volume surge below 20 EMA (SELL).',
    indicators: 'Chaikin Money Flow (20-period), Volume Ratio, 20 EMA',
    whyItWorks: 'Tracks whether big institutional players are accumulating or distributing shares before price makes an extended swing.'
  },
  {
    id: 'cpr_breakout_reversal',
    name: 'Central Pivot Range (CPR)',
    category: 'Smart Money',
    family: 'Smart Money',
    winRateOrRank: '75% Win Rate (Rank 1)',
    rrRatio: '1 : 2.0 to 1 : 2.5',
    triggerRules: 'Rejection or breakout of Daily TC (Top Central) / BC (Bottom Central) pivot lines on high volume.',
    indicators: 'Pivot Point = (H + L + C)/3, TC = (Pivot - BC) + Pivot, BC = (H + L)/2',
    whyItWorks: 'Virgin and standard CPR levels act as high-probability magnet and support/resistance zones respected by Indian institutional algorithms.'
  },
  {
    id: 'liquidity_grab_reversal',
    name: 'Liquidity Grab Reversal',
    category: 'Smart Money',
    family: 'Smart Money',
    winRateOrRank: '78% Win Rate (Rank 2)',
    rrRatio: '1 : 2.5',
    triggerRules: 'Price briefly sweeps past previous day high/low or key swing point to trigger retail stop-orders, then aggressively closes back inside.',
    indicators: 'Swing Highs/Lows, Wick-to-Body Ratio > 2.0, Volume Spike',
    whyItWorks: 'Exploits fakeouts where smart money hunts retail stop-losses before driving price in the genuine counter-direction.'
  },
  {
    id: 'opening_range_breakout',
    name: 'Opening Range Breakout (ORB)',
    category: 'Intraday Pattern',
    family: 'Intraday',
    winRateOrRank: '72% Win Rate (Rank 3)',
    rrRatio: '1 : 2.0',
    triggerRules: 'First 15-minute high or low broken with strong expansion candle and relative volume surge.',
    indicators: '15-min High/Low Range, Relative Volume (RVOL)',
    whyItWorks: 'Sets the directional tone for the entire morning session once early market inventory is cleared.'
  },
  {
    id: 'gap_fill',
    name: 'Gap Fill Reversal',
    category: 'Mean Reversion',
    family: 'Smart Money',
    winRateOrRank: '68% Win Rate (Rank 4)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Morning gap up/down fails to sustain past key level; price re-enters yesterday’s closing range targeting the gap close.',
    indicators: 'Previous Close, Opening Tick Gap, 9 EMA Rejection',
    whyItWorks: 'Overextended overnight retail sentiment gets exhausted at open, creating reliable mean-reversion back to the prior close.'
  },
  {
    id: 'volume_delta_divergence',
    name: 'Volume Delta Divergence',
    category: 'Smart Money',
    family: 'Smart Money',
    winRateOrRank: 'Rank 5 (₹3,007 P&L)',
    rrRatio: '1 : 2.2',
    triggerRules: 'Price makes a lower low while buying delta volume increases (bullish), or price makes higher high while selling volume dominates (bearish).',
    indicators: 'Cumulative Volume Delta (CVD proxy), Swing Extremes',
    whyItWorks: 'Identifies institutional absorption where passive limit orders soak up aggressive market orders before a sharp reversal.'
  },
  {
    id: 'williams_r',
    name: 'Williams %R Extreme',
    category: 'Momentum Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Rank 7 (₹2,079 P&L)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Crosses upward above -80 from deeply oversold zone (BUY) or downward below -20 from overbought zone (SELL).',
    indicators: '14-period Williams %R',
    whyItWorks: 'Unlike standard RSI, Williams %R uses the highest high and lowest low of the lookback period, making it faster at catching cycle turns.'
  },
  {
    id: 'cci_reversal',
    name: 'Commodity Channel Index (CCI)',
    category: 'Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Rank 8 (₹1,603 P&L)',
    rrRatio: '1 : 2.0',
    triggerRules: 'CCI crosses back above -100 after reaching extreme oversold levels, confirmed by positive price bar.',
    indicators: '20-period CCI',
    whyItWorks: 'Measures standard deviation from mean price; extreme deviations inevitably snap back toward statistical equilibrium.'
  },
  {
    id: 'macd_cross',
    name: 'MACD Zero-Line Cross',
    category: 'Momentum',
    family: 'Momentum',
    winRateOrRank: 'Rank 9 (₹1,346 P&L)',
    rrRatio: '1 : 2.0',
    triggerRules: 'MACD line crosses Signal line in the direction of the zero-line threshold with expanding histogram bars.',
    indicators: 'Fast EMA (12), Slow EMA (26), Signal SMA (9)',
    whyItWorks: 'Filters out low-velocity whipsaws by requiring momentum confirmation across multiple moving average lookbacks.'
  },
  {
    id: 'bollinger_breakout',
    name: 'Bollinger Bands Squeeze Breakout',
    category: 'Breakout',
    family: 'Breakout',
    winRateOrRank: 'Rank 10 (₹1,135 P&L)',
    rrRatio: '1 : 2.5',
    triggerRules: 'Bollinger Band width narrows to 20-period low (volatility squeeze), followed by a decisive close outside the bands.',
    indicators: '20 SMA, 2.0 Standard Deviations, Bandwidth %',
    whyItWorks: 'Low volatility leads to high volatility; squeezing bands build stored potential energy that unleashes directional trend moves.'
  },
  {
    id: 'stochastic_reversal',
    name: 'Stochastic Oscillator Cross',
    category: 'Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Rank 11 (₹909 P&L)',
    rrRatio: '1 : 2.0',
    triggerRules: '%K line crosses above %D line below 20 (oversold) or %K crosses below %D above 80 (overbought).',
    indicators: '14, 3, 3 Fast/Slow Stochastic',
    whyItWorks: 'Excellent for swing reversals in range-bound market regimes.'
  },
  {
    id: 'tsi_cross',
    name: 'True Strength Index (TSI)',
    category: 'Momentum',
    family: 'Momentum',
    winRateOrRank: 'Rank 12 (₹877 P&L)',
    rrRatio: '1 : 2.0',
    triggerRules: 'TSI line crosses signal line in territory aligned with prevailing 50 EMA trend.',
    indicators: 'Double smoothed 25 and 13 EMAs',
    whyItWorks: 'Eliminates choppy lag and false crossovers by double-smoothing price momentum changes.'
  },
  {
    id: 'psar_trend',
    name: 'Parabolic SAR Trend Shift',
    category: 'Trend',
    family: 'Trend',
    winRateOrRank: 'Rank 13 (₹567 P&L)',
    rrRatio: '1 : 2.0',
    triggerRules: 'PSAR dot flips from above candles to below candles (BUY) with confirmation from ADX > 20.',
    indicators: 'Step 0.02, Max 0.20 Parabolic SAR',
    whyItWorks: 'Classic trailing indicator that stays in strong intraday trends until momentum completely collapses.'
  },
  {
    id: 'supertrend',
    name: 'Supertrend Directional Filter',
    category: 'Trend',
    family: 'Trend',
    winRateOrRank: 'Core Trend Validator',
    rrRatio: '1 : 2.0',
    triggerRules: 'Price closes across the Supertrend line (Period 10, Multiplier 3.0) confirming trend transition.',
    indicators: 'ATR (10) * 3.0 band offset from median price',
    whyItWorks: 'Provides a robust trend backbone, eliminating counter-trend noise during trending market regimes.'
  },
  {
    id: 'vwap_bounce',
    name: 'VWAP Pullback & Bounce',
    category: 'Intraday Pattern',
    family: 'Intraday',
    winRateOrRank: 'Institutional Benchmark',
    rrRatio: '1 : 2.0',
    triggerRules: 'Price pulls back to test session VWAP, forming a bullish hammer or bearish shooting star rejection.',
    indicators: 'Volume Weighted Average Price (VWAP)',
    whyItWorks: 'Institutions use VWAP as their primary benchmark; testing VWAP offers optimal risk-reward entry before smart money pushes price away.'
  },
  {
    id: 'order_block_fvg',
    name: 'Order Block & Fair Value Gap',
    category: 'Smart Money',
    family: 'Smart Money',
    winRateOrRank: 'Smart Money ICT',
    rrRatio: '1 : 2.5',
    triggerRules: 'Imbalance / 3-candle Fair Value Gap created by high-volume displacement, followed by a mitigation retest.',
    indicators: 'Fair Value Gap (FVG), Prior Pivot Displacement',
    whyItWorks: 'Fills institutional buy/sell imbalances created when market orders overwhelmed resting liquidity.'
  },
  {
    id: 'adx_momentum',
    name: 'ADX Trend Momentum Strength',
    category: 'Momentum',
    family: 'Momentum',
    winRateOrRank: 'Trend Strength Filter',
    rrRatio: '1 : 2.0',
    triggerRules: '+DI crosses above -DI with ADX > 25 rising (BUY), or -DI crosses above +DI with ADX > 25 (SELL).',
    indicators: '14-period ADX, +DI, -DI',
    whyItWorks: 'Distinguishes genuine directional trends from choppy consolidation ranges.'
  },
  {
    id: 'donchian_breakout',
    name: 'Donchian Channel Breakout (Turtle)',
    category: 'Breakout',
    family: 'Breakout',
    winRateOrRank: 'Classic Turtle Trading',
    rrRatio: '1 : 3.0',
    triggerRules: 'Price exceeds 20-period high (BUY) or breaks 20-period low (SELL).',
    indicators: '20-period Donchian Channels',
    whyItWorks: 'Captures tail-risk explosive moves by entering whenever price creates a new multi-hour high or low.'
  },
  {
    id: 'rsi_reversal',
    name: 'RSI Divergence & Reversal',
    category: 'Momentum',
    family: 'Momentum',
    winRateOrRank: 'Classic Mean Reversion',
    rrRatio: '1 : 2.0',
    triggerRules: 'Bullish divergence (price makes lower low while RSI makes higher low) or exit from oversold (<30).',
    indicators: '14-period Relative Strength Index',
    whyItWorks: 'Spots internal momentum exhaustion before it reflects on the candlestick chart.'
  }
];

const SystemGuide: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'architecture' | 'strategies' | 'confluence' | 'partial_booking' | 'paper_vs_live'>('architecture');
  const [strategyFilter, setStrategyFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredStrategies = STRATEGIES_LIST.filter(s => {
    const matchesCategory = strategyFilter === 'All' || s.category === strategyFilter || s.family === strategyFilter;
    const matchesSearch = s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.triggerRules.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.whyItWorks.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-surface-800 via-surface-900 to-surface-950 p-6 rounded-2xl border border-surface-700 shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-accent-light/10 text-accent-light rounded-xl border border-accent-light/20">
              <BookOpen size={26} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                System Architecture & Strategy Guide
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/30">
                  v2.4 Quant Core
                </span>
              </h1>
              <p className="text-sm text-surface-400 mt-1">
                Complete technical reference for strategies, multi-family confluence, risk geometry, and order execution.
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-2 p-1.5 bg-surface-950/70 rounded-xl border border-surface-800">
          {[
            { id: 'architecture', label: 'Architecture', icon: <Cpu size={16} /> },
            { id: 'strategies', label: '20+ Strategies', icon: <Compass size={16} /> },
            { id: 'confluence', label: 'Confluence & R:R', icon: <Layers size={16} /> },
            { id: 'partial_booking', label: 'Partial Booking', icon: <Split size={16} /> },
            { id: 'paper_vs_live', label: 'Paper vs Live', icon: <ShieldCheck size={16} /> }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-accent-light text-surface-950 font-semibold shadow-md'
                  : 'text-surface-400 hover:text-white hover:bg-surface-800'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}

      {/* 1. ARCHITECTURE & LIFECYCLE */}
      {activeTab === 'architecture' && (
        <div className="space-y-6">
          <div className="bg-surface-800 border border-surface-700/80 rounded-2xl p-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-2">
              <Cpu className="text-accent-light" size={20} />
              End-to-End System Pipeline
            </h2>
            <p className="text-sm text-surface-400 mb-6">
              The platform connects an Electron React desktop frontend over an IPC/JSON-RPC bridge to a headless Python quant engine running 20 strategies against live SmartAPI feeds.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {[
                {
                  step: '1',
                  title: 'Watchlist Feed',
                  desc: 'Hourly scanner ranks top liquid F&O symbols. WebSocket feeds real-time LTP ticks.',
                  badge: 'Dynamic Watchlist'
                },
                {
                  step: '2',
                  title: '20 TA Strategies',
                  desc: 'Pure vector functions run across candles every scan interval to detect setups.',
                  badge: 'Technical Scanner'
                },
                {
                  step: '3',
                  title: 'Confluence Gate',
                  desc: 'Requires ≥ 2 distinct indicator families voting together + 50 EMA trend check.',
                  badge: 'Statistical Gate'
                },
                {
                  step: '4',
                  title: 'Risk & Sizing',
                  desc: 'Calculates 1% account risk, 1.0% noise buffer floor, and 5x intraday margin.',
                  badge: 'Risk Manager'
                },
                {
                  step: '5',
                  title: 'Order Dispatch',
                  desc: 'Sends LIMIT pseudo-market orders to Angel One SmartAPI or virtual sandbox.',
                  badge: 'SmartAPI Bridge'
                },
                {
                  step: '6',
                  title: 'Active Monitor',
                  desc: 'Watches LTP ticks for Target 1, Breakeven SL, Target 2, and 15:15 auto square-off.',
                  badge: 'Multi-Target Exit'
                }
              ].map((item, idx) => (
                <div key={idx} className="relative flex flex-col bg-surface-900 border border-surface-700 rounded-xl p-4 hover:border-accent-light/40 transition-all">
                  <div className="flex items-center justify-between mb-2">
                    <span className="w-6 h-6 rounded-full bg-accent-light/20 text-accent-light flex items-center justify-center text-xs font-bold font-mono">
                      {item.step}
                    </span>
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-surface-800 text-surface-400">
                      {item.badge}
                    </span>
                  </div>
                  <h3 className="font-semibold text-white text-sm mb-1">{item.title}</h3>
                  <p className="text-xs text-surface-400 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-surface-800 border border-surface-700/80 rounded-2xl p-6 space-y-4">
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                <ShieldCheck className="text-profit-light" size={18} />
                Intraday Safeguards & Time Gates
              </h3>
              <ul className="space-y-3 text-xs text-surface-300">
                <li className="flex items-start gap-2.5">
                  <div className="p-1 rounded bg-profit-light/10 text-profit-light mt-0.5">
                    <CheckCircle2 size={14} />
                  </div>
                  <div>
                    <strong className="text-white">Opening 15-Minute Shield (9:15 – 9:30 AM):</strong> No new entries are allowed during the opening chaos to prevent wick stop-outs.
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <div className="p-1 rounded bg-profit-light/10 text-profit-light mt-0.5">
                    <CheckCircle2 size={14} />
                  </div>
                  <div>
                    <strong className="text-white">Golden Window (1:00 – 2:00 PM):</strong> Optimal afternoon session when European institutional volume drives directional follow-through.
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <div className="p-1 rounded bg-profit-light/10 text-profit-light mt-0.5">
                    <CheckCircle2 size={14} />
                  </div>
                  <div>
                    <strong className="text-white">3:00 PM Entry Cutoff:</strong> Absolute cutoff for opening new trades to avoid end-of-day market gamma crush.
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <div className="p-1 rounded bg-loss-light/10 text-loss-light mt-0.5">
                    <AlertCircle size={14} />
                  </div>
                  <div>
                    <strong className="text-white">3:15 PM Mandatory Auto Square-Off:</strong> All open intraday positions are closed automatically to avoid broker penalty fees.
                  </div>
                </li>
              </ul>
            </div>

            <div className="bg-surface-800 border border-surface-700/80 rounded-2xl p-6 space-y-4">
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                <Percent className="text-accent-light" size={18} />
                Risk Architecture & Money Management
              </h3>
              <ul className="space-y-3 text-xs text-surface-300">
                <li className="flex items-start gap-2.5">
                  <div className="p-1 rounded bg-accent-light/10 text-accent-light mt-0.5">
                    <Info size={14} />
                  </div>
                  <div>
                    <strong className="text-white">1.0% Noise Floor Stop-Loss:</strong> Any strategy with a native SL tighter than 1.0% is automatically expanded to 1.0% so normal volatility doesn’t trigger false exits.
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <div className="p-1 rounded bg-accent-light/10 text-accent-light mt-0.5">
                    <Info size={14} />
                  </div>
                  <div>
                    <strong className="text-white">Position Sizing:</strong> Based on capital allocation per trade (default ₹10,000–₹20,000) with 5x MIS margin (20% required margin).
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <div className="p-1 rounded bg-accent-light/10 text-accent-light mt-0.5">
                    <Info size={14} />
                  </div>
                  <div>
                    <strong className="text-white">Max Daily Loss Guard:</strong> If aggregate daily realized + unrealized loss reaches threshold (e.g. -₹2,000), trading halts immediately for the day.
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <div className="p-1 rounded bg-accent-light/10 text-accent-light mt-0.5">
                    <Info size={14} />
                  </div>
                  <div>
                    <strong className="text-white">Trailing SL & Breakeven:</strong> Ratchets stop-loss upward as the trade progresses, locking in unrealized paper profits.
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* 2. STRATEGIES CATALOG */}
      {activeTab === 'strategies' && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-surface-800 p-4 rounded-xl border border-surface-700">
            <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
              {['All', 'Smart Money', 'Breakout', 'Trend', 'Oscillator', 'Intraday'].map(cat => (
                <button
                  key={cat}
                  onClick={() => setStrategyFilter(cat)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-colors ${
                    strategyFilter === cat
                      ? 'bg-accent-light text-surface-950 font-semibold'
                      : 'bg-surface-900 text-surface-400 hover:text-white hover:bg-surface-700'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-2.5 text-surface-500" size={16} />
              <input
                type="text"
                placeholder="Search strategy or indicator..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-surface-900 border border-surface-700 rounded-lg text-xs text-white placeholder-surface-500 focus:outline-none focus:border-accent-light"
              />
            </div>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredStrategies.map((s, idx) => (
              <div
                key={idx}
                className="bg-surface-800 border border-surface-700/80 rounded-xl p-5 hover:border-accent-light/50 transition-all flex flex-col justify-between group shadow-sm hover:shadow-md"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-surface-900 text-accent-light border border-surface-700">
                      {s.category}
                    </span>
                    <span className="text-[11px] font-mono text-profit-light font-semibold">
                      {s.winRateOrRank}
                    </span>
                  </div>

                  <h3 className="font-bold text-white text-base group-hover:text-accent-light transition-colors mb-2">
                    {s.name}
                  </h3>

                  <div className="space-y-2 text-xs text-surface-400 mb-4">
                    <div>
                      <span className="text-surface-500 uppercase tracking-wider font-semibold text-[10px] block">Trigger Logic:</span>
                      <p className="text-surface-300 mt-0.5">{s.triggerRules}</p>
                    </div>
                    <div>
                      <span className="text-surface-500 uppercase tracking-wider font-semibold text-[10px] block">Indicators:</span>
                      <p className="text-surface-300 mt-0.5 font-mono text-[11px]">{s.indicators}</p>
                    </div>
                    <div>
                      <span className="text-surface-500 uppercase tracking-wider font-semibold text-[10px] block">Quant Rationale:</span>
                      <p className="text-surface-300 mt-0.5">{s.whyItWorks}</p>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-surface-700 flex items-center justify-between text-xs">
                  <span className="text-surface-400">Target R:R:</span>
                  <span className="font-semibold text-white px-2 py-0.5 bg-surface-900 rounded border border-surface-700 font-mono">
                    {s.rrRatio || '1 : 2.0'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. CONFLUENCE & R:R ENGINE */}
      {activeTab === 'confluence' && (
        <div className="space-y-6">
          <div className="bg-surface-800 border border-surface-700/80 rounded-2xl p-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-3">
              <Layers className="text-accent-light" size={20} />
              How the Multi-Family Confluence Gate Operates
            </h2>
            <p className="text-sm text-surface-400 leading-relaxed mb-6">
              A single indicator firing is rarely enough to beat intraday market friction. The Confluence Gate groups all 20 strategies into independent statistical families. An order is ONLY approved when multiple distinct families agree on the same direction at the same time.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-6">
              {[
                { name: 'Trend Family', examples: 'EMA Cross, Supertrend, PSAR', role: 'Confirms broad momentum direction' },
                { name: 'Smart Money Family', examples: 'CPR, Liquidity Sweep, CMF Flow', role: 'Tracks institutional footprint' },
                { name: 'Volatility Family', examples: 'Keltner Channel, Bollinger Bands', role: 'Validates expansion out of compression' },
                { name: 'Oscillator Family', examples: 'Williams %R, CCI, Stochastic', role: 'Catches cycle inflection points' },
                { name: 'Momentum Family', examples: 'MACD, True Strength Index (TSI)', role: 'Ensures velocity is accelerating' }
              ].map((fam, i) => (
                <div key={i} className="bg-surface-900 p-4 rounded-xl border border-surface-700">
                  <h4 className="text-sm font-semibold text-white mb-1">{fam.name}</h4>
                  <p className="text-[11px] font-mono text-accent-light mb-2">{fam.examples}</p>
                  <p className="text-xs text-surface-400">{fam.role}</p>
                </div>
              ))}
            </div>

            <div className="bg-surface-900 border border-surface-700 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <BarChart3 className="text-accent-light" size={16} />
                Why Did HINDZINC Get a 1:4 R:R While CMF Got 1:2 Today?
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-surface-300">
                <div className="p-4 rounded-lg bg-surface-800 border border-surface-700">
                  <h4 className="font-bold text-accent-light mb-2 flex items-center gap-1.5">
                    <span>HINDZINC: Keltner Breakout (1:4 R:R)</span>
                  </h4>
                  <ul className="space-y-1.5 leading-relaxed">
                    <li>• <strong>Strategy Blueprint:</strong> Channel breakouts possess explosive directional momentum, so Keltner specifies an initial 0.5% SL and 2.0% Target (1:4 ratio).</li>
                    <li>• <strong>Noise Expansion:</strong> The Confluence Gate observed 0.5% (₹3.00) is too tight for market noise, widening it to the 1.0% safety floor (₹6.01 → SL ₹606.76).</li>
                    <li>• <strong>Edge Preservation:</strong> Rather than reducing reward, the gate scaled target by 4 × Safe Risk (₹6.01 × 4 = ₹24.03 → Target ₹576.72).</li>
                    <li>• <strong>Outcome:</strong> Complete 1:4 ratio preserved with 2x more breathing room against false breakouts!</li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg bg-surface-800 border border-surface-700">
                  <h4 className="font-bold text-accent-light mb-2 flex items-center gap-1.5">
                    <span>HCLTECH & LICHSGFIN: CMF Flow (1:2 R:R)</span>
                  </h4>
                  <ul className="space-y-1.5 leading-relaxed">
                    <li>• <strong>Strategy Blueprint:</strong> Institutional volume accumulation/distribution is a trend-continuation setup, optimized for a reliable 1:2 R:R.</li>
                    <li>• <strong>Noise Buffer:</strong> Both stop losses were aligned to the 1.0% floor (HCLTECH ₹12.04, LICHSGFIN ₹5.53).</li>
                    <li>• <strong>Target Calculation:</strong> Exactly 2.0 × Risk distance (HCLTECH ₹24.08, LICHSGFIN ₹11.07).</li>
                    <li>• <strong>Outcome:</strong> High hit-rate, steady baseline profit trades.</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. PARTIAL PROFIT BOOKING */}
      {activeTab === 'partial_booking' && (
        <div className="space-y-6">
          <div className="bg-surface-800 border border-surface-700/80 rounded-2xl p-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-3">
              <Split className="text-accent-light" size={20} />
              Multi-Target Scaling & Breakeven Protection
            </h2>
            <p className="text-sm text-surface-400 leading-relaxed mb-6">
              In intraday equities, a 4% move (like 1:4 on HINDZINC) rarely moves in a straight line. The system automatically splits high-asymmetry setups into a 2-stage execution:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-surface-900 border border-surface-700 rounded-xl p-5 relative">
                <span className="w-7 h-7 rounded-full bg-accent-light/20 text-accent-light flex items-center justify-center font-bold text-xs mb-3">
                  1
                </span>
                <h3 className="font-bold text-white text-sm mb-1">Entry & Dual Targets</h3>
                <p className="text-xs text-surface-400 leading-relaxed">
                  Position opens with 100% quantity. Target 1 is pegged at 1:2 R:R, and Target 2 is pegged at full breakout target (1:4 R:R).
                </p>
              </div>

              <div className="bg-surface-900 border border-surface-700 rounded-xl p-5 relative">
                <span className="w-7 h-7 rounded-full bg-profit-light/20 text-profit-light flex items-center justify-center font-bold text-xs mb-3">
                  2
                </span>
                <h3 className="font-bold text-white text-sm mb-1">Target 1: Book 50%</h3>
                <p className="text-xs text-surface-400 leading-relaxed">
                  When price hits Target 1, 50% of the shares are exited immediately, locking in guaranteed green P&L into your cash balance.
                </p>
              </div>

              <div className="bg-surface-900 border border-surface-700 rounded-xl p-5 relative">
                <span className="w-7 h-7 rounded-full bg-surface-700 text-white flex items-center justify-center font-bold text-xs mb-3">
                  3
                </span>
                <h3 className="font-bold text-white text-sm mb-1">SL to Breakeven (Risk-Free)</h3>
                <p className="text-xs text-surface-400 leading-relaxed">
                  The Stop Loss for the remaining 50% is instantly ratcheted to the <strong>Entry Price</strong>. The runner now targets Target 2 with ZERO downside risk.
                </p>
              </div>
            </div>

            <div className="bg-gradient-to-r from-surface-900 to-surface-800 border border-surface-700 rounded-xl p-5">
              <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-2">
                <ShieldCheck className="text-profit-light" size={16} />
                Smart Brokerage Safeguard (Avoiding Order Fee Drag)
              </h3>
              <p className="text-xs text-surface-300 leading-relaxed">
                Because Angel One charges <strong>₹20 per executed order</strong>, splitting a trade into two sell orders costs an extra <strong>₹20 (+ GST = ₹23.60)</strong>.
                To ensure this fee never hurts returns, the engine enforces a <strong>₹250 Minimum Profit Threshold</strong>:
              </p>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-3 bg-surface-950/60 rounded border border-surface-700">
                  <span className="text-profit-light font-semibold">Standard Position (e.g. 166 shares HINDZINC):</span>
                  <p className="text-surface-400 mt-1">
                    50% profit at 1:2 = <strong>+₹997.66</strong>. Paying ₹23.60 extra brokerage to lock in ₹997 and make the rest risk-free is mathematically superior.
                  </p>
                </div>
                <div className="p-3 bg-surface-950/60 rounded border border-surface-700">
                  <span className="text-accent-light font-semibold">Micro Position (e.g. 2 shares of ₹200 stock):</span>
                  <p className="text-surface-400 mt-1">
                    50% profit at 1:2 = ₹8.00. Splitting would waste ₹23.60. The engine automatically bypasses partial booking and uses a <strong>single full exit</strong>!
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. PAPER VS LIVE TRADING */}
      {activeTab === 'paper_vs_live' && (
        <div className="space-y-6">
          <div className="bg-surface-800 border border-surface-700/80 rounded-2xl p-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-3">
              <HelpCircle className="text-accent-light" size={20} />
              Paper Trading vs Live SmartAPI Trading Comparison
            </h2>
            <p className="text-sm text-surface-400 leading-relaxed mb-6">
              The Paper Trading sandbox runs on the exact same backend scanner and confluence gate as real live trading. Here is how they compare:
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-surface-900 text-surface-400 uppercase tracking-wider font-semibold border-b border-surface-700">
                  <tr>
                    <th className="p-3.5">Dimension</th>
                    <th className="p-3.5 text-accent-light">Virtual Paper Trading</th>
                    <th className="p-3.5 text-profit-light">Live Trading (Angel One SmartAPI)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700">
                  {[
                    {
                      dim: 'Strategy Signals & Scanner',
                      paper: 'Identical (20 Strategies scan every minute)',
                      live: 'Identical (Shares the exact same Python scanner)'
                    },
                    {
                      dim: 'Confluence Gate & Multi-Family Voting',
                      paper: 'Identical (Requires ≥ 2 families + 50 EMA trend)',
                      live: 'Identical (Extra backstop: Confidence ≥ 85% in Auto mode)'
                    },
                    {
                      dim: 'Risk-to-Reward & Noise Floor',
                      paper: 'Identical (1.0% min SL buffer + 1:2 or 1:4 Target)',
                      live: 'Identical (Exact same ₹ levels placed to broker)'
                    },
                    {
                      dim: 'Partial Profit Booking & Breakeven',
                      paper: 'Supported (Books 50% at Target 1, moves SL to Entry)',
                      live: 'Supported (Sends partial limit order, ratchets broker SL)'
                    },
                    {
                      dim: 'Order Execution Mechanism',
                      paper: 'Simulated fill at tick price',
                      live: 'Real LIMIT orders placed via SmartAPI on NSE/BSE'
                    },
                    {
                      dim: 'Charges & Taxes',
                      paper: '₹0 (Gross P&L tracking)',
                      live: '₹20/order brokerage + STT + Exchange fees + GST'
                    },
                    {
                      dim: 'Execution Modes',
                      paper: 'Always automatic in virtual sandbox',
                      live: 'Toggle between "Confirm Mode" (manual approval) and "Auto Mode"'
                    }
                  ].map((row, i) => (
                    <tr key={i} className="hover:bg-surface-700/50 transition-colors">
                      <td className="p-3.5 font-semibold text-white">{row.dim}</td>
                      <td className="p-3.5 text-surface-300">{row.paper}</td>
                      <td className="p-3.5 text-surface-300">{row.live}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemGuide;
