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
  Flame,
  Send,
  Smartphone,
  ShieldAlert,
  Terminal,
  Radio,
  Scale,
  Ban,
  Filter,
  Award
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
  const [activeTab, setActiveTab] = useState<'architecture' | 'quant_edge' | 'strategies' | 'confluence' | 'partial_booking' | 'paper_vs_live' | 'telegram_control'>('architecture');
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
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Macro Screener</span>
              <span className="text-base font-bold text-accent-light font-mono">KER ≥ 0.28</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Friction Guard</span>
              <span className="text-base font-bold text-profit-light font-mono">≥ 3.5x Fee</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Daily Trade Cap</span>
              <span className="text-base font-bold text-warning-light font-mono">Max 8/Day</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Confluence</span>
              <span className="text-base font-bold text-white font-mono">≥ 2 Families</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Safety Floor</span>
              <span className="text-base font-bold text-profit-light font-mono">1.0% Min SL</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">60d Net Return</span>
              <span className="text-base font-bold text-profit-light font-mono">+120.2%</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="mt-6 pt-5 border-t border-surface-700/60 flex flex-wrap gap-2">
          {[
            { id: 'architecture', label: 'Architecture & Schedule', icon: <Cpu size={15} /> },
            { id: 'quant_edge', label: 'Quant Edge & KER Screener', icon: <TrendingUp size={15} /> },
            { id: 'strategies', label: '20+ TA Strategies', icon: <Compass size={15} /> },
            { id: 'confluence', label: 'Confluence & Dynamic R:R', icon: <Layers size={15} /> },
            { id: 'partial_booking', label: 'Partial Profit Booking', icon: <Split size={15} /> },
            { id: 'paper_vs_live', label: 'Paper vs Live Mode', icon: <ShieldCheck size={15} /> },
            { id: 'telegram_control', label: 'Telegram Remote Control', icon: <Send size={15} /> }
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
                  desc: 'Ranks liquid candidates using Daily Kaufman Efficiency Ratio (KER N=20 ≥ 0.28). SmartAPI WebSocket streams real-time tick updates.',
                  badge: 'KER Macro Universe'
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
                  desc: 'Applies 1.0% noise buffer floor, pre-trade statutory friction guard (≥3.5x), max 8 trades/day cap, and 5x MIS margin.',
                  badge: 'Quant Risk Geometry'
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

      {/* Tab: QUANT EDGE & KER SCREENER */}
      {activeTab === 'quant_edge' && (
        <div className="space-y-6">
          {/* Header Overview Card */}
          <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl p-6 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-accent-DEFAULT/5 rounded-full blur-3xl pointer-events-none" />
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
              <div>
                <div className="flex items-center gap-2">
                  <span className="p-2 bg-accent-light/10 text-accent-light rounded-xl border border-accent-light/20">
                    <TrendingUp size={20} />
                  </span>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Institutional Quant Edge & Pre-Trade Protection
                  </h2>
                </div>
                <p className="text-xs text-surface-400 mt-1 max-w-3xl leading-relaxed">
                  How the Kaufman Efficiency Ratio (KER), pre-trade statutory friction gating, daily trade limits, and systematic universe curation transform volatile high-beta equities into an audited <strong className="text-profit-light">+120.2% net gain</strong>.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/30 flex items-center gap-1.5">
                  <CheckCircle2 size={13} />
                  Audit Verified: +₹48,083 Net (60d)
                </span>
              </div>
            </div>

            {/* 4 Core Pillars KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-4 flex flex-col justify-between hover:border-accent-light/40 transition-colors">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-surface-400 tracking-wider">Regime Screener</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-light/10 text-accent-light border border-accent-light/20">Pre-Market</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-white mb-1">Daily KER ≥ 0.28</div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Evaluated daily over 20 sessions (N=20). Filters out noisy, mean-reverting chop while preserving directional momentum runners across the universe.
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-surface-800 text-[11px] font-mono text-accent-light/80">
                  Targeted Direction / Volatility
                </div>
              </div>

              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-4 flex flex-col justify-between hover:border-profit-light/40 transition-colors">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-surface-400 tracking-wider">Statutory Barrier</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-profit-light/10 text-profit-light border border-profit-light/20">Pre-Trade</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-profit-light mb-1">Payoff ≥ 3.5x Fees</div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Calculates exact Indian broker + STT + NSE + GST + Stamp Duty friction. Rejects orders whose target profit cannot clear 3.5x friction.
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-surface-800 text-[11px] font-mono text-profit-light/80">
                  Zero Low-Delta Fee Traps
                </div>
              </div>

              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-4 flex flex-col justify-between hover:border-warning-light/40 transition-colors">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-surface-400 tracking-wider">Discipline Cap</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-warning-light/10 text-warning-light border border-warning-light/20">Daily RMS</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-warning-light mb-1">Max 8 Trades/Day</div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Restricts execution to the top morning and European crossover momentum setups. Completely halts over-trading and late-session chop drift.
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-surface-800 text-[11px] font-mono text-warning-light/80">
                  Focus on High-Conviction Flow
                </div>
              </div>

              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-4 flex flex-col justify-between hover:border-surface-600 transition-colors">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-surface-400 tracking-wider">Dynamic Quality Gate</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-profit-light/10 text-profit-light border border-profit-light/20">Automated</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-white mb-1">Adaptive Screening</div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Dynamic noise exclusion handles chop and erratic whipsaws automatically via KER and liquidity checks, eliminating the need for rigid static stock blacklists.
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-surface-800 text-[11px] font-mono text-profit-light/80">
                  Dynamic Regime Selection
                </div>
              </div>
            </div>
          </div>

          {/* Section 1: Kaufman Efficiency Ratio (KER) Deep Dive */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-700/60 pb-4">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Scale className="text-accent-light" size={18} />
                  Kaufman Efficiency Ratio (KER): Macro Trend vs Noise Screener
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  Perry Kaufman's mathematical formulation for distinguishing directional runners from friction-heavy consolidation traps.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/20">
                  Daily Period: N = 20
                </span>
                <span className="text-xs font-mono px-3 py-1 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/20">
                  Threshold: KER ≥ 0.28
                </span>
              </div>
            </div>

            {/* Critical Architectural Placement Alert */}
            <div className="p-4 rounded-xl bg-accent-DEFAULT/10 border border-accent-DEFAULT/30 space-y-2">
              <div className="flex items-center gap-2 text-accent-light font-bold text-xs uppercase tracking-wider">
                <ShieldAlert size={15} />
                Strict Architectural Placement Rule
              </div>
              <p className="text-xs text-surface-300 leading-relaxed">
                <strong>Why KER is strictly evaluated on Daily Bars (N=20), never as an Intraday 15-Minute Trigger:</strong> Intraday volatility breakouts (such as Keltner Channel expansions and Donchian breakouts) naturally emerge from tight, compressed ranges where 15-minute price travel is minimal. Enforcing a high intraday KER chokes fresh breakouts at birth and forces late entries at extended exhaustion tops. By screening KER solely at the <strong>Daily Macro level before 09:15 IST</strong>, the engine selects smooth trending candidates while preserving instant, zero-lag breakout execution intraday.
              </p>
            </div>

            {/* Mathematical Formulation Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-surface-900/90 border border-surface-700/80 space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-surface-400 block">Step 1: Net Direction</span>
                <div className="p-2.5 rounded-lg bg-surface-950 font-mono text-sm text-accent-light border border-surface-800">
                  Direction = |Close[t] - Close[t-20]|
                </div>
                <p className="text-xs text-surface-400 leading-relaxed">
                  Net directional price displacement across the 20-day macro window, measuring end-to-end trend progress without regard to path.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-surface-900/90 border border-surface-700/80 space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-surface-400 block">Step 2: Cumulative Volatility</span>
                <div className="p-2.5 rounded-lg bg-surface-950 font-mono text-sm text-accent-light border border-surface-800">
                  Volatility = Σ |Close[i] - Close[i-1]|
                </div>
                <p className="text-xs text-surface-400 leading-relaxed">
                  The sum of all daily absolute price steps over the 20-day lookback, capturing every intraday swing and retracement.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-surface-900/90 border border-surface-700/80 space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-surface-400 block">Step 3: Efficiency Ratio</span>
                <div className="p-2.5 rounded-lg bg-surface-950 font-mono text-sm text-profit-light border border-surface-800">
                  KER = Direction / Volatility (0.0 to 1.0)
                </div>
                <p className="text-xs text-surface-400 leading-relaxed">
                  A perfect one-way line yields 1.0. A pure sideways random walk approaches 0.0. Candidates with KER ≥ 0.28 qualify for intraday trading.
                </p>
              </div>
            </div>

            {/* Comparison Cards: Approved vs Rejected */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-profit-DEFAULT/5 border border-profit-DEFAULT/30 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-profit-light font-bold text-sm">
                    <CheckCircle2 size={16} />
                    KER ≥ 0.28: Approved Trending Regimes
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-profit-light/15 text-profit-light border border-profit-light/30">
                    High Signal-to-Noise
                  </span>
                </div>
                <p className="text-xs text-surface-300 leading-relaxed">
                  Securities characterized by sustained directional order flow, clean consecutive price swings, and predictable pullbacks that respect moving averages and VWAP.
                </p>
                <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                  <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                    <div className="text-white font-bold">Directional Drift</div>
                    <div className="text-[10px] text-profit-light">Net Travel &gt; Noise</div>
                  </div>
                  <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                    <div className="text-white font-bold">Clean Swings</div>
                    <div className="text-[10px] text-profit-light">Respects 20 EMA</div>
                  </div>
                  <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                    <div className="text-white font-bold">High Follow-Thru</div>
                    <div className="text-[10px] text-profit-light">Expanded Targets</div>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-loss-DEFAULT/5 border border-loss-DEFAULT/30 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-loss-light font-bold text-sm">
                    <Ban size={16} />
                    KER &lt; 0.28: Rejected Consolidation Regimes
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-loss-light/15 text-loss-light border border-loss-light/30">
                    High Friction Traps
                  </span>
                </div>
                <p className="text-xs text-surface-300 leading-relaxed">
                  Securities locked in mean-reverting noise, overlapping wick candles, and frequent false-breakout whipsaws. Dynamically pruned pre-market without needing static exclusion lists.
                </p>
                <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                  <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                    <div className="text-white font-bold">Severe Chop</div>
                    <div className="text-[10px] text-loss-light">Random Walk Noise</div>
                  </div>
                  <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                    <div className="text-white font-bold">Overlapping Wicks</div>
                    <div className="text-[10px] text-loss-light">Frequent Stop Hunts</div>
                  </div>
                  <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                    <div className="text-white font-bold">Dynamic Skip</div>
                    <div className="text-[10px] text-loss-light">Filtered at Root</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Pre-Trade Statutory Indian Friction Guard */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-700/60 pb-4">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Percent className="text-profit-light" size={18} />
                  Pre-Trade Statutory Indian Friction Guard
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  Modeling complete regulatory charges, exchange turnover levies, and broker fees to eliminate low-delta traps.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/20">
                Gate: Expected Gain ≥ 3.5x Total Fees
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Fee Breakdown Table */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                  Indian Intraday Equity Statutory Cost Matrix (Angel One MIS)
                </h4>
                <div className="overflow-x-auto rounded-xl border border-surface-700/80">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-surface-900 text-surface-400 text-[11px] border-b border-surface-700">
                      <tr>
                        <th className="p-2.5">Charge Component</th>
                        <th className="p-2.5">Levy Rate</th>
                        <th className="p-2.5">Applicability</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-800 text-surface-300">
                      <tr>
                        <td className="p-2.5 font-semibold text-white">Angel One Brokerage</td>
                        <td className="p-2.5 text-accent-light">Flat ₹20 / order</td>
                        <td className="p-2.5">₹40.00 Round-Trip</td>
                      </tr>
                      <tr>
                        <td className="p-2.5 font-semibold text-white">STT (Securities Tax)</td>
                        <td className="p-2.5 text-warning-light">0.025%</td>
                        <td className="p-2.5">Sell Turnover Only</td>
                      </tr>
                      <tr>
                        <td className="p-2.5 font-semibold text-white">NSE Exchange Turnover</td>
                        <td className="p-2.5 text-surface-300">0.00297%</td>
                        <td className="p-2.5">Total (Buy + Sell) Turnover</td>
                      </tr>
                      <tr>
                        <td className="p-2.5 font-semibold text-white">State Stamp Duty</td>
                        <td className="p-2.5 text-surface-300">0.003%</td>
                        <td className="p-2.5">Buy Turnover Only</td>
                      </tr>
                      <tr>
                        <td className="p-2.5 font-semibold text-white">SEBI Turnover Charge</td>
                        <td className="p-2.5 text-surface-300">₹10 / Crore (0.0001%)</td>
                        <td className="p-2.5">Total Turnover</td>
                      </tr>
                      <tr>
                        <td className="p-2.5 font-semibold text-white">GST</td>
                        <td className="p-2.5 text-loss-light">18.00%</td>
                        <td className="p-2.5">On Brokerage + NSE + SEBI</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* The Gate Logic */}
              <div className="space-y-3 flex flex-col justify-between">
                <div className="space-y-2.5">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    The 3.5x Payoff Filter Algorithm
                  </h4>
                  <p className="text-xs text-surface-300 leading-relaxed">
                    Most retail algorithms fail in Indian markets because they celebrate ₹30 gross wins while silently paying ₹52 in round-trip regulatory fees. Our risk engine calculates exact statutory friction <em>before</em> sending the order to SmartAPI:
                  </p>
                  <div className="p-3 bg-surface-950 rounded-xl border border-surface-800 font-mono text-xs text-profit-light space-y-1">
                    <div>Est_Profit = Quantity * (Target1 - EntryPrice)</div>
                    <div>Est_Fees = ₹40 Brokerage + STT + Turnover + Stamp + GST</div>
                    <div className="text-white font-bold pt-1 border-t border-surface-800">
                      Condition: Est_Profit &gt;= (3.5 * Est_Fees)
                    </div>
                  </div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    If an opportunity's expected target payoff is smaller than 3.5x round-trip friction, the trade is rejected at the root. We only trade setups where the mathematical edge overwhelmingly dwarfs exchange and tax overhead.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Section 3 & 4: Daily Trade Cap & Dynamic Universe Filtering */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Daily Trade Cap */}
            <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-4">
              <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Zap className="text-warning-light" size={18} />
                  Portfolio-Level Daily Trade Cap
                </h3>
                <span className="text-xs font-mono px-3 py-1 rounded-full bg-warning-light/10 text-warning-light border border-warning-light/20">
                  Max 8 Trades / Day
                </span>
              </div>
              <p className="text-xs text-surface-300 leading-relaxed">
                Empirical quantitative backtesting revealed that over-trading after 12:30 PM significantly erodes daily alpha. Restricting total portfolio execution to the <strong>first 8 high-conviction signals</strong> generates maximum net edge:
              </p>
              <ul className="space-y-2.5 text-xs text-surface-300">
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={15} className="text-profit-light shrink-0 mt-0.5" />
                  <span><strong>Morning & European Session Concentration:</strong> Trades 1 through 8 capture the cleanest momentum expansion windows (09:30–11:45 and 13:00–14:30).</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={15} className="text-profit-light shrink-0 mt-0.5" />
                  <span><strong>Friction Suppression:</strong> Capping executions prevents paying 20+ broker tickets during noisy sideways consolidations.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={15} className="text-profit-light shrink-0 mt-0.5" />
                  <span><strong>Chronological Gate:</strong> Once the 8th trade is entered, new entries are locked, while active trailing stops and targets continue protecting current holdings.</span>
                </li>
              </ul>
            </div>

            {/* Dynamic Universe Screening & Strategy Optimization */}
            <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-4">
              <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Filter className="text-accent-light" size={18} />
                  Dynamic Universe Screening & Strategy Alignment
                </h3>
                <span className="text-xs font-mono px-3 py-1 rounded-full bg-surface-900 text-surface-300 border border-surface-700">
                  Dynamic Alpha Selection
                </span>
              </div>
              <div className="space-y-3 text-xs">
                <div>
                  <span className="font-semibold text-accent-light block mb-1">Mathematical Noise Pruning (KER-Driven):</span>
                  <p className="text-surface-300 leading-relaxed mb-2.5">
                    Instead of maintaining static, hardcoded symbol exclusion lists, the engine dynamically screens candidate scrips using the Kaufman Efficiency Ratio (KER). Underperforming or choppy stocks are filtered out naturally:
                  </p>
                  <div className="grid grid-cols-3 gap-2 font-mono text-[11px] text-center">
                    <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                      <span className="font-bold text-white">Chop Traps</span>
                      <p className="text-[10px] text-loss-light mt-0.5">KER &lt; 0.28 filtered</p>
                    </div>
                    <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                      <span className="font-bold text-white">Spread Drag</span>
                      <p className="text-[10px] text-warning-light mt-0.5">3.5x friction guard</p>
                    </div>
                    <div className="p-2 rounded-lg bg-surface-900 border border-surface-700">
                      <span className="font-bold text-white">Adaptive Flow</span>
                      <p className="text-[10px] text-profit-light mt-0.5">Zero manual lists</p>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-surface-800">
                  <span className="font-semibold text-warning-light block mb-1">Pruned 15m Lagging Sub-Strategies:</span>
                  <p className="text-surface-400 text-xs leading-relaxed">
                    <code>supertrend</code>, <code>mfi_exhaustion</code>, and <code>stochastic_reversal</code> are disabled by default. In 15-minute intraday trading, these lagging oscillators generate false reversals during strong institutional runaway trends.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Section 5: Audited 60-Day Backtest Scorecard */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-700/60 pb-4">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Award className="text-profit-light" size={18} />
                  Audited 60-Day Multi-Scrip Backtest Benchmark
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  High-Beta active equities universe evaluated tick-by-tick across 60 days with complete statutory Indian taxes deducted.
                </p>
              </div>
              <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-profit-light/15 text-profit-light border border-profit-light/30">
                ₹40,000 Starting Capital (5x MIS Margin)
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700/80 text-center">
                <span className="text-[10px] uppercase font-bold text-surface-400 block mb-1">Net Realized P&L</span>
                <span className="text-base sm:text-lg font-bold font-mono text-profit-light">+₹48,083.85</span>
              </div>
              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700/80 text-center">
                <span className="text-[10px] uppercase font-bold text-surface-400 block mb-1">Return on Capital</span>
                <span className="text-base sm:text-lg font-bold font-mono text-profit-light">+120.21%</span>
              </div>
              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700/80 text-center">
                <span className="text-[10px] uppercase font-bold text-surface-400 block mb-1">Profit Factor</span>
                <span className="text-base sm:text-lg font-bold font-mono text-white">1.47</span>
              </div>
              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700/80 text-center">
                <span className="text-[10px] uppercase font-bold text-surface-400 block mb-1">Total Executions</span>
                <span className="text-base sm:text-lg font-bold font-mono text-white">442 Trades</span>
              </div>
              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700/80 text-center">
                <span className="text-[10px] uppercase font-bold text-surface-400 block mb-1">Win Rate (Asymmetric)</span>
                <span className="text-base sm:text-lg font-bold font-mono text-accent-light">43.44%</span>
              </div>
              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700/80 text-center">
                <span className="text-[10px] uppercase font-bold text-surface-400 block mb-1">Trade Expectancy</span>
                <span className="text-base sm:text-lg font-bold font-mono text-profit-light">+₹108.79 / trd</span>
              </div>
            </div>

            {/* Explanatory Footer Note */}
            <div className="p-4 bg-surface-950/60 rounded-xl border border-surface-700/60 flex items-center gap-3 text-xs text-surface-400">
              <Info size={18} className="text-accent-light shrink-0" />
              <div className="leading-relaxed">
                <strong>Why 43.4% Win Rate generates +120% Return:</strong> The platform leverages strong positive asymmetry. Average winning trades generate <strong>+₹784.81</strong> (driven by 1:4.0 Keltner Channel and Donchian breakouts), while disciplined stop-losses and the 1.0% safety floor keep average losses to <strong>-₹410.40</strong>. You do not need a 90% win rate to achieve institutional performance—you only need positive expectancy and tight friction gating.
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

      {/* Tab 6: Telegram 2-Way Remote Control */}
      {activeTab === 'telegram_control' && (
        <div className="space-y-6 animate-fade-in">
          {/* Header Card */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute -right-10 -bottom-10 w-72 h-72 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="p-2 bg-sky-500/15 text-sky-400 rounded-xl border border-sky-500/30">
                    <Send size={20} />
                  </span>
                  <h2 className="text-xl font-bold text-white">2-Way Telegram Remote Control & Panic Switch</h2>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-sky-500/15 text-sky-400 border border-sky-500/30">
                    Interactive Bot
                  </span>
                </div>
                <p className="text-sm text-surface-300 max-w-3xl leading-relaxed">
                  Monitor your trading engine, check live unrealised P&L, inspect open positions, remotely start/stop market scanning, or trigger an instant emergency square-off directly from your smartphone.
                </p>
              </div>

              <div className="flex items-center gap-3 self-start md:self-auto">
                <div className="px-3.5 py-2 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
                  <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Protocol</span>
                  <span className="text-xs font-bold text-sky-400 font-mono">getUpdates Long-Poll</span>
                </div>
                <div className="px-3.5 py-2 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
                  <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Security</span>
                  <span className="text-xs font-bold text-profit-light font-mono">Chat ID Locked</span>
                </div>
              </div>
            </div>
          </div>

          {/* Commands Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              {
                cmd: '/status',
                tag: 'Monitoring',
                color: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
                desc: 'Returns live agent status (RUNNING/STOPPED), execution mode (AUTO/CONFIRM), count of active positions, today’s realised and unrealised P&L, win rate, and available equity margin.',
                example: '🤖 AGENT STATUS\n⚡ Engine: 🟢 RUNNING (Mode: AUTO)\n📊 Active Positions: 2\n💰 Today P&L: +₹1,450.00'
              },
              {
                cmd: '/positions',
                tag: 'Portfolio',
                color: 'text-accent-light bg-accent-DEFAULT/10 border-accent-DEFAULT/30',
                desc: 'Fetches real-time open positions from Angel One SmartAPI, displaying stock symbol, direction (BUY/SELL), quantity, average entry price, LTP, and net P&L in rupees and percent.',
                example: '📊 CURRENT OPEN POSITIONS\n🟢 RELIANCE (BUY × 15)\n  • Entry: ₹2,900 | LTP: ₹2,935\n  • P&L: +₹525.00 (+1.21%)'
              },
              {
                cmd: '/squareoff',
                tag: '🚨 Emergency Panic',
                color: 'text-loss-light bg-loss-DEFAULT/15 border-loss-DEFAULT/40',
                desc: 'Immediate emergency exit button. Cancels open tracking and sends market/exit limit orders to close all open intraday positions on Angel One, then halts the trading engine.',
                example: '🚨 EMERGENCY SQUARE-OFF\n⚡ Closed: 2 positions squared off\n🛑 Engine: Stopped\n⏱ Executed At: 14:15:02 IST'
              },
              {
                cmd: '/start auto',
                tag: 'Execution',
                color: 'text-profit-light bg-profit-DEFAULT/10 border-profit-DEFAULT/30',
                desc: 'Remotely activates the trading engine in full automated execution mode. Scanner will auto-place broker orders whenever a signal with ≥85% confidence and ≥2 confluence families appears.',
                example: '🚀 TRADING ENGINE STARTED\n🏷 Mode: AUTO\n🔍 Dynamic scanner & position monitoring active.'
              },
              {
                cmd: '/start confirm',
                tag: 'Safety',
                color: 'text-warning-light bg-warning-DEFAULT/10 border-warning-DEFAULT/30',
                desc: 'Activates the trading engine in confirmation mode. Signals are scanned and streamed to the desktop UI for your manual review without executing trades automatically.',
                example: '🚀 TRADING ENGINE STARTED\n🏷 Mode: CONFIRM\n🛡 Signals will await confirmation in UI.'
              },
              {
                cmd: '/stop',
                tag: 'Control',
                color: 'text-surface-300 bg-surface-700/30 border-surface-600/40',
                desc: 'Pauses market scanning and halts new trade generation. Existing open positions remain live and will exit upon reaching Targets or End-Of-Day RMS square-off.',
                example: '🛑 TRADING ENGINE STOPPED\nMarket scanning paused.\nExisting open positions remain live.'
              }
            ].map((card, i) => (
              <div key={i} className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 flex flex-col justify-between space-y-3 shadow-md hover:border-surface-600 transition-all">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-base font-mono font-bold text-white bg-surface-950 px-2.5 py-1 rounded-lg border border-surface-700">
                      {card.cmd}
                    </span>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${card.color}`}>
                      {card.tag}
                    </span>
                  </div>
                  <p className="text-xs text-surface-300 leading-relaxed">
                    {card.desc}
                  </p>
                </div>

                <div className="bg-surface-950/80 border border-surface-800 rounded-lg p-2.5 font-mono text-[11px] text-surface-400 whitespace-pre-line leading-snug">
                  {card.example}
                </div>
              </div>
            ))}
          </div>

          {/* Critical Safeguards & Power Outage Architecture */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-surface-800/80 border border-surface-700/80 rounded-2xl p-6 space-y-4">
              <div className="flex items-center gap-2.5 text-profit-light font-bold text-base">
                <ShieldAlert size={20} />
                <span>Strict Security: Private Chat ID Authorization</span>
              </div>
              <p className="text-xs text-surface-300 leading-relaxed">
                By default, Telegram bots can receive messages from anyone on the internet. To prevent unauthorized control over your trading capital, this application uses a <strong>strict cryptographic identity check</strong>:
              </p>
              <ul className="space-y-2 text-xs text-surface-300">
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-profit-light shrink-0 mt-0.5" />
                  <span>Every inbound message is verified against your personal numeric <code>chatId</code> configured in Settings.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-profit-light shrink-0 mt-0.5" />
                  <span>Messages from any other Telegram user are immediately rejected with an <em>Access Denied</em> alert.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-profit-light shrink-0 mt-0.5" />
                  <span><strong>Zero Port Forwarding:</strong> The bot uses long-polling (<code>getUpdates</code>), so your machine never opens incoming firewall ports.</span>
                </li>
              </ul>
            </div>

            <div className="bg-surface-800/80 border border-surface-700/80 rounded-2xl p-6 space-y-4">
              <div className="flex items-center gap-2.5 text-warning-light font-bold text-base">
                <Radio size={20} />
                <span>Power Outage & Network Failure Handling</span>
              </div>
              <p className="text-xs text-surface-300 leading-relaxed">
                If your local PC loses electricity or internet connection while you are away:
              </p>
              <ul className="space-y-2 text-xs text-surface-300">
                <li className="flex items-start gap-2">
                  <AlertCircle size={14} className="text-warning-light shrink-0 mt-0.5" />
                  <span><strong>Angel One Mobile App:</strong> Open the official Angel One mobile app on your smartphone to instantly view or exit open positions.</span>
                </li>
                <li className="flex items-start gap-2">
                  <AlertCircle size={14} className="text-warning-light shrink-0 mt-0.5" />
                  <span><strong>Intraday Auto Square-Off:</strong> All orders use <code>INTRADAY</code> (MIS). Angel One RMS automatically squares off positions at 3:15 PM IST.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-profit-light shrink-0 mt-0.5" />
                  <span><strong>Cloud VPS Recommendation:</strong> For 100% 24/7 uptime without power risk, host this bot headless on a cloud VPS (AWS, DigitalOcean, or Hetzner).</span>
                </li>
              </ul>
            </div>
          </div>

          {/* 60-Second Setup Guide */}
          <div className="bg-gradient-to-r from-sky-500/10 via-surface-800 to-surface-800 border border-sky-500/30 rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-2 text-sky-400 font-bold text-base">
              <Smartphone size={18} />
              <span>How to Set Up Remote Telegram Control in 60 Seconds</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-surface-300">
              <div className="bg-surface-900/80 p-4 rounded-xl border border-surface-700/60 space-y-1.5">
                <span className="font-bold text-white block">Step 1: Create Your Bot</span>
                <p>Open Telegram, search for <strong>@BotFather</strong>, and send <code>/newbot</code>. Choose a name and username to receive your <strong>Bot Token</strong>.</p>
              </div>
              <div className="bg-surface-900/80 p-4 rounded-xl border border-surface-700/60 space-y-1.5">
                <span className="font-bold text-white block">Step 2: Get Your Chat ID</span>
                <p>Search for <strong>@userinfobot</strong> on Telegram and tap Start. It will reply with your personal numeric <strong>Id</strong> (e.g. <code>987654321</code>).</p>
              </div>
              <div className="bg-surface-900/80 p-4 rounded-xl border border-surface-700/60 space-y-1.5">
                <span className="font-bold text-white block">Step 3: Save in Settings & Start</span>
                <p>Go to <strong>Settings &gt; Notifications</strong> in this app. Enter your Token &amp; Chat ID, click <strong>Save</strong>, open your bot chat and send <code>/status</code>!</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemGuide;
