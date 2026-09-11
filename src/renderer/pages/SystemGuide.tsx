import React, { useState, useMemo } from 'react';
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
  Info,
  Clock,
  Zap,
  Target,
  ArrowRight,
  TrendingUp,
  Sparkles,
  Lock,
  Flame
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
    winRateOrRank: 'High Momentum (Top Tier)',
    rrRatio: '1 : 4.0 (High Asymmetry)',
    triggerRules: 'Candle closes strictly outside Upper Band (BUY) or Lower Band (SELL) after prior bar consolidation within the channel envelope.',
    indicators: '20 EMA midline + 10 ATR envelope (Upper & Lower bands)',
    whyItWorks: 'Volatility breakouts out of compressed Keltner channels exhibit explosive directional velocity. Targets outsized tail moves with scaled reward.'
  },
  {
    id: 'cmf_accumulation',
    name: 'CMF Institutional Flow',
    category: 'Institutional Flow',
    family: 'Smart Money',
    winRateOrRank: 'High Hit Rate (~74%)',
    rrRatio: '1 : 2.0 (Standard Flow)',
    triggerRules: 'CMF > +0.10 with volume > 1.2x 20-bar average and price > 20 EMA (BUY). CMF < -0.10 with volume surge below 20 EMA (SELL).',
    indicators: 'Chaikin Money Flow (20-period), Volume Ratio, 20 EMA',
    whyItWorks: 'Detects institutional accumulation or distribution before price breaks into an extended trend continuation swing.'
  },
  {
    id: 'cpr_breakout_reversal',
    name: 'Central Pivot Range (CPR)',
    category: 'Smart Money',
    family: 'Smart Money',
    winRateOrRank: 'High Probability (~75%)',
    rrRatio: '1 : 2.0 to 1 : 2.5',
    triggerRules: 'Rejection or breakout of Daily TC (Top Central) / BC (Bottom Central) pivot lines on elevated volume.',
    indicators: 'Pivot Point = (H + L + C)/3, TC = (Pivot - BC) + Pivot, BC = (H + L)/2',
    whyItWorks: 'Standard and virgin CPR levels act as high-probability magnets and inflection barriers heavily tracked by institutional algorithmic execution.'
  },
  {
    id: 'liquidity_grab_reversal',
    name: 'Liquidity Grab Reversal',
    category: 'Smart Money',
    family: 'Smart Money',
    winRateOrRank: 'Elite Edge (~78% Win Rate)',
    rrRatio: '1 : 2.5',
    triggerRules: 'Price sweeps past key swing high/low to trigger resting retail stop orders, then aggressively snaps back inside the range.',
    indicators: 'Swing Highs/Lows, Wick-to-Body Ratio > 2.0, Volume Spike',
    whyItWorks: 'Exploits institutional stop-hunts where large participants absorb counter-party inventory before driving price in the genuine direction.'
  },
  {
    id: 'opening_range_breakout',
    name: 'Opening Range Breakout (ORB)',
    category: 'Intraday Pattern',
    family: 'Intraday',
    winRateOrRank: 'Morning Focus (~72%)',
    rrRatio: '1 : 2.0',
    triggerRules: 'First 15-minute high or low decisively breached with strong expansion candle and relative volume surge.',
    indicators: '15-min High/Low Range, Relative Volume (RVOL)',
    whyItWorks: 'Establishes the prevailing directional order-flow for the entire morning session once opening market imbalances clear.'
  },
  {
    id: 'gap_fill',
    name: 'Gap Fill Reversal',
    category: 'Mean Reversion',
    family: 'Smart Money',
    winRateOrRank: 'High Reliability (~68%)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Morning gap up/down fails to sustain past key inflection; price re-enters prior day closing range targeting the gap fill.',
    indicators: 'Prior Close, Opening Tick Gap, 9 EMA Rejection',
    whyItWorks: 'Overextended retail opening sentiment gets exhausted quickly, creating reliable statistical reversion back to prior settlement value.'
  },
  {
    id: 'volume_delta_divergence',
    name: 'Volume Delta Divergence',
    category: 'Smart Money',
    family: 'Smart Money',
    winRateOrRank: 'Institutional Divergence',
    rrRatio: '1 : 2.2',
    triggerRules: 'Price prints lower low while buying delta volume increases (bullish), or price makes higher high while selling delta dominates (bearish).',
    indicators: 'Cumulative Volume Delta (CVD proxy), Swing Extremes',
    whyItWorks: 'Pinpoints institutional absorption where passive limit orders soak up aggressive market orders before a sharp trend turn.'
  },
  {
    id: 'williams_r',
    name: 'Williams %R Extreme',
    category: 'Momentum Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Cycle Inflection',
    rrRatio: '1 : 2.0',
    triggerRules: 'Crosses upward above -80 from deeply oversold band (BUY) or downward below -20 from overbought zone (SELL).',
    indicators: '14-period Williams %R',
    whyItWorks: 'Evaluates current close relative to the highest high and lowest low of the lookback, making it faster at detecting momentum turning points.'
  },
  {
    id: 'cci_reversal',
    name: 'Commodity Channel Index (CCI)',
    category: 'Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Statistical Mean Reversion',
    rrRatio: '1 : 2.0',
    triggerRules: 'CCI crosses back above -100 after reaching extreme statistical oversold territory, confirmed by positive price action.',
    indicators: '20-period CCI',
    whyItWorks: 'Measures standard deviation from mean price; extreme statistical extensions predictably snap back toward mathematical equilibrium.'
  },
  {
    id: 'macd_cross',
    name: 'MACD Zero-Line Cross',
    category: 'Momentum',
    family: 'Momentum',
    winRateOrRank: 'Momentum Validation',
    rrRatio: '1 : 2.0',
    triggerRules: 'MACD line crosses Signal line in the direction of the zero-line threshold with expanding histogram bars.',
    indicators: 'Fast EMA (12), Slow EMA (26), Signal SMA (9)',
    whyItWorks: 'Eliminates low-velocity whipsaws by requiring momentum confirmation across multiple exponential moving average lookbacks.'
  },
  {
    id: 'bollinger_breakout',
    name: 'Bollinger Bands Squeeze Breakout',
    category: 'Breakout',
    family: 'Breakout',
    winRateOrRank: 'Volatility Expansion',
    rrRatio: '1 : 2.5',
    triggerRules: 'Bollinger Band width contracts to multi-period low (volatility squeeze), followed by a decisive candle close outside the bands.',
    indicators: '20 SMA, 2.0 Standard Deviations, Bandwidth %',
    whyItWorks: 'Prolonged compression cycles store energy that reliably transitions into explosive directional volatility expansion.'
  },
  {
    id: 'stochastic_reversal',
    name: 'Stochastic Oscillator Cross',
    category: 'Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Range Reversal',
    rrRatio: '1 : 2.0',
    triggerRules: '%K line crosses above %D line below 20 (oversold) or %K crosses below %D above 80 (overbought).',
    indicators: '14, 3, 3 Fast/Slow Stochastic',
    whyItWorks: 'Optimized for high-probability swing turns within range-bound and consolidating market regimes.'
  },
  {
    id: 'tsi_cross',
    name: 'True Strength Index (TSI)',
    category: 'Momentum',
    family: 'Momentum',
    winRateOrRank: 'Smooth Trend Tracker',
    rrRatio: '1 : 2.0',
    triggerRules: 'TSI line crosses signal line in territory aligned with prevailing 50 EMA trend.',
    indicators: 'Double smoothed 25 and 13 EMAs',
    whyItWorks: 'Eliminates choppy lag and false crossovers by double-smoothing momentum rate-of-change.'
  },
  {
    id: 'psar_trend',
    name: 'Parabolic SAR Trend Shift',
    category: 'Trend',
    family: 'Trend',
    winRateOrRank: 'Trend Ride Setup',
    rrRatio: '1 : 2.0',
    triggerRules: 'PSAR dot flips from above candles to below candles (BUY) with confirmation from ADX > 20.',
    indicators: 'Step 0.02, Max 0.20 Parabolic SAR',
    whyItWorks: 'Classical trailing indicator that locks in directional intraday trends until underlying momentum completely exhausts.'
  },
  {
    id: 'supertrend',
    name: 'Supertrend Directional Filter',
    category: 'Trend',
    family: 'Trend',
    winRateOrRank: 'Core Trend Backbone',
    rrRatio: '1 : 2.0',
    triggerRules: 'Price closes across the Supertrend line (Period 10, Multiplier 3.0) confirming structural trend transition.',
    indicators: 'ATR (10) * 3.0 band offset from median price',
    whyItWorks: 'Provides a robust trend backbone, eliminating counter-trend noise during directional market days.'
  },
  {
    id: 'vwap_bounce',
    name: 'VWAP Pullback & Bounce',
    category: 'Intraday Pattern',
    family: 'Intraday',
    winRateOrRank: 'Institutional Benchmark',
    rrRatio: '1 : 2.0',
    triggerRules: 'Price pulls back to test session VWAP, forming a bullish hammer or bearish rejection candle.',
    indicators: 'Volume Weighted Average Price (VWAP)',
    whyItWorks: 'Institutions use VWAP as primary benchmark; testing VWAP offers tight risk-reward entry before large participants step back in.'
  },
  {
    id: 'order_block_fvg',
    name: 'Order Block & Fair Value Gap',
    category: 'Smart Money',
    family: 'Smart Money',
    winRateOrRank: 'Imbalance Fill Setup',
    rrRatio: '1 : 2.5',
    triggerRules: 'Imbalance / 3-candle Fair Value Gap created by high-volume displacement, followed by a mitigation retest.',
    indicators: 'Fair Value Gap (FVG), Prior Pivot Displacement',
    whyItWorks: 'Fills institutional buy/sell imbalances created when large market orders aggressively displace resting liquidity.'
  },
  {
    id: 'adx_momentum',
    name: 'ADX Trend Momentum Strength',
    category: 'Momentum',
    family: 'Momentum',
    winRateOrRank: 'Strength Qualifier',
    rrRatio: '1 : 2.0',
    triggerRules: '+DI crosses above -DI with ADX > 25 rising (BUY), or -DI crosses above +DI with ADX > 25 (SELL).',
    indicators: '14-period ADX, +DI, -DI',
    whyItWorks: 'Distinguishes true persistent directional moves from choppy consolidation noise.'
  },
  {
    id: 'donchian_breakout',
    name: 'Donchian Channel Breakout',
    category: 'Breakout',
    family: 'Breakout',
    winRateOrRank: 'Turtle Trend Breakout',
    rrRatio: '1 : 3.0',
    triggerRules: 'Price exceeds 20-period highest high (BUY) or breaks 20-period lowest low (SELL).',
    indicators: '20-period Donchian Channels',
    whyItWorks: 'Captures tail-risk explosive moves by entering whenever price creates a new multi-hour high or low.'
  },
  {
    id: 'rsi_reversal',
    name: 'RSI Divergence & Reversal',
    category: 'Momentum',
    family: 'Momentum',
    winRateOrRank: 'Mean Reversion',
    rrRatio: '1 : 2.0',
    triggerRules: 'Bullish divergence (price prints lower low while RSI makes higher low) or exit from oversold (<30).',
    indicators: '14-period Relative Strength Index',
    whyItWorks: 'Identifies internal momentum exhaustion before it becomes visible on the candlestick chart.'
  }
];

const SystemGuide: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'architecture' | 'strategies' | 'confluence' | 'partial_booking' | 'paper_vs_live'>('architecture');
  const [strategyFilter, setStrategyFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredStrategies = useMemo(() => {
    return STRATEGIES_LIST.filter(s => {
      const matchesCategory = strategyFilter === 'All' || s.category === strategyFilter || s.family === strategyFilter;
      const matchesSearch = s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.family.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.triggerRules.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.whyItWorks.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [strategyFilter, searchQuery]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner Header */}
      <div className="relative overflow-hidden bg-gradient-to-br from-surface-800 via-surface-900 to-surface-950 p-6 md:p-8 rounded-2xl border border-surface-700/80 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent-DEFAULT/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-accent-light/15 text-accent-light rounded-xl border border-accent-light/30 shadow-inner">
                <BookOpen size={24} />
              </div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
                  System Architecture & Strategy Guide
                </h1>
                <span className="hidden sm:inline-flex text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-accent-light/15 text-accent-light border border-accent-light/30">
                  v2.4 Quant Core
                </span>
              </div>
            </div>
            <p className="text-sm text-surface-300 max-w-2xl leading-relaxed">
              Complete technical specification for algorithmic execution, multi-family confluence gating, intraday time windows, and mathematical risk geometry.
            </p>
          </div>

          {/* Quick Metrics Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Strategies</span>
              <span className="text-base font-bold text-white font-mono">20 Active</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Confluence</span>
              <span className="text-base font-bold text-accent-light font-mono">≥ 2 Families</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Safety Floor</span>
              <span className="text-base font-bold text-profit-light font-mono">1.0% Min SL</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Intraday MIS</span>
              <span className="text-base font-bold text-warning-light font-mono">5x Margin</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="mt-6 pt-5 border-t border-surface-700/60 flex flex-wrap gap-2">
          {[
            { id: 'architecture', label: 'Architecture & Schedule', icon: <Cpu size={15} /> },
            { id: 'strategies', label: '20+ TA Strategies', icon: <Compass size={15} /> },
            { id: 'confluence', label: 'Confluence & Dynamic R:R', icon: <Layers size={15} /> },
            { id: 'partial_booking', label: 'Partial Profit Booking', icon: <Split size={15} /> },
            { id: 'paper_vs_live', label: 'Paper vs Live Mode', icon: <ShieldCheck size={15} /> }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-accent-light text-surface-950 shadow-lg shadow-accent-DEFAULT/20'
                  : 'text-surface-300 hover:text-white bg-surface-900/60 hover:bg-surface-800 border border-surface-700/60'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab 1: ARCHITECTURE & LIFECYCLE */}
      {activeTab === 'architecture' && (
        <div className="space-y-6">
          {/* End-to-End Pipeline Card */}
          <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Cpu className="text-accent-light" size={20} />
                  End-to-End Execution Pipeline
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">
                  How high-frequency candle ticks transform into risk-controlled intraday executions.
                </p>
              </div>
              <span className="text-[11px] px-2.5 py-1 rounded-lg bg-surface-900 text-surface-300 border border-surface-700 font-mono">
                JSON-RPC Bridge
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
              {[
                {
                  step: '01',
                  title: 'Watchlist Feed',
                  desc: 'Ranks top liquid F&O candidates every scan cycle. SmartAPI WebSocket streams real-time tick updates.',
                  badge: 'Dynamic Universe'
                },
                {
                  step: '02',
                  title: '20 TA Strategies',
                  desc: 'Vectorized mathematical functions evaluate candles simultaneously across all symbols.',
                  badge: 'Signal Engine'
                },
                {
                  step: '03',
                  title: 'Confluence Gate',
                  desc: 'Requires ≥ 2 distinct indicator families to agree with the 50 EMA macro trend direction.',
                  badge: 'Consensus Filter'
                },
                {
                  step: '04',
                  title: 'Risk Geometry',
                  desc: 'Applies 1.0% noise buffer floor, enforces max capital allocation, and sizes orders with 5x MIS margin.',
                  badge: 'Position Sizing'
                },
                {
                  step: '05',
                  title: 'Order Dispatch',
                  desc: 'Routes smart limit pseudo-market orders via SmartAPI for live trading, or simulates fills in paper mode.',
                  badge: 'Execution Core'
                },
                {
                  step: '06',
                  title: 'Active Lifecycle',
                  desc: 'Trails stop-loss, books 50% at Target 1, ratchets runner to breakeven, and triggers 15:15 auto square-off.',
                  badge: 'Risk Monitor'
                }
              ].map((item, idx) => (
                <div
                  key={idx}
                  className="relative flex flex-col justify-between bg-surface-900/80 border border-surface-700/80 rounded-xl p-4 hover:border-accent-light/50 transition-all group"
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="w-6 h-6 rounded-lg bg-accent-light/10 text-accent-light flex items-center justify-center text-xs font-bold font-mono border border-accent-light/20">
                        {item.step}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded bg-surface-800 text-surface-400 border border-surface-700/50">
                        {item.badge}
                      </span>
                    </div>
                    <h3 className="font-semibold text-white text-sm mb-1.5 group-hover:text-accent-light transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-xs text-surface-400 leading-relaxed">
                      {item.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Intraday Trading Schedule & Safeguards (Timeline Format) */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Clock className="text-accent-light" size={18} />
                  Intraday Market Session & Trading Window Schedule
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  The automated scanner enforces disciplined time gates to avoid low-liquidity whipsaws and exchange penalties.
                </p>
              </div>
              <span className="text-xs px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/20 self-start sm:self-auto font-mono">
                Indian Standard Time (IST)
              </span>
            </div>

            {/* Visual Timeline Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Window 1 */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-loss-light/20 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-white bg-surface-800 px-2.5 py-1 rounded border border-surface-700">
                      09:15 – 09:30 AM
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-loss-light/10 text-loss-light border border-loss-light/20 flex items-center gap-1">
                      <Lock size={10} /> Shielded
                    </span>
                  </div>
                  <h4 className="font-bold text-white text-sm mt-2">Opening 15-Minute Volatility Shield</h4>
                  <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                    New entries are gated during the initial opening rush. This prevents getting stopped out by wide opening spreads, fakeout wicks, and order queue chaos.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-surface-800 text-[11px] text-surface-500 font-mono">
                  Gate: Entry Paused (noEntryFirstMins = 15)
                </div>
              </div>

              {/* Window 2 */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-profit-light/30 flex flex-col justify-between relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-profit-light/5 rounded-full blur-xl pointer-events-none" />
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-profit-light bg-profit-light/10 px-2.5 py-1 rounded border border-profit-light/20">
                      09:30 – 11:45 AM
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-profit-light/15 text-profit-light border border-profit-light/30 flex items-center gap-1">
                      <Zap size={10} /> Active
                    </span>
                  </div>
                  <h4 className="font-bold text-white text-sm mt-2">Morning Momentum Session</h4>
                  <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                    Primary morning window. Highest volume and momentum setups (ORB, Keltner Breakouts, CPR Reversals) are evaluated and executed here.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-surface-800 text-[11px] text-profit-light/80 font-mono">
                  Gate: High-Probability Trading Enabled
                </div>
              </div>

              {/* Window 3 */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-warning-light/20 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-warning-light bg-warning-light/10 px-2.5 py-1 rounded border border-warning-light/20">
                      11:45 AM – 01:00 PM
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-warning-light/10 text-warning-light border border-warning-light/20 flex items-center gap-1">
                      <Clock size={10} /> Paused
                    </span>
                  </div>
                  <h4 className="font-bold text-white text-sm mt-2">Midday Lull & Lunch Consolidation</h4>
                  <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                    Market turnover drops across domestic equities. New entries are restricted to avoid getting caught in low-volume sideways consolidation chop.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-surface-800 text-[11px] text-surface-500 font-mono">
                  Gate: Existing trades managed; new entries paused
                </div>
              </div>

              {/* Window 4 */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-accent-light/30 flex flex-col justify-between relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-accent-light/5 rounded-full blur-xl pointer-events-none" />
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-accent-light bg-accent-light/10 px-2.5 py-1 rounded border border-accent-light/20">
                      01:00 – 03:00 PM
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-accent-light/15 text-accent-light border border-accent-light/30 flex items-center gap-1">
                      <Flame size={10} /> Active
                    </span>
                  </div>
                  <h4 className="font-bold text-white text-sm mt-2">Afternoon Session & European Crossover</h4>
                  <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                    Turnover accelerates as European markets open (1:00–2:00 PM Golden Window). Strong trend continuations and volume delta expansions take place until 3:00 PM.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-surface-800 text-[11px] text-accent-light/80 font-mono">
                  Gate: Afternoon High-Conviction Entries
                </div>
              </div>

              {/* Window 5 */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-surface-300 bg-surface-800 px-2.5 py-1 rounded border border-surface-700">
                      03:00 PM Cutoff
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-surface-800 text-surface-400 border border-surface-700 flex items-center gap-1">
                      <AlertCircle size={10} /> Hard Cutoff
                    </span>
                  </div>
                  <h4 className="font-bold text-white text-sm mt-2">Intraday Entry Stop</h4>
                  <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                    Zero new trades are allowed after 3:00 PM. Prevents opening positions that lack enough remaining market duration to reach target before square-off.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-surface-800 text-[11px] text-surface-500 font-mono">
                  Gate: noNewTradesAfter = "15:00"
                </div>
              </div>

              {/* Window 6 */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-loss-light/40 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-loss-light bg-loss-light/10 px-2.5 py-1 rounded border border-loss-light/20">
                      03:15 PM Square-Off
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-loss-light/15 text-loss-light border border-loss-light/30 flex items-center gap-1">
                      <ShieldCheck size={10} /> Auto-Exit
                    </span>
                  </div>
                  <h4 className="font-bold text-white text-sm mt-2">Mandatory Intraday Square-Off</h4>
                  <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                    All remaining open intraday positions are automatically closed at market price. Protects your account from broker auto-square-off penalty charges.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-surface-800 text-[11px] text-loss-light font-mono">
                  Gate: squareOffTime = "15:15"
                </div>
              </div>
            </div>

            <div className="p-3 bg-surface-950/60 rounded-xl border border-surface-700/60 flex items-center gap-2 text-xs text-surface-400">
              <Info size={16} className="text-accent-light shrink-0" />
              <span>
                <strong>Note on Virtual / Paper Testing:</strong> Outside regular market hours (before 9:15 AM or after 3:30 PM), time gating automatically unlocks in development/paper mode so you can test strategies and signal functions freely.
              </span>
            </div>
          </div>

          {/* Core Risk & Money Management Rules */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg">
            <h3 className="font-bold text-white text-base flex items-center gap-2 mb-4">
              <Percent className="text-accent-light" size={18} />
              Mathematical Risk Architecture & Position Sizing
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs text-surface-300">
              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/70 space-y-1.5">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <ShieldCheck size={16} className="text-profit-light" />
                  1.0% Noise Buffer Floor
                </div>
                <p className="text-surface-400 leading-relaxed">
                  Any strategy with a tight raw SL (e.g. 0.4%–0.5%) is automatically widened to the 1.0% safety floor, ensuring normal intraday tick noise doesn't trigger false stop-outs.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/70 space-y-1.5">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Target size={16} className="text-accent-light" />
                  Capital Allocation & MIS
                </div>
                <p className="text-surface-400 leading-relaxed">
                  Position quantity is calculated based on configured capital per trade (e.g. ₹10,000–₹20,000) factoring 5x intraday leverage (20% margin requirement).
                </p>
              </div>

              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/70 space-y-1.5">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <AlertCircle size={16} className="text-loss-light" />
                  Daily Loss Circuit Breaker
                </div>
                <p className="text-surface-400 leading-relaxed">
                  If combined daily realized + unrealized loss hits the configured limit (e.g. -₹2,000), the engine immediately stops opening new trades and halts for the remainder of the day.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/70 space-y-1.5">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <TrendingUp size={16} className="text-warning-light" />
                  Adaptive Trailing SL
                </div>
                <p className="text-surface-400 leading-relaxed">
                  Once a trade reaches +1.0R profit cushion, an ATR-based trailing stop ratchets behind the high-water mark, guaranteeing paper gains are protected against sudden reversals.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: STRATEGIES CATALOG */}
      {activeTab === 'strategies' && (
        <div className="space-y-6">
          {/* Filter & Search Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-surface-800/90 p-4 rounded-2xl border border-surface-700/80 shadow-md">
            <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
              {['All', 'Smart Money', 'Breakout', 'Trend', 'Momentum', 'Oscillator', 'Intraday'].map(cat => (
                <button
                  key={cat}
                  onClick={() => setStrategyFilter(cat)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-all ${
                    strategyFilter === cat
                      ? 'bg-accent-light text-surface-950 font-bold shadow'
                      : 'bg-surface-900 text-surface-400 hover:text-white hover:bg-surface-700 border border-surface-700/50'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <span className="text-xs text-surface-400 whitespace-nowrap font-mono hidden md:inline">
                {filteredStrategies.length} of {STRATEGIES_LIST.length} strategies
              </span>
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-2.5 text-surface-500" size={15} />
                <input
                  type="text"
                  placeholder="Search rules or indicators..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-surface-900 border border-surface-700 rounded-xl text-xs text-white placeholder-surface-500 focus:outline-none focus:border-accent-light"
                />
              </div>
            </div>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredStrategies.map((s, idx) => (
              <div
                key={idx}
                className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-5 hover:border-accent-light/50 transition-all flex flex-col justify-between group shadow-sm hover:shadow-xl hover:-translate-y-0.5"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2.5">
                    <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-surface-900 text-accent-light border border-surface-700">
                      {s.category}
                    </span>
                    <span className="text-[11px] font-mono text-profit-light font-bold">
                      {s.winRateOrRank}
                    </span>
                  </div>

                  <h3 className="font-bold text-white text-base group-hover:text-accent-light transition-colors mb-3">
                    {s.name}
                  </h3>

                  <div className="space-y-2.5 text-xs text-surface-400 mb-4">
                    <div>
                      <span className="text-surface-500 uppercase tracking-wider font-bold text-[10px] block">
                        Trigger Rules:
                      </span>
                      <p className="text-surface-200 mt-0.5 leading-relaxed">{s.triggerRules}</p>
                    </div>
                    <div>
                      <span className="text-surface-500 uppercase tracking-wider font-bold text-[10px] block">
                        Indicators:
                      </span>
                      <p className="text-surface-300 mt-0.5 font-mono text-[11px] bg-surface-900/80 px-2 py-1 rounded border border-surface-700/40">
                        {s.indicators}
                      </p>
                    </div>
                    <div>
                      <span className="text-surface-500 uppercase tracking-wider font-bold text-[10px] block">
                        Quant Edge:
                      </span>
                      <p className="text-surface-300 mt-0.5 leading-relaxed">{s.whyItWorks}</p>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-surface-700/80 flex items-center justify-between text-xs">
                  <span className="text-surface-400 font-medium">Target R:R:</span>
                  <span className="font-bold text-white px-2.5 py-1 bg-surface-900 rounded-lg border border-surface-700 font-mono text-xs">
                    {s.rrRatio}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: CONFLUENCE & R:R ENGINE */}
      {activeTab === 'confluence' && (
        <div className="space-y-6">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Layers className="text-accent-light" size={20} />
                  Multi-Family Confluence Architecture
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">
                  Eliminating false breakouts through independent mathematical voting.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/30">
                Min 2 Distinct Families
              </span>
            </div>

            <p className="text-sm text-surface-300 leading-relaxed mb-6">
              A single technical indicator firing is statistically insufficient to overcome exchange friction and slippage. The platform groups all 20 strategies into five independent indicator families. An order is approved <strong>only when multiple distinct families agree on the same direction</strong> and align with the 50-period EMA macro trend.
            </p>

            {/* 5 Families Cards */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-8">
              {[
                { name: 'Trend Family', examples: '50 EMA, Supertrend, PSAR', role: 'Confirms prevailing macro direction & prevents counter-trend traps' },
                { name: 'Smart Money Family', examples: 'CPR, Liquidity Grab, CMF Flow', role: 'Tracks institutional footprint & resting liquidity sweeps' },
                { name: 'Volatility Family', examples: 'Keltner Channel, Bollinger Bands', role: 'Validates explosive expansion out of tight consolidation' },
                { name: 'Oscillator Family', examples: 'Williams %R, CCI, Stochastic', role: 'Pinpoints statistical exhaustion & cycle inflection pivots' },
                { name: 'Momentum Family', examples: 'MACD, True Strength (TSI), ADX', role: 'Confirms directional acceleration & candle expansion velocity' }
              ].map((fam, i) => (
                <div key={i} className="bg-surface-900/90 p-4 rounded-xl border border-surface-700/80 flex flex-col justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-white mb-1">{fam.name}</h4>
                    <p className="text-[11px] font-mono text-accent-light mb-2">{fam.examples}</p>
                    <p className="text-xs text-surface-400 leading-relaxed">{fam.role}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Dynamic R:R Scaling & Noise Floor Explanation */}
            <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-6 space-y-6">
              <div className="flex items-center justify-between border-b border-surface-800 pb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <BarChart3 className="text-accent-light" size={18} />
                    Dynamic Risk-to-Reward Geometry & The 1.0% Noise Buffer
                  </h3>
                  <p className="text-xs text-surface-400 mt-1">
                    How the system automatically adapts stop-losses and targets based on strategy characteristics and intraday noise.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-xs text-surface-300">
                {/* Breakout Model */}
                <div className="p-5 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-white text-sm flex items-center gap-2">
                      <Zap size={16} className="text-warning-light" />
                      High-Asymmetry Breakout Setups (1 : 3.0 to 1 : 4.0 R:R)
                    </h4>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-warning-light/10 text-warning-light border border-warning-light/30">
                      Asymmetric Payoff
                    </span>
                  </div>
                  <ul className="space-y-2 leading-relaxed text-surface-400">
                    <li>
                      • <strong className="text-white">Setup Profile:</strong> Strategies like Keltner Channel and Donchian Breakouts trigger when volatility explodes out of tight consolidation.
                    </li>
                    <li>
                      • <strong className="text-white">The Noise Problem:</strong> Pure breakout indicators often suggest an ultra-tight technical stop-loss (e.g. 0.4%–0.5% below the trigger candle). In real market conditions, random micro-wicks frequently hit tight stops before the true trend move unfolds.
                    </li>
                    <li>
                      • <strong className="text-white">Noise Floor Expansion:</strong> The Confluence Gate automatically widens any stop-loss below 1.0% to the <strong>1.0% minimum safety floor</strong>.
                    </li>
                    <li>
                      • <strong className="text-white">Edge Preservation:</strong> To maintain the strategy's statistical edge, the target is proportionately expanded:
                      <div className="mt-1 font-mono text-[11px] text-accent-light bg-surface-900 p-2 rounded border border-surface-700">
                        Target Distance = 1.0% Safety SL × Strategy Ratio (e.g., 1.0% × 4 = 4.0% Target)
                      </div>
                    </li>
                  </ul>
                </div>

                {/* Continuation Model */}
                <div className="p-5 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-white text-sm flex items-center gap-2">
                      <TrendingUp size={16} className="text-profit-light" />
                      High-Probability Continuation Setups (1 : 2.0 R:R)
                    </h4>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-profit-light/10 text-profit-light border border-profit-light/30">
                      High Hit-Rate
                    </span>
                  </div>
                  <ul className="space-y-2 leading-relaxed text-surface-400">
                    <li>
                      • <strong className="text-white">Setup Profile:</strong> Strategies like CMF Institutional Flow, CPR Pivots, and VWAP Pullbacks capitalize on steady institutional volume accumulation.
                    </li>
                    <li>
                      • <strong className="text-white">Balanced Geometry:</strong> Optimized for high-frequency baseline profit and rapid target execution with a standard 1:2 Risk-to-Reward ratio.
                    </li>
                    <li>
                      • <strong className="text-white">Standard Alignment:</strong> The stop-loss is placed at the 1.0% noise buffer floor, and the target is calculated at exactly 2.0 × risk distance:
                      <div className="mt-1 font-mono text-[11px] text-profit-light bg-surface-900 p-2 rounded border border-surface-700">
                        Target Distance = 1.0% Safety SL × 2.0 = 2.0% Target (1:2 R:R)
                      </div>
                    </li>
                    <li>
                      • <strong className="text-white">Quant Expectancy:</strong> Provides consistent daily equity curve progression while higher-asymmetry breakout trades capture large tail gains.
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: PARTIAL PROFIT BOOKING */}
      {activeTab === 'partial_booking' && (
        <div className="space-y-6">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Split className="text-accent-light" size={20} />
                  Two-Stage Multi-Target Scaling & Breakeven Protection
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">
                  Locking in guaranteed gains while letting trend runners capture extended profits risk-free.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/30">
                50% Milestone Exit
              </span>
            </div>

            <p className="text-sm text-surface-300 leading-relaxed mb-6">
              In intraday equities, large breakout moves rarely happen in a single straight line. The execution engine automatically divides positions into a 2-stage lifecycle to protect profits against midday market pullbacks:
            </p>

            {/* 3 Steps */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 relative flex flex-col justify-between">
                <div>
                  <span className="w-8 h-8 rounded-xl bg-accent-light/15 text-accent-light flex items-center justify-center font-bold font-mono text-xs mb-3 border border-accent-light/30">
                    01
                  </span>
                  <h3 className="font-bold text-white text-sm mb-1.5">Dual-Target Entry</h3>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    The position opens with 100% quantity. Target 1 is set at 1:2 R:R (e.g. +2.0%), while Target 2 is placed at the full setup target (e.g. +4.0%).
                  </p>
                </div>
              </div>

              <div className="bg-surface-900/90 border border-profit-light/30 rounded-xl p-5 relative flex flex-col justify-between">
                <div>
                  <span className="w-8 h-8 rounded-xl bg-profit-light/15 text-profit-light flex items-center justify-center font-bold font-mono text-xs mb-3 border border-profit-light/30">
                    02
                  </span>
                  <h3 className="font-bold text-white text-sm mb-1.5">Target 1: Lock 50% Profit</h3>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    When price reaches Target 1, 50% of the position is exited immediately at market price, crediting realized profit directly into your cash balance.
                  </p>
                </div>
              </div>

              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 relative flex flex-col justify-between">
                <div>
                  <span className="w-8 h-8 rounded-xl bg-surface-800 text-white flex items-center justify-center font-bold font-mono text-xs mb-3 border border-surface-700">
                    03
                  </span>
                  <h3 className="font-bold text-white text-sm mb-1.5">Stop-Loss Ratchets to Breakeven</h3>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    The Stop Loss for the remaining 50% is instantly adjusted to the <strong>Entry Price</strong>. The remainder is now a completely risk-free runner targeting Target 2.
                  </p>
                </div>
              </div>
            </div>

            {/* Brokerage Safeguard Engine */}
            <div className="bg-gradient-to-r from-surface-900 via-surface-900 to-surface-800 border border-surface-700/80 rounded-xl p-6">
              <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-2">
                <ShieldCheck className="text-profit-light" size={18} />
                Smart Brokerage Safeguard (Preventing Fee Drag)
              </h3>
              <p className="text-xs text-surface-300 leading-relaxed">
                Angel One charges <strong>₹20 per executed order</strong> (plus statutory taxes & GST ≈ ₹23.60). Splitting an exit into two transactions incurs an extra order fee. To guarantee this cost never erodes returns, the engine enforces an automatic <strong>₹250 Minimum Profit Threshold</strong>:
              </p>

              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-4 bg-surface-950/70 rounded-xl border border-profit-light/20 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-profit-light font-bold">
                    <CheckCircle2 size={15} />
                    Standard Trade Size (Capital Allocation ≥ ₹10,000)
                  </div>
                  <p className="text-surface-400 leading-relaxed">
                    50% profit at Target 1 yields substantial return (e.g. +₹1,000+). Spending ₹23.60 to lock in that gain and turn the remaining runner into a 100% risk-free trade is mathematically superior.
                  </p>
                </div>

                <div className="p-4 bg-surface-950/70 rounded-xl border border-warning-light/20 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-warning-light font-bold">
                    <AlertCircle size={15} />
                    Micro / Small Position (Low Capital Allocation)
                  </div>
                  <p className="text-surface-400 leading-relaxed">
                    If 50% profit would generate under ₹250, splitting would cause fees to consume over 10% of earnings. The engine automatically bypasses partial scaling and uses a <strong>single full exit at target</strong>.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: PAPER VS LIVE TRADING */}
      {activeTab === 'paper_vs_live' && (
        <div className="space-y-6">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <HelpCircle className="text-accent-light" size={20} />
                  Virtual Paper Sandbox vs Live SmartAPI Trading
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">
                  Identical mathematical quantitative core with zero-risk forward validation.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/30">
                Identical Quant Scanner
              </span>
            </div>

            <p className="text-sm text-surface-300 leading-relaxed mb-6">
              The Paper Trading engine is not a toy backtester. It executes against real live tick feeds from Angel One SmartAPI and routes through the exact same Python scanner, multi-family confluence gate, and risk management algorithms as live trading.
            </p>

            <div className="overflow-x-auto rounded-xl border border-surface-700/80">
              <table className="w-full text-xs text-left">
                <thead className="bg-surface-900 text-surface-400 uppercase tracking-wider font-semibold border-b border-surface-700">
                  <tr>
                    <th className="p-4 font-bold text-white">System Component</th>
                    <th className="p-4 text-accent-light font-bold">Virtual Paper Sandbox</th>
                    <th className="p-4 text-profit-light font-bold">Live SmartAPI Trading</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700/60 bg-surface-900/40">
                  {[
                    {
                      dim: 'Strategy Scanners & Signals',
                      paper: 'Identical (20 Strategies scan simultaneously across active universe)',
                      live: 'Identical (Executes on the exact same Python scanner)'
                    },
                    {
                      dim: 'Confluence Gate & Multi-Family Voting',
                      paper: 'Identical (Requires ≥ 2 families + 50 EMA trend check)',
                      live: 'Identical (Extra backstop: Confidence ≥ 85% in Auto mode)'
                    },
                    {
                      dim: 'Risk-to-Reward & Noise Buffer Floor',
                      paper: 'Identical (1.0% minimum SL buffer + 1:2 or 1:4 Target)',
                      live: 'Identical (Exact calculated price levels routed to broker)'
                    },
                    {
                      dim: 'Partial Booking & Breakeven Ratchet',
                      paper: 'Supported (Books 50% at Target 1, ratchets virtual SL)',
                      live: 'Supported (Dispatches partial limit order, ratchets broker stop)'
                    },
                    {
                      dim: 'Order Dispatch Mechanism',
                      paper: 'Simulated fill at incoming real-time tick price',
                      live: 'Real LIMIT orders placed via SmartAPI on NSE/BSE'
                    },
                    {
                      dim: 'Brokerage & Statutory Taxes',
                      paper: '₹0 (Gross theoretical P&L tracking)',
                      live: '₹20/order brokerage + STT + Exchange fees + GST'
                    },
                    {
                      dim: 'Execution Modes',
                      paper: 'Always automatic simulation in local storage',
                      live: 'Toggle between "Confirm Mode" (manual review) and "Auto Mode"'
                    }
                  ].map((row, i) => (
                    <tr key={i} className="hover:bg-surface-700/40 transition-colors">
                      <td className="p-4 font-semibold text-white">{row.dim}</td>
                      <td className="p-4 text-surface-300 leading-relaxed">{row.paper}</td>
                      <td className="p-4 text-surface-300 leading-relaxed">{row.live}</td>
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
