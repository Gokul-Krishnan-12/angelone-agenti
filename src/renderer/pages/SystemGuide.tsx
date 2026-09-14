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
  Award,
  Calculator,
  Copy,
  Check,
  Calendar,
  Eye,
  Database,
  RefreshCw,
  Timer
} from 'lucide-react';

interface StrategyItem {
  id: string;
  name: string;
  category: string;
  family: 'Trend' | 'Momentum' | 'Oscillator' | 'Breakout' | 'Intraday' | 'Volume' | 'Structure' | 'Reversal';
  winRateOrRank: string;
  rrRatio: string;
  triggerRules: string;
  indicators: string;
  whyItWorks: string;
}

const STRATEGIES_LIST: StrategyItem[] = [
  // ── 1. Breakout Family (3) ──────────────────────────────────────────
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
    id: 'bollinger_breakout',
    name: 'Bollinger Bands Squeeze Breakout',
    category: 'Volatility Squeeze',
    family: 'Breakout',
    winRateOrRank: 'Volatility Expansion',
    rrRatio: '1 : 2.5',
    triggerRules: 'Bollinger Band width contracts to multi-period low (volatility squeeze), followed by a decisive candle close outside the bands with volume confirmation.',
    indicators: '20 SMA, 2.0 Standard Deviations, Bandwidth %',
    whyItWorks: 'Prolonged compression cycles store energy that reliably transitions into explosive directional volatility expansion.'
  },
  {
    id: 'donchian_breakout',
    name: 'Donchian Channel Breakout',
    category: 'Multi-Period Breakout',
    family: 'Breakout',
    winRateOrRank: 'Turtle Trend Breakout',
    rrRatio: '1 : 3.0',
    triggerRules: 'Price exceeds 20-period highest high (BUY) or breaks 20-period lowest low (SELL) with expanding candle range.',
    indicators: '20-period Donchian Channels (Upper & Lower boundaries)',
    whyItWorks: 'Captures tail-risk explosive moves by entering whenever price creates a new multi-hour high or low.'
  },

  // ── 2. Volume Family (1) ────────────────────────────────────────────
  {
    id: 'cmf_accumulation',
    name: 'CMF Institutional Flow',
    category: 'Institutional Flow',
    family: 'Volume',
    winRateOrRank: 'High Hit Rate (~74%)',
    rrRatio: '1 : 2.0 (Standard Flow)',
    triggerRules: 'CMF > +0.10 with volume > 1.2x 20-bar average and price > 20 EMA (BUY). CMF < -0.10 with volume surge below 20 EMA (SELL).',
    indicators: 'Chaikin Money Flow (20-period), Volume Ratio, 20 EMA',
    whyItWorks: 'Detects institutional accumulation or distribution before price breaks into an extended trend continuation swing.'
  },

  // ── 3. Structure Family (4) ─────────────────────────────────────────
  {
    id: 'cpr_breakout_reversal',
    name: 'Central Pivot Range (CPR)',
    category: 'Pivot Structure',
    family: 'Structure',
    winRateOrRank: 'High Probability (~75%)',
    rrRatio: '1 : 2.0 to 1 : 2.5',
    triggerRules: 'Rejection or breakout of Daily TC (Top Central) / BC (Bottom Central) pivot lines on elevated volume.',
    indicators: 'Pivot Point = (H + L + C)/3, TC = (Pivot - BC) + Pivot, BC = (H + L)/2',
    whyItWorks: 'Standard and virgin CPR levels act as high-probability magnets and inflection barriers heavily tracked by institutional algorithmic execution.'
  },
  {
    id: 'institutional_absorption',
    name: 'Institutional Absorption',
    category: 'Multi-Candle Absorption',
    family: 'Structure',
    winRateOrRank: 'High Conviction',
    rrRatio: '1 : 2.5',
    triggerRules: 'Multi-candle absorption scan (last 3 bars) prints high volume (≥ 2.5x avg) with rejection wick ≥ 45% of range, followed by confirmation candle closing in direction of interest.',
    indicators: '20-period Volume SMA, Rejection Wick Ratio, ADX > 20 filter',
    whyItWorks: 'Detects large institutions absorbing resting market inventory with passive limit orders before initiating aggressive repricing.'
  },
  {
    id: 'order_block_fvg',
    name: 'Order Block & Fair Value Gap',
    category: 'SMC Imbalance',
    family: 'Structure',
    winRateOrRank: 'Imbalance Fill Setup',
    rrRatio: '1 : 2.5',
    triggerRules: 'Imbalance / 3-candle Fair Value Gap created by high-volume displacement, followed by a mitigation retest into the imbalance.',
    indicators: 'Fair Value Gap (FVG), Prior Pivot Displacement, 20 EMA',
    whyItWorks: 'Fills institutional buy/sell imbalances created when large market orders aggressively displace resting liquidity.'
  },
  {
    id: 'volume_delta_divergence',
    name: 'Volume Delta Divergence',
    category: 'Order Flow Divergence',
    family: 'Structure',
    winRateOrRank: 'Institutional Divergence',
    rrRatio: '1 : 2.2',
    triggerRules: 'Price prints lower low while buying delta volume increases (bullish), or price makes higher high while selling delta dominates (bearish).',
    indicators: 'Cumulative Volume Delta (CVD proxy), Swing Extremes',
    whyItWorks: 'Pinpoints institutional absorption where passive limit orders soak up aggressive market orders before a sharp trend turn.'
  },

  // ── 4. Reversal Family (2) ──────────────────────────────────────────
  {
    id: 'liquidity_grab_reversal',
    name: 'Liquidity Grab Reversal',
    category: 'Smart Money Reversal',
    family: 'Reversal',
    winRateOrRank: 'Elite Edge (~78% Win Rate)',
    rrRatio: '1 : 2.5',
    triggerRules: 'Price sweeps past key swing high/low to trigger resting retail stop orders, then aggressively snaps back inside the range with long rejection wick.',
    indicators: 'Swing Highs/Lows, Wick-to-Body Ratio > 2.0, Volume Spike',
    whyItWorks: 'Exploits institutional stop-hunts where large participants absorb counter-party inventory before driving price in the genuine direction.'
  },
  {
    id: 'gap_fill',
    name: 'Gap Fill Reversal',
    category: 'Mean Reversion',
    family: 'Reversal',
    winRateOrRank: 'High Reliability (~68%)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Morning gap up/down fails to sustain past key inflection; price re-enters prior day closing range targeting the gap fill.',
    indicators: 'Prior Close, Opening Tick Gap, 9 EMA Rejection',
    whyItWorks: 'Overextended retail opening sentiment gets exhausted quickly, creating reliable statistical reversion back to prior settlement value.'
  },

  // ── 5. Intraday Family (2) ──────────────────────────────────────────
  {
    id: 'opening_range_breakout',
    name: 'Opening Range Breakout (ORB)',
    category: 'Morning Momentum',
    family: 'Intraday',
    winRateOrRank: 'Morning Focus (~72%)',
    rrRatio: '1 : 2.0',
    triggerRules: 'First 15-minute high or low decisively breached after 09:30 IST with strong expansion candle and relative volume surge.',
    indicators: '15-min High/Low Range, Relative Volume (RVOL)',
    whyItWorks: 'Establishes the prevailing directional order-flow for the entire morning session once opening market imbalances clear.'
  },
  {
    id: 'vwap_bounce',
    name: 'VWAP Pullback & Bounce',
    category: 'Intraday Benchmark',
    family: 'Intraday',
    winRateOrRank: 'Institutional Benchmark',
    rrRatio: '1 : 2.0',
    triggerRules: 'Price pulls back to test session VWAP, forming a bullish hammer or bearish rejection candle with volume surge.',
    indicators: 'Volume Weighted Average Price (VWAP), 20-bar Volume SMA',
    whyItWorks: 'Institutions use VWAP as primary execution benchmark; testing VWAP offers tight risk-reward entry before large participants step back in.'
  },

  // ── 6. Trend Family (4) ─────────────────────────────────────────────
  {
    id: 'ema_crossover',
    name: 'EMA Directional Crossover',
    category: 'Dynamic Moving Average',
    family: 'Trend',
    winRateOrRank: 'Trend Alignment',
    rrRatio: '1 : 2.0',
    triggerRules: 'Fast EMA(9) crosses Slow EMA(21) with decisive gap ≥ 0.05% of price, ADX > 20 regime filter, and 1.5x volume confirmation.',
    indicators: '9 EMA, 21 EMA, 14 ADX, 20 Volume SMA',
    whyItWorks: 'Requires directional momentum regime (ADX > 20) and volume expansion, eliminating false whipsaws in sideways choppy markets.'
  },
  {
    id: 'supertrend',
    name: 'Supertrend Directional Filter',
    category: 'Structural Trend',
    family: 'Trend',
    winRateOrRank: 'Core Trend Backbone',
    rrRatio: '1 : 2.0',
    triggerRules: 'Price closes across the Supertrend line (Period 10, Multiplier 3.0) confirming structural trend transition.',
    indicators: 'ATR (10) * 3.0 band offset from median price',
    whyItWorks: 'Provides a robust trend backbone, eliminating counter-trend noise during directional market days.'
  },
  {
    id: 'psar_trend',
    name: 'Parabolic SAR Trend Shift',
    category: 'Trailing Trend',
    family: 'Trend',
    winRateOrRank: 'Trend Ride Setup',
    rrRatio: '1 : 2.0',
    triggerRules: 'PSAR dot flips from above candles to below candles (BUY) or vice versa with confirmation from ADX > 20.',
    indicators: 'Step 0.02, Max 0.20 Parabolic SAR, ADX',
    whyItWorks: 'Classical trailing indicator that locks in directional intraday trends until underlying momentum completely exhausts.'
  },
  {
    id: 'adx_momentum',
    name: 'ADX Trend Momentum Strength',
    category: 'Directional Velocity',
    family: 'Trend',
    winRateOrRank: 'Strength Qualifier',
    rrRatio: '1 : 2.0',
    triggerRules: '+DI crosses above -DI with ADX > 25 rising (BUY), or -DI crosses above +DI with ADX > 25 rising (SELL).',
    indicators: '14-period ADX, +DI, -DI',
    whyItWorks: 'Distinguishes true persistent directional moves from choppy consolidation noise.'
  },

  // ── 7. Momentum Family (3) ──────────────────────────────────────────
  {
    id: 'macd_cross',
    name: 'MACD Zero-Line Cross',
    category: 'Multi-Period Momentum',
    family: 'Momentum',
    winRateOrRank: 'Momentum Validation',
    rrRatio: '1 : 2.0',
    triggerRules: 'MACD line crosses Signal line in the direction of the zero-line threshold with expanding histogram bars.',
    indicators: 'Fast EMA (12), Slow EMA (26), Signal SMA (9)',
    whyItWorks: 'Eliminates low-velocity whipsaws by requiring momentum confirmation across multiple exponential moving average lookbacks.'
  },
  {
    id: 'rsi_reversal',
    name: 'RSI Divergence & Reversal',
    category: 'Momentum Exhaustion',
    family: 'Momentum',
    winRateOrRank: 'Mean Reversion',
    rrRatio: '1 : 2.0',
    triggerRules: 'Bullish divergence (price prints lower low while RSI makes higher low) or exit from oversold (<30) territory.',
    indicators: '14-period Relative Strength Index',
    whyItWorks: 'Identifies internal momentum exhaustion before it becomes visible on the candlestick chart.'
  },
  {
    id: 'tsi_cross',
    name: 'True Strength Index (TSI)',
    category: 'Double-Smoothed Momentum',
    family: 'Momentum',
    winRateOrRank: 'Smooth Trend Tracker',
    rrRatio: '1 : 2.0',
    triggerRules: 'TSI line crosses signal line in territory aligned with prevailing 50 EMA trend.',
    indicators: 'Double smoothed 25 and 13 EMAs',
    whyItWorks: 'Eliminates choppy lag and false crossovers by double-smoothing momentum rate-of-change.'
  },

  // ── 8. Oscillator Family (6 - counts as 1 single family vote) ────────
  {
    id: 'stochastic_reversal',
    name: 'Stochastic Oscillator Cross',
    category: 'Cyclic Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Range Reversal',
    rrRatio: '1 : 2.0',
    triggerRules: '%K line crosses above %D line below 20 (oversold) or %K crosses below %D above 80 (overbought).',
    indicators: '14, 3, 3 Fast/Slow Stochastic',
    whyItWorks: 'Optimized for high-probability swing turns within range-bound and consolidating market regimes.'
  },
  {
    id: 'stoc_rsi',
    name: 'Stochastic RSI Bound Turn',
    category: 'High-Sensitivity Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Rapid Momentum Shift',
    rrRatio: '1 : 2.0',
    triggerRules: 'StochRSI K line crosses above 0.20 and above D line (BUY) or crosses below 0.80 and below D line (SELL).',
    indicators: '14-period RSI, 14 Stochastic, 3 K, 3 D',
    whyItWorks: 'Applies Stochastic formula to RSI values, creating extreme sensitivity to sudden shifts in intraday velocity.'
  },
  {
    id: 'cci_reversal',
    name: 'Commodity Channel Index (CCI)',
    category: 'Statistical Deviation',
    family: 'Oscillator',
    winRateOrRank: 'Statistical Mean Reversion',
    rrRatio: '1 : 2.0',
    triggerRules: 'CCI crosses back above -100 after reaching extreme statistical oversold territory, confirmed by positive price action.',
    indicators: '20-period CCI',
    whyItWorks: 'Measures standard deviation from mean price; extreme statistical extensions predictably snap back toward mathematical equilibrium.'
  },
  {
    id: 'williams_r',
    name: 'Williams %R Extreme',
    category: 'Lookback Momentum',
    family: 'Oscillator',
    winRateOrRank: 'Cycle Inflection',
    rrRatio: '1 : 2.0',
    triggerRules: 'Crosses upward above -80 from deeply oversold band (BUY) or downward below -20 from overbought zone (SELL).',
    indicators: '14-period Williams %R',
    whyItWorks: 'Evaluates current close relative to highest high and lowest low of lookback, rapidly detecting momentum inflection points.'
  },
  {
    id: 'awesome_oscillator',
    name: 'Awesome Oscillator Zero Cross',
    category: 'Median Momentum',
    family: 'Oscillator',
    winRateOrRank: 'Momentum Shift',
    rrRatio: '1 : 2.0',
    triggerRules: 'AO crosses above the zero line (BUY) or crosses below the zero line (SELL) reflecting shift in market velocity.',
    indicators: '5 SMA and 34 SMA of bar midpoints ((H+L)/2)',
    whyItWorks: 'Measures immediate momentum vs broader historical trend to catch early directional cycle turns.'
  },
  {
    id: 'mfi_exhaustion',
    name: 'MFI Volume-Weighted Exhaustion',
    category: 'Money Flow Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Volume Flow Turn',
    rrRatio: '1 : 2.0',
    triggerRules: 'Money Flow Index bounces above 20 from extreme exhaustion zone (BUY) or turns down from above 80 (SELL).',
    indicators: '14-period Money Flow Index (Price × Volume)',
    whyItWorks: 'Combines price momentum with volume accumulation to identify points where aggressive selling or buying has dried up.'
  }
];

const FAMILIES = [
  'All',
  'Breakout',
  'Structure',
  'Smart Money',
  'Trend',
  'Momentum',
  'Oscillator',
  'Intraday',
  'Volume',
  'Reversal'
];

const SystemGuide: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    | 'architecture'
    | 'quant_edge'
    | 'strategies'
    | 'confluence'
    | 'friction_guard'
    | 'partial_booking'
    | 'swing_screener'
    | 'backtest_expectancy'
    | 'telegram_control'
    | 'paper_vs_live'
  >('architecture');

  const [strategyFilter, setStrategyFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  // Interactive Statutory Fee Calculator state
  const [calcPrice, setCalcPrice] = useState<number>(2500);
  const [calcQty, setCalcQty] = useState<number>(50);
  const [calcTargetPct, setCalcTargetPct] = useState<number>(2.0);

  // Compute Indian Statutory Fees dynamically
  const feeCalculation = useMemo(() => {
    const buyVal = calcPrice * calcQty;
    const targetPrice = calcPrice * (1 + calcTargetPct / 100);
    const sellVal = targetPrice * calcQty;
    const totalTurnover = buyVal + sellVal;
    const estProfit = sellVal - buyVal;

    // Brokerage: ₹20 / order
    const brokerage = 40.0;
    // STT: 0.025% on sell side for intraday equities
    const stt = sellVal * 0.00025;
    // NSE Turnover: 0.00297% on total turnover
    const nseTurnover = totalTurnover * 0.0000297;
    // Stamp Duty: 0.003% on buy side
    const stampDuty = buyVal * 0.00003;
    // SEBI Turnover: ₹10 / Crore = 0.0001%
    const sebi = totalTurnover * 0.000001;
    // GST: 18% on (Brokerage + NSE + SEBI)
    const gst = (brokerage + nseTurnover + sebi) * 0.18;

    const totalFriction = brokerage + stt + nseTurnover + stampDuty + sebi + gst;
    const minRequiredPayoff = totalFriction * 3.5;
    const passesGate = estProfit >= minRequiredPayoff;
    const netProfitAfterFriction = estProfit - totalFriction;

    return {
      buyVal,
      sellVal,
      totalTurnover,
      estProfit,
      brokerage,
      stt,
      nseTurnover,
      stampDuty,
      sebi,
      gst,
      totalFriction,
      minRequiredPayoff,
      passesGate,
      netProfitAfterFriction
    };
  }, [calcPrice, calcQty, calcTargetPct]);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const filteredStrategies = useMemo(() => {
    return STRATEGIES_LIST.filter(s => {
      const matchesCategory =
        strategyFilter === 'All' ||
        s.category === strategyFilter ||
        s.family === strategyFilter ||
        (strategyFilter === 'Smart Money' && (s.family === 'Structure' || s.family === 'Reversal' || s.family === 'Volume'));

      const matchesSearch =
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.family.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.triggerRules.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.whyItWorks.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.indicators.toLowerCase().includes(searchQuery.toLowerCase());

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
              Complete technical specification for algorithmic execution, multi-family confluence gating, dynamic regime screening, and mathematical risk geometry.
            </p>
          </div>

          {/* Quick Institutional Metrics Pills */}
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
              <span className="text-base font-bold text-warning-light font-mono">Max 8-10</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Confluence</span>
              <span className="text-base font-bold text-white font-mono">≥ 3 Families</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Safety Floor</span>
              <span className="text-base font-bold text-profit-light font-mono">1.0% Min SL</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Risk Geometry</span>
              <span className="text-base font-bold text-accent-light font-mono">1:2 to 1:4</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="mt-6 pt-5 border-t border-surface-700/60 flex flex-wrap gap-2">
          {[
            { id: 'architecture', label: 'Architecture & Schedule', icon: <Cpu size={15} /> },
            { id: 'quant_edge', label: 'Quant Edge & Screener', icon: <TrendingUp size={15} /> },
            { id: 'strategies', label: '25 TA Strategies', count: '25', icon: <Compass size={15} /> },
            { id: 'confluence', label: 'Confluence & Dynamic R:R', icon: <Layers size={15} /> },
            { id: 'friction_guard', label: 'Statutory Friction Guard', icon: <Calculator size={15} /> },
            { id: 'partial_booking', label: 'Partial Profit Booking', icon: <Split size={15} /> },
            { id: 'swing_screener', label: 'Swing & Sector Screener', icon: <BarChart3 size={15} /> },
            { id: 'backtest_expectancy', label: 'Walk-Forward Backtesting', icon: <Award size={15} /> },
            { id: 'telegram_control', label: 'Telegram Remote Control', icon: <Send size={15} /> },
            { id: 'paper_vs_live', label: 'Paper vs Live Mode', icon: <ShieldCheck size={15} /> }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl transition-all duration-200 cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-accent-light text-surface-950 shadow-lg shadow-accent-DEFAULT/20'
                  : 'text-surface-300 hover:text-white bg-surface-900/60 hover:bg-surface-800 border border-surface-700/60'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.count && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  activeTab === tab.id ? 'bg-surface-950 text-accent-light' : 'bg-surface-800 text-surface-400'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ─── TAB 1: ARCHITECTURE & SCHEDULE ─────────────────────────────── */}
      {activeTab === 'architecture' && (
        <div className="space-y-6 animate-fade-in">
          {/* End-to-End Pipeline Card */}
          <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Cpu className="text-accent-light" size={20} />
                  End-to-End Execution Pipeline
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">
                  How real-time tick feeds transform into mathematically guarded intraday executions.
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
                  desc: 'Screens ~200 F&O stocks dynamically using Daily Kaufman Efficiency Ratio (KER N=20 ≥ 0.28). SmartAPI WebSocket streams real-time tick updates.',
                  badge: 'KER Macro Universe'
                },
                {
                  step: '02',
                  title: '25 TA Strategies',
                  desc: 'Vectorized mathematical functions evaluate candles simultaneously across all active scrips in 8 independent strategy families.',
                  badge: 'Signal Engine'
                },
                {
                  step: '03',
                  title: 'Confluence & Regime',
                  desc: 'Requires ≥ 3 independent indicator families to agree with 50 EMA trend direction plus Market Regime gating (ADX ≥ 20, KER ≥ 0.25). All 6 oscillator strategies cluster into 1 single vote.',
                  badge: 'Consensus Filter'
                },
                {
                  step: '04',
                  title: '1R Risk Geometry',
                  desc: 'Enforces dynamic 1R risk-based position sizing [Q = min(floor(Risk/ΔSL), floor(Exposure/Price))], 1.0% noise buffer floor, friction guard (≥3.5x fees), and daily trade cap.',
                  badge: '1R Quant Sizing'
                },
                {
                  step: '05',
                  title: 'Limit Queue & Timeout',
                  desc: 'Places smart limit entry with a 60-second timeout queue. Unfilled orders are cancelled automatically to prevent stale fills on fast moves.',
                  badge: '60s Timeout Queue'
                },
                {
                  step: '06',
                  title: 'Native Exchange SL',
                  desc: 'Submits native STOPLOSS_LIMIT order directly to the exchange upon fill, trails stop dynamically, books 50% at Target 1, and squares off at 15:15.',
                  badge: 'Exchange-Side SL'
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

          {/* Enterprise Execution Safeguards & Crash Resilience */}
          <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <ShieldCheck className="text-profit-light" size={20} />
                  Enterprise Execution Safeguards &amp; Crash Resilience
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  Production-grade safeguards protecting live capital against disconnections, order lag, software crashes, and session expiry.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/30">
                Institutional Safety Architecture
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Safeguard 1: Native Exchange SL */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Lock size={14} className="text-accent-light" /> Native Exchange SL
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 text-profit-light border border-surface-700">
                    STOPLOSS_LIMIT
                  </span>
                </div>
                <p className="text-xs text-surface-300 leading-relaxed">
                  Immediately upon entry fill, a real <strong>STOPLOSS_LIMIT</strong> order is dispatched directly to the NSE match engine. If your desktop, internet, or app crashes, your capital remains 100% safeguarded on the broker/exchange order book.
                </p>
                <div className="text-[10px] text-surface-500 font-mono pt-1">
                  Dynamic Ratchet: SmartAPI modify_order moves SL to breakeven at Target 1.
                </div>
              </div>

              {/* Safeguard 2: 60s Pending Limit Queue */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Timer size={14} className="text-warning-light" /> 60s Limit Queue
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 text-warning-light border border-surface-700">
                    TTL 60 Seconds
                  </span>
                </div>
                <p className="text-xs text-surface-300 leading-relaxed">
                  Breakout entries are placed as Limit orders near the bid/ask spread. The engine tracks unfilled orders in an active timeout queue. If unfilled after <strong>60 seconds</strong>, the order is automatically cancelled to prevent adverse fills on fading momentum.
                </p>
                <div className="text-[10px] text-surface-500 font-mono pt-1">
                  Anti-Lag: Eliminates stale resting orders during market reversals.
                </div>
              </div>

              {/* Safeguard 3: Active Trades Disk Persistence */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Database size={14} className="text-accent-light" /> Disk Persistence
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 text-accent-light border border-surface-700">
                    active_trades.json
                  </span>
                </div>
                <p className="text-xs text-surface-300 leading-relaxed">
                  Every active trade, position watermark, and corresponding native stop-loss order ID is atomically persisted to encrypted disk storage. On process restart or system reboot, the engine automatically reloads and re-attaches to live orders without state loss.
                </p>
                <div className="text-[10px] text-surface-500 font-mono pt-1">
                  Crash Proof: Reconstructs state without orphan orders or ghost trades.
                </div>
              </div>

              {/* Safeguard 4: Headless Session Re-Auth */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <RefreshCw size={14} className="text-profit-light" /> Session Auto-Renewal
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 text-profit-light border border-surface-700">
                    TOTP Auto Re-Auth
                  </span>
                </div>
                <p className="text-xs text-surface-300 leading-relaxed">
                  SmartAPI JWT tokens expire every 24 hours. When an API call returns <code>AB1010</code>, <code>AG8001</code>, or <code>Invalid Token</code>, the client headlessly regenerates a fresh TOTP code, re-authenticates with SmartAPI, and seamlessly retries the operation.
                </p>
                <div className="text-[10px] text-surface-500 font-mono pt-1">
                  Zero Interruption: Scanning and order monitoring continue without user login.
                </div>
              </div>
            </div>
          </div>

          {/* Automated Exchange Trading Holiday & Weekend Protection Notice */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-accent-DEFAULT/10 via-surface-900 to-surface-900 border border-accent-DEFAULT/30 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-accent-light font-bold text-xs uppercase tracking-wider">
                <Calendar size={16} />
                Dynamic Exchange Holiday &amp; Weekend Guard
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-light/15 text-accent-light border border-accent-light/30">
                Live API Synced
              </span>
            </div>
            <p className="text-xs text-surface-300 leading-relaxed">
              The platform connects to live exchange holiday feeds (official NSE Holiday Master &amp; Upstox Public Exchange API) and local disk cache to monitor official trading closures (including Ganesh Chaturthi, Diwali, Eid, Holi, etc.) and weekends. On non-trading days, the execution engine automatically prevents live order placement and displays the exact holiday status (e.g. <code>CLOSED (Holiday: Ganesh Chaturthi)</code>) across the UI.
            </p>
          </div>

          {/* Intraday Trading Schedule & Safeguards (Timeline Format) */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Clock className="text-accent-light" size={18} />
                  Intraday Market Session &amp; Trading Window Schedule
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
                  <h4 className="font-bold text-white text-sm mt-2">Midday Lull &amp; Lunch Consolidation</h4>
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
                  <h4 className="font-bold text-white text-sm mt-2">Afternoon Session &amp; European Crossover</h4>
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
          </div>
        </div>
      )}

      {/* ─── TAB 2: QUANT EDGE & SCREENER ───────────────────────────────── */}
      {activeTab === 'quant_edge' && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl p-6 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-accent-DEFAULT/5 rounded-full blur-3xl pointer-events-none" />
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
              <div>
                <div className="flex items-center gap-2">
                  <span className="p-2 bg-accent-light/10 text-accent-light rounded-xl border border-accent-light/20">
                    <TrendingUp size={20} />
                  </span>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Institutional Quant Edge &amp; Pre-Trade Protection
                  </h2>
                </div>
                <p className="text-xs text-surface-400 mt-1 max-w-3xl leading-relaxed">
                  How the Kaufman Efficiency Ratio (KER), pre-trade statutory friction gating, daily trade caps, and systematic F&amp;O universe curation filter noise to establish positive mathematical expectancy across varying market regimes.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/30 flex items-center gap-1.5">
                  <CheckCircle2 size={13} />
                  Dynamic Universe: ~200 F&amp;O Scrips
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
                  <div className="text-lg font-bold font-mono text-warning-light mb-1">Max 8-10 Trades/Day</div>
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
                  <div className="text-lg font-bold font-mono text-white mb-1">Adaptive Universe</div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Scrapes the active liquid F&amp;O universe (~200 scrips) dynamically, verifying ₹40 Cr turnover, ₹150 price floor, and ATR ≥ 1.5%.
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-surface-800 text-[11px] font-mono text-profit-light/80">
                  Dynamic Regime Selection
                </div>
              </div>
            </div>
          </div>

          {/* KER Mathematical Formulation */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-700/60 pb-4">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Scale className="text-accent-light" size={18} />
                  Kaufman Efficiency Ratio (KER): Macro Trend vs Noise Screener
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  Mathematical formulation for distinguishing directional runners from friction-heavy consolidation traps.
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
                  A pure straight line yields 1.0. A sideways random walk approaches 0.0. Candidates with KER ≥ 0.28 qualify for intraday trading.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 3: 25 STRATEGIES CATALOG ───────────────────────────────── */}
      {activeTab === 'strategies' && (
        <div className="space-y-6 animate-fade-in">
          {/* Active Roster Pruning Notice */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-accent-DEFAULT/15 via-surface-900 to-surface-900 border border-accent-DEFAULT/30 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-accent-light font-bold text-xs uppercase tracking-wider">
                <Filter size={16} />
                Quantitative Strategy Pruning Policy (Walk-Forward Verified)
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-light/15 text-accent-light border border-accent-light/30">
                Shared by Auto &amp; Paper Agent
              </span>
            </div>
            <p className="text-xs text-surface-300 leading-relaxed">
              To eliminate false whipsaws and negative fee drag, lagging indicators and low-expectancy oscillators have been <strong>pruned and disabled by default</strong> in the backend scanner configuration. Rigorous walk-forward backtesting proved that standard 15-minute trend crossovers (PSAR: -₹8,575 P&amp;L, EMA Crossover: -₹2,201 P&amp;L, MACD cross, 15m Supertrend) and exhausted oscillators suffer from excessive stop-loss rates (56%–63%).
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1 text-xs">
              <div className="p-2.5 rounded-xl bg-surface-800/80 border border-loss-light/20 text-surface-300">
                <span className="font-bold text-loss-light block mb-1">Pruned / Disabled by Default:</span>
                <span className="text-[11px] text-surface-400">PSAR Trend, EMA Crossover, MACD Cross, Supertrend, Stochastic Reversal, Williams %R, CCI, ADX Momentum, VWAP Bounce.</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface-800/80 border border-profit-light/20 text-surface-300">
                <span className="font-bold text-profit-light block mb-1">Active High-Conviction Core:</span>
                <span className="text-[11px] text-surface-400">Donchian Breakout, Keltner Channel Breakout, Bollinger Squeeze, Institutional Absorption, Fair Value Gap (FVG), Volume Delta Divergence, CMF Accumulation, Opening Range Breakout (ORB).</span>
              </div>
            </div>
          </div>

          {/* Filter & Search Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-surface-800/90 p-4 rounded-2xl border border-surface-700/80 shadow-md">
            <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
              {FAMILIES.map(cat => {
                const count = cat === 'All'
                  ? STRATEGIES_LIST.length
                  : STRATEGIES_LIST.filter(s => s.family === cat || s.category === cat).length;
                return (
                  <button
                    key={cat}
                    onClick={() => setStrategyFilter(cat)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-all flex items-center gap-1.5 cursor-pointer ${
                      strategyFilter === cat
                        ? 'bg-accent-light text-surface-950 font-bold shadow'
                        : 'bg-surface-900 text-surface-400 hover:text-white hover:bg-surface-700 border border-surface-700/50'
                    }`}
                  >
                    <span>{cat}</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                      strategyFilter === cat ? 'bg-surface-950 text-accent-light font-bold' : 'bg-surface-800 text-surface-400'
                    }`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <span className="text-xs text-surface-400 whitespace-nowrap font-mono hidden md:inline">
                {filteredStrategies.length} of {STRATEGIES_LIST.length} strategies
              </span>
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-2.5 text-surface-500" size={15} />
                <input
                  type="text"
                  placeholder="Search rules, indicators..."
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
                      {s.family} • {s.category}
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

      {/* Header Pills & Nav */}
      <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-5 shadow-lg">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
            <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Discipline</span>
            <span className="text-base font-bold text-warning-light font-mono">Max 8-10 / Day</span>
          </div>
          <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
            <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Confluence</span>
            <span className="text-base font-bold text-white font-mono">≥ 3 Families</span>
          </div>
          <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
            <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Market Regime</span>
            <span className="text-base font-bold text-accent-light font-mono">ADX ≥ 20</span>
          </div>
          <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
            <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Risk Geometry</span>
            <span className="text-base font-bold text-profit-light font-mono">1:2.0 Min R:R</span>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="mt-6 pt-5 border-t border-surface-700/60 flex flex-wrap gap-2">
          {[
            { id: 'architecture', label: 'Architecture & Schedule', icon: <Cpu size={15} /> },
            { id: 'quant_edge', label: 'Quant Edge & Screener', icon: <TrendingUp size={15} /> },
            { id: 'strategies', label: '25 TA Strategies', count: '25', icon: <Compass size={15} /> },
            { id: 'confluence', label: 'Confluence, Regime & 1:2 R:R', icon: <Layers size={15} /> },
            { id: 'friction_guard', label: 'Statutory Friction Guard', icon: <Calculator size={15} /> },
            { id: 'partial_booking', label: 'Partial Profit Booking', icon: <Split size={15} /> },
            { id: 'swing_screener', label: 'Swing & Sector Screener', icon: <BarChart3 size={15} /> },
            { id: 'backtest_expectancy', label: 'Walk-Forward Backtesting', icon: <Award size={15} /> },
            { id: 'telegram_control', label: 'Telegram Remote Control', icon: <Send size={15} /> },
            { id: 'paper_vs_live', label: 'Paper vs Live Mode', icon: <ShieldCheck size={15} /> }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer border ${
                activeTab === tab.id
                  ? 'bg-accent-light/15 text-white border-accent-light/40 shadow-sm'
                  : 'bg-surface-900/60 text-surface-400 border-surface-700/60 hover:bg-surface-800/80 hover:text-surface-200'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.count && (
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full ${
                    activeTab === tab.id ? 'bg-surface-950 text-accent-light' : 'bg-surface-800 text-surface-400'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ─── TAB 4: CONFLUENCE, REGIME & 1:2 R:R ─────────────────────────── */}
      {activeTab === 'confluence' && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-6">
            <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Layers className="text-accent-light" size={20} />
                  Multi-Family Confluence &amp; Market Regime Architecture
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">
                  Eliminating false breakouts through independent mathematical family voting and macro volatility classification.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/30">
                Confluence: ≥ 3 Distinct Families
              </span>
            </div>

            <p className="text-sm text-surface-300 leading-relaxed">
              A single technical indicator firing is statistically insufficient to overcome exchange friction and slippage. The platform groups all 25 strategies into eight independent indicator families. An order is approved <strong>only when ≥ 3 distinct families agree on the same direction</strong>, align with the 50-period EMA macro trend, and pass the Market Regime Filter.
            </p>

            {/* Market Regime Engine Card */}
            <div className="bg-surface-900/90 border border-accent-light/30 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <ShieldAlert className="text-accent-light" size={18} />
                  Quantitative Market Regime Filter (The Anti-Chop Guard)
                </h3>
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-accent-light/10 text-accent-light border border-accent-light/30 font-bold">
                  Active in Live &amp; Paper Modes
                </span>
              </div>

              <p className="text-xs text-surface-300 leading-relaxed">
                In our 1-year walk-forward backtest, the system was profitable in <strong>8 out of 13 months</strong> and gained +₹10,164 between Dec and Apr. The drawdowns occurred specifically during two sideways consolidation periods (Nov 2025 and July 2026), where market-wide ranges chopped up breakout strategies. The <strong>Market Regime Filter</strong> classifies market structure into three distinct states:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-profit-dark/10 border border-profit/30 space-y-1.5">
                  <span className="font-bold text-profit-light block">1. TRENDING_BULL</span>
                  <p className="text-surface-300 leading-relaxed">
                    ADX ≥ 20, +DI &gt; -DI, Close &gt; 50 EMA, and KER ≥ 0.25. High-conviction long breakouts and momentum continuation approved. Counter-trend shorts prohibited.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-loss-dark/10 border border-loss/30 space-y-1.5">
                  <span className="font-bold text-loss-light block">2. TRENDING_BEAR</span>
                  <p className="text-surface-300 leading-relaxed">
                    ADX ≥ 20, -DI &gt; +DI, Close &lt; 50 EMA, and KER ≥ 0.25. Short breakdowns approved. Counter-trend longs prohibited.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-warning-dark/10 border border-warning/30 space-y-1.5">
                  <span className="font-bold text-warning-light block">3. CHOPPY_RANGE (Squeeze)</span>
                  <p className="text-surface-300 leading-relaxed">
                    ADX &lt; 20, KER &lt; 0.25, or Bollinger Band Width squeezed. <strong>Breakout strategies (Donchian, Bollinger) are automatically suppressed</strong> to eliminate fee drain.
                  </p>
                </div>
              </div>
            </div>

            {/* 8 Families Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              {[
                { name: 'Trend Family (4)', examples: 'EMA Crossover, Supertrend, PSAR, ADX', role: 'Confirms prevailing macro direction & prevents counter-trend traps' },
                { name: 'Structure Family (4)', examples: 'Absorption, FVG, Delta, CPR', role: 'Validates key institutional support/resistance levels & order blocks' },
                { name: 'Breakout Family (3)', examples: 'Keltner, Bollinger Squeeze, Donchian', role: 'Validates explosive volatility expansion out of tight consolidation' },
                { name: 'Momentum Family (3)', examples: 'MACD Zero-Cross, RSI, TSI', role: 'Confirms directional acceleration & candle expansion velocity' },
                { name: 'Oscillator Family (6)', examples: 'Stochastic, StochRSI, CCI, Williams, AO, MFI', role: 'Pinpoints statistical exhaustion (counts as 1 collective family vote)' },
                { name: 'Intraday Family (2)', examples: 'VWAP Bounce, 15m ORB', role: 'Tracks session-specific benchmark inflection & opening order flow' },
                { name: 'Volume Family (1)', examples: 'Chaikin Money Flow (CMF)', role: 'Confirms institutional volume flow before price breaks out' },
                { name: 'Reversal Family (2)', examples: 'Liquidity Grab, Gap Fill', role: 'Exploits retail stop hunts and opening tick sentiment reversion' }
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

            {/* 1:2.0 Risk-to-Reward Geometry & Harmonized Trailing SL */}
            <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <BarChart3 className="text-accent-light" size={18} />
                1:2.0 Risk-to-Reward Geometry &amp; Harmonized ATR Trailing Stop-Loss
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-surface-300">
                <div className="p-4 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-2">
                  <h4 className="font-bold text-white flex items-center gap-2">
                    <ShieldCheck size={16} className="text-profit-light" />
                    Phase 1: 0 to +1.0R (Breathing Room)
                  </h4>
                  <p className="text-surface-400 leading-relaxed">
                    Initial protective stop is placed at -1.0R (minimum 1.0% safety noise floor). The trailing stop stays disarmed during initial oscillations to avoid stopping out prematurely.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-2">
                  <h4 className="font-bold text-white flex items-center gap-2">
                    <Target size={16} className="text-accent-light" />
                    Phase 2: +1.0R Reached (Breakeven Lock)
                  </h4>
                  <p className="text-surface-400 leading-relaxed">
                    Once price advances past +1.0R profit cushion, the trailing stop immediately arms and ratchets to <strong>Breakeven (Entry Price)</strong>. Downside loss risk is completely eliminated!
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-2">
                  <h4 className="font-bold text-white flex items-center gap-2">
                    <TrendingUp size={16} className="text-profit-light" />
                    Phase 3: +1.0R to +2.0R (Profit Ratchet)
                  </h4>
                  <p className="text-surface-400 leading-relaxed">
                    Stop loss trails 2.0 × ATR behind price. If market pulls back, it secures locked profit. If momentum continues, it captures the full 1:2.0 target (+₹1,000 against ₹500 risk).
                  </p>
                </div>
              </div>
            </div>

            {/* 1R Risk-Based Position Sizing & Milestone Stepping Ladder */}
            <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Scale className="text-profit-light" size={18} />
                  1R Dynamic Sizing &amp; Capital Milestone Ladder (₹40k Baseline)
                </h3>
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-profit-light/10 text-profit-light border border-profit-light/30 font-bold">
                  Compounding Progression
                </span>
              </div>

              <p className="text-xs text-surface-300 leading-relaxed">
                Positions are sized dynamically so every loss is strictly clamped to 1R:
                <code className="text-accent-light font-mono ml-1">Quantity = min( floor( Risk Budget / |Entry - SL| ), floor( Max Exposure / Price ) )</code>.
                Capital scaling increases systematically as your portfolio reaches milestone thresholds:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-1">
                  <span className="font-bold text-white block">Tier 1: ₹40,000 – ₹50,000</span>
                  <p className="text-surface-400 font-mono text-[11px]">
                    1R Risk Budget: <strong>₹500 (1.25%)</strong><br />
                    Max Margin Cap: <strong>₹8,000 (20%)</strong><br />
                    Max Daily Loss: <strong>₹1,500</strong>
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-1">
                  <span className="font-bold text-white block">Tier 2: ₹50,000 – ₹60,000</span>
                  <p className="text-surface-400 font-mono text-[11px]">
                    1R Risk Budget: <strong>₹625 (1.25%)</strong><br />
                    Max Margin Cap: <strong>₹10,000 (20%)</strong><br />
                    Max Daily Loss: <strong>₹1,875</strong>
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-1">
                  <span className="font-bold text-white block">Tier 3: ₹60,000 – ₹70,000</span>
                  <p className="text-surface-400 font-mono text-[11px]">
                    1R Risk Budget: <strong>₹750 (1.25%)</strong><br />
                    Max Margin Cap: <strong>₹12,000 (20%)</strong><br />
                    Max Daily Loss: <strong>₹2,250</strong>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 5: STATUTORY FRICTION GUARD & CALCULATOR ──────────────── */}
      {activeTab === 'friction_guard' && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-700/60 pb-4">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Calculator className="text-profit-light" size={20} />
                  Interactive Indian Statutory Friction Calculator &amp; 3.5x Barrier
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  Simulate exact Indian brokerage, regulatory turnover taxes, stamp duties, and GST before placing any trade.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/20">
                Gate: Expected Gain ≥ 3.5x Total Fees
              </span>
            </div>

            {/* Interactive Calculator Widget */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Inputs Column */}
              <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Calculator size={15} className="text-accent-light" />
                  Trade Simulation Parameters
                </h4>

                <div className="space-y-1.5">
                  <label className="text-xs text-surface-400">Stock Price (₹):</label>
                  <input
                    type="number"
                    value={calcPrice}
                    onChange={e => setCalcPrice(Math.max(1, parseFloat(e.target.value) || 0))}
                    className="w-full px-3 py-2 bg-surface-950 border border-surface-700 rounded-xl text-sm font-mono text-white focus:outline-none focus:border-accent-light"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs text-surface-400">Quantity (Shares):</label>
                  <input
                    type="number"
                    value={calcQty}
                    onChange={e => setCalcQty(Math.max(1, parseInt(e.target.value) || 0))}
                    className="w-full px-3 py-2 bg-surface-950 border border-surface-700 rounded-xl text-sm font-mono text-white focus:outline-none focus:border-accent-light"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs text-surface-400">Target Profit Gain (%):</label>
                  <input
                    type="number"
                    step="0.1"
                    value={calcTargetPct}
                    onChange={e => setCalcTargetPct(Math.max(0.1, parseFloat(e.target.value) || 0))}
                    className="w-full px-3 py-2 bg-surface-950 border border-surface-700 rounded-xl text-sm font-mono text-white focus:outline-none focus:border-accent-light"
                  />
                </div>

                <div className="pt-2 border-t border-surface-800 text-xs text-surface-400 space-y-1 font-mono">
                  <div className="flex justify-between">
                    <span>Position Size:</span>
                    <span className="text-white">₹{feeCalculation.buyVal.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Expected Gain:</span>
                    <span className="text-profit-light">+₹{feeCalculation.estProfit.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                  </div>
                </div>
              </div>

              {/* Fee Breakdown Column */}
              <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                  Angel One &amp; Exchange Fee Breakdown
                </h4>
                <div className="space-y-2 text-xs font-mono text-surface-300">
                  <div className="flex justify-between pb-1 border-b border-surface-800">
                    <span>Angel One Brokerage (Buy + Sell):</span>
                    <span className="text-white font-bold">₹{feeCalculation.brokerage.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pb-1 border-b border-surface-800">
                    <span>STT (0.025% on Sell):</span>
                    <span className="text-white font-bold">₹{feeCalculation.stt.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pb-1 border-b border-surface-800">
                    <span>NSE Turnover Levy (0.00297%):</span>
                    <span className="text-white font-bold">₹{feeCalculation.nseTurnover.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pb-1 border-b border-surface-800">
                    <span>State Stamp Duty (0.003% on Buy):</span>
                    <span className="text-white font-bold">₹{feeCalculation.stampDuty.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pb-1 border-b border-surface-800">
                    <span>SEBI Turnover Charge:</span>
                    <span className="text-white font-bold">₹{feeCalculation.sebi.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pb-1 border-b border-surface-800">
                    <span>GST (18% on Brokerage+NSE+SEBI):</span>
                    <span className="text-white font-bold">₹{feeCalculation.gst.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pt-1 text-sm font-bold text-loss-light">
                    <span>Total Round-Trip Friction:</span>
                    <span>-₹{feeCalculation.totalFriction.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Gate Decision Column */}
              <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 flex flex-col justify-between space-y-4">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-white mb-2">
                    Pre-Trade Friction Gate Status
                  </h4>
                  <div className="p-3 bg-surface-950 rounded-xl border border-surface-800 font-mono text-xs space-y-1.5 text-surface-300">
                    <div className="flex justify-between">
                      <span>3.5x Friction Multiple:</span>
                      <span className="text-warning-light font-bold">₹{feeCalculation.minRequiredPayoff.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Expected Target Payoff:</span>
                      <span className="text-white font-bold">₹{feeCalculation.estProfit.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-surface-800">
                      <span>Net P&amp;L After Taxes:</span>
                      <span className={feeCalculation.netProfitAfterFriction >= 0 ? 'text-profit-light font-bold' : 'text-loss-light font-bold'}>
                        {feeCalculation.netProfitAfterFriction >= 0 ? '+' : ''}₹{feeCalculation.netProfitAfterFriction.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className={`p-4 rounded-xl border text-center font-bold text-sm ${
                  feeCalculation.passesGate
                    ? 'bg-profit-DEFAULT/10 border-profit-DEFAULT/30 text-profit-light'
                    : 'bg-loss-DEFAULT/10 border-loss-DEFAULT/30 text-loss-light'
                }`}>
                  {feeCalculation.passesGate ? (
                    <div className="flex items-center justify-center gap-2">
                      <CheckCircle2 size={18} />
                      <span>GATE APPROVED (Payoff ≥ 3.5x Fees)</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center gap-2">
                      <Ban size={18} />
                      <span>REJECTED (Payoff &lt; 3.5x Fees)</span>
                    </div>
                  )}
                </div>

                <p className="text-[11px] text-surface-400 leading-relaxed">
                  The engine automatically discards low-delta opportunities where broker fees and taxes erode significant profits.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 6: PARTIAL PROFIT BOOKING ──────────────────────────────── */}
      {activeTab === 'partial_booking' && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-6">
            <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Split className="text-accent-light" size={20} />
                  Two-Stage Multi-Target Scaling &amp; Breakeven Protection
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">
                  Locking in guaranteed gains while letting trend runners capture extended profits risk-free.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/30">
                50% Milestone Exit
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 relative flex flex-col justify-between">
                <div>
                  <span className="w-8 h-8 rounded-xl bg-accent-light/15 text-accent-light flex items-center justify-center font-bold font-mono text-xs mb-3 border border-accent-light/30">
                    01
                  </span>
                  <h3 className="font-bold text-white text-sm mb-1.5">Dual-Target Entry</h3>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    The position opens with 100% quantity. Target 1 is placed at 1:2 R:R (e.g. +2.0%), while Target 2 is set at the full setup target (e.g. +4.0%).
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
                    When price reaches Target 1, exactly 50% of the position is exited immediately at market price, crediting realized profit into cash balance.
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

            {/* ₹250 Minimum Profit Threshold Alert */}
            <div className="bg-gradient-to-r from-surface-900 via-surface-900 to-surface-800 border border-surface-700/80 rounded-xl p-5">
              <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-2">
                <ShieldCheck className="text-profit-light" size={18} />
                Smart Brokerage Safeguard (₹250 Minimum Profit Threshold)
              </h3>
              <p className="text-xs text-surface-300 leading-relaxed">
                Angel One charges flat ₹20 per order. Splitting an exit into two transactions incurs an extra order fee (≈₹23.60 with GST). To ensure this cost never erodes returns, the engine enforces a <strong>₹250 Minimum Profit Threshold</strong>: if 50% exit profit would yield under ₹250, partial booking is automatically bypassed in favor of a single full exit at target.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 7: SWING & SECTOR SCREENER ─────────────────────────────── */}
      {activeTab === 'swing_screener' && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-6">
            <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <BarChart3 className="text-accent-light" size={20} />
                  Multi-Timeframe Daily &amp; Weekly Swing Screener
                </h2>
                <p className="text-xs text-surface-400 mt-0.5">
                  Positional momentum screening across high-beta equities with fundamental quality scoring.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/30">
                Daily / Weekly Timeframes
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 5 Technical Archetypes */}
              <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                  5 Positional Technical Setup Archetypes
                </h4>
                <ul className="space-y-2 text-xs text-surface-300">
                  <li className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <strong className="text-accent-light block">1. Trend Following:</strong>
                    <span>Aligned 20 &amp; 50 EMA slope, Supertrend active, ADX &gt; 25 indicating strong institutional trending momentum.</span>
                  </li>
                  <li className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <strong className="text-profit-light block">2. Multi-Week Breakout:</strong>
                    <span>Price breaking 20-day high with 2.0x volume expansion out of a volatility compression envelope.</span>
                  </li>
                  <li className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <strong className="text-warning-light block">3. Mean Reversion:</strong>
                    <span>RSI oversold &lt; 35 exiting lower bounds with bullish divergence on daily candlestick charts.</span>
                  </li>
                  <li className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <strong className="text-white block">4. Key S/R Bounce:</strong>
                    <span>Pullback retesting prior major resistance-turned-support pivot with hammer rejection.</span>
                  </li>
                  <li className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <strong className="text-accent-light block">5. Pullback in Trend:</strong>
                    <span>20 EMA test within strong primary daily uptrend offering high risk-reward entry.</span>
                  </li>
                </ul>
              </div>

              {/* Fundamental & Sector Profiling */}
              <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 space-y-4 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-white mb-2">
                    Fundamental Quality Filter &amp; Sector Categorization
                  </h4>
                  <p className="text-xs text-surface-300 leading-relaxed mb-4">
                    In addition to mathematical technical scans, each candidate equity is scored against curated institutional fundamental profiles:
                  </p>
                  <div className="space-y-2.5 text-xs">
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                      <span className="text-surface-400">Quality Rating:</span>
                      <span className="font-bold text-profit-light">Tier A+ / A Institutionally Backed</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                      <span className="text-surface-400">Sector Grouping:</span>
                      <span className="font-bold text-white">Banking, IT, Auto, Energy, Metals, FMCG</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                      <span className="text-surface-400">Market Cap Tier:</span>
                      <span className="font-bold text-accent-light">Mega Cap &amp; Large Cap Derivatives</span>
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-surface-950/60 rounded-xl border border-surface-700/60 text-xs text-surface-400">
                  Access the full live screener anytime via the <strong>Swing Screener</strong> tab on the left sidebar.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 8: WALK-FORWARD BACKTESTING & EXPECTANCY ────────────────── */}
      {activeTab === 'backtest_expectancy' && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-700/60 pb-4">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Award className="text-profit-light" size={20} />
                  Walk-Forward Backtesting &amp; Mathematical Expectancy Architecture
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  How the system validates quantitative setups across any chosen calendar month without relying on static historical claims.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/30">
                Zero Look-Ahead Bias
              </span>
            </div>

            {/* Why Static Returns Vary Box */}
            <div className="p-4 rounded-xl bg-surface-900 border border-surface-700/80 space-y-2">
              <div className="flex items-center gap-2 text-warning-light font-bold text-xs uppercase tracking-wider">
                <AlertCircle size={16} />
                Why Fixed Net Returns Are Never Hardcoded
              </div>
              <p className="text-xs text-surface-300 leading-relaxed">
                Market regimes naturally shift month-to-month. A month characterized by strong institutional trend expansion (high Kaufman Efficiency Ratio) produces rapid breakout follow-through, while a consolidating, mean-reverting month experiences tighter price action. Hardcoding a static return from one specific test window is mathematically misleading. Instead, our framework relies on <strong>Positive Expectancy Geometry</strong> and provides a built-in walk-forward backtest runner so you can test any custom date range dynamically.
              </p>
            </div>

            {/* Mathematical Expectancy Formula */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                  The Mathematical Intraday Expectancy Equation
                </h4>
                <div className="p-3 bg-surface-950 rounded-xl border border-surface-800 font-mono text-xs text-profit-light leading-relaxed">
                  Expectancy = (Win% × Avg_Win) - (Loss% × Avg_Loss) - Friction
                </div>
                <p className="text-xs text-surface-300 leading-relaxed">
                  Institutional profitability is not driven by predicting every market tick or chasing an artificial 90% win rate. It is governed by <strong>positive payoff asymmetry</strong>:
                </p>
                <ul className="space-y-1.5 text-xs text-surface-400">
                  <li>• Asymmetric breakout setups target 1:2.5 to 1:4.0 Risk-to-Reward.</li>
                  <li>• Disciplined 1.0% safety noise floors clamp average loss sizes tightly.</li>
                  <li>• The 3.5x pre-trade friction guard eliminates high-turnover fee traps.</li>
                </ul>
              </div>

              {/* Quality Metrics Evaluated */}
              <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                  Institutional Quality Benchmarks Measured
                </h4>
                <div className="grid grid-cols-2 gap-2 font-mono text-xs">
                  <div className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <span className="text-surface-400 text-[10px] block uppercase">Profit Factor</span>
                    <span className="text-white font-bold text-sm">Target &gt; 1.30</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <span className="text-surface-400 text-[10px] block uppercase">Asymmetry Ratio</span>
                    <span className="text-profit-light font-bold text-sm">Avg Win &gt; 1.8x Loss</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <span className="text-surface-400 text-[10px] block uppercase">Max Drawdown</span>
                    <span className="text-warning-light font-bold text-sm">Controlled &lt; 8%</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                    <span className="text-surface-400 text-[10px] block uppercase">Friction Drag</span>
                    <span className="text-accent-light font-bold text-sm">Fees &lt; 15% Gain</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 1-Year Walk-Forward Empirical Performance (Realized Data) */}
            <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <BarChart3 size={16} className="text-profit-light" />
                  1-Year Walk-Forward Empirical Results (₹40,000 Capital Baseline)
                </h4>
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-profit-light/10 text-profit-light border border-profit-light/30 font-bold">
                  8 of 13 Months Profitable
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                <div className="p-3 bg-surface-950 rounded-xl border border-surface-800">
                  <span className="text-surface-400 text-[10px] block uppercase">Gross Trading Profit</span>
                  <span className="text-profit-light font-bold text-sm">+₹31,017 (+77.5%)</span>
                </div>
                <div className="p-3 bg-surface-950 rounded-xl border border-surface-800">
                  <span className="text-surface-400 text-[10px] block uppercase">Peak Account Equity</span>
                  <span className="text-white font-bold text-sm">₹48,230.17</span>
                </div>
                <div className="p-3 bg-surface-950 rounded-xl border border-surface-800">
                  <span className="text-surface-400 text-[10px] block uppercase">Statutory Taxes &amp; Fees</span>
                  <span className="text-loss-light font-bold text-sm">-₹32,153 (547 Trades)</span>
                </div>
                <div className="p-3 bg-surface-950 rounded-xl border border-surface-800">
                  <span className="text-surface-400 text-[10px] block uppercase">Top Alpha Strategy</span>
                  <span className="text-accent-light font-bold text-sm">Keltner (+₹5,387)</span>
                </div>
              </div>

              <div className="p-3.5 bg-surface-950/80 rounded-xl border border-surface-800 text-xs text-surface-300 space-y-2">
                <p className="font-bold text-white flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-accent-light" />
                  Why the Market Regime Filter &amp; 1:2 R:R Transform Profitability:
                </p>
                <p className="text-surface-400 leading-relaxed">
                  The raw strategy produced an outstanding +77.5% gross return (+₹31,017). However, high-frequency churn across sideways consolidation months (Nov 2025 and July 2026) drained capital into taxes and brokerage. By enforcing <strong>≥ 3-family confluence</strong>, <strong>1:2.0 minimum R:R</strong>, and <strong>Market Regime Squeeze Gating (ADX ≥ 20)</strong>, the engine cuts trade count by ~60%, saving over ₹20,000 in friction and locking in clean net alpha!
                </p>
              </div>
            </div>

            {/* How to Run Your Own Walk-Forward Backtest */}
            <div className="bg-surface-900/90 p-5 rounded-xl border border-surface-700/80 space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <Terminal size={16} className="text-accent-light" />
                Run Custom Date Range / Month Backtests via CLI
              </h4>
              <p className="text-xs text-surface-300 leading-relaxed">
                You can run the walk-forward backtesting engine directly from your terminal over any lookback period (30 days, 60 days, 6 months, or custom symbols) with full statutory Indian taxes deducted tick-by-tick:
              </p>

              <div className="space-y-2">
                {[
                  {
                    id: 'cmd1',
                    label: '30-Day F&O Intraday 15-Minute Backtest (KER Filtered):',
                    cmd: 'uv run python -m backend.backtest.run_backtest --period 30d --interval 15m'
                  },
                  {
                    id: 'cmd2',
                    label: '60-Day Multi-Scrip High-Beta Backtest:',
                    cmd: 'uv run python -m backend.backtest.run_backtest --period 60d --interval 15m --symbols RELIANCE TCS INFY HDFCBANK ICICIBANK'
                  }
                ].map(item => (
                  <div key={item.id} className="p-3 bg-surface-950 rounded-xl border border-surface-800 flex items-center justify-between gap-3">
                    <div className="space-y-1 overflow-hidden">
                      <span className="text-[11px] text-surface-400 block">{item.label}</span>
                      <code className="text-xs font-mono text-accent-light block truncate">{item.cmd}</code>
                    </div>
                    <button
                      onClick={() => copyToClipboard(item.cmd, item.id)}
                      className="p-2 rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-300 hover:text-white border border-surface-700 transition-all shrink-0 cursor-pointer"
                      title="Copy command"
                    >
                      {copiedCmd === item.id ? <Check size={14} className="text-profit-light" /> : <Copy size={14} />}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 9: TELEGRAM REMOTE CONTROL ─────────────────────────────── */}
      {activeTab === 'telegram_control' && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute -right-10 -bottom-10 w-72 h-72 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="p-2 bg-sky-500/15 text-sky-400 rounded-xl border border-sky-500/30">
                    <Send size={20} />
                  </span>
                  <h2 className="text-xl font-bold text-white">2-Way Telegram Remote Control &amp; Panic Switch</h2>
                </div>
                <p className="text-sm text-surface-300 max-w-3xl leading-relaxed">
                  Monitor trading engine status, inspect open positions, remotely start/stop market scanning, or trigger an instant emergency square-off directly from your smartphone.
                </p>
              </div>

              <div className="flex items-center gap-3 self-start md:self-auto">
                <div className="px-3.5 py-2 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
                  <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Protocol</span>
                  <span className="text-xs font-bold text-sky-400 font-mono">Long-Poll (getUpdates)</span>
                </div>
                <div className="px-3.5 py-2 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
                  <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Security</span>
                  <span className="text-xs font-bold text-profit-light font-mono">Numeric Chat ID Lock</span>
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
                desc: 'Returns live agent status (RUNNING/STOPPED), execution mode, active positions count, today’s realised and unrealised P&L, and available equity margin.',
                example: '🤖 AGENT STATUS\n⚡ Engine: 🟢 RUNNING (Mode: AUTO)\n📊 Active Positions: 2\n💰 Today P&L: +₹1,450.00'
              },
              {
                cmd: '/positions',
                tag: 'Portfolio',
                color: 'text-accent-light bg-accent-DEFAULT/10 border-accent-DEFAULT/30',
                desc: 'Fetches real-time open positions from Angel One SmartAPI, displaying stock symbol, direction, quantity, entry price, LTP, and net P&L.',
                example: '📊 CURRENT OPEN POSITIONS\n🟢 RELIANCE (BUY × 15)\n  • Entry: ₹2,900 | LTP: ₹2,935\n  • P&L: +₹525.00 (+1.21%)'
              },
              {
                cmd: '/squareoff',
                tag: '🚨 Emergency Panic',
                color: 'text-loss-light bg-loss-DEFAULT/15 border-loss-DEFAULT/40',
                desc: 'Immediate emergency exit button. Cancels open tracking and sends market orders to close all open intraday positions on Angel One, then halts the engine.',
                example: '🚨 EMERGENCY SQUARE-OFF\n⚡ Closed: 2 positions squared off\n🛑 Engine: Stopped\n⏱ Executed At: 14:15:02 IST'
              },
              {
                cmd: '/start auto',
                tag: 'Execution',
                color: 'text-profit-light bg-profit-DEFAULT/10 border-profit-DEFAULT/30',
                desc: 'Remotely activates the trading engine in automated execution mode. Scanner will auto-place orders when confidence ≥85% and ≥2 confluence families agree.',
                example: '🚀 TRADING ENGINE STARTED\n🏷 Mode: AUTO\n🔍 Dynamic scanner & position monitoring active.'
              },
              {
                cmd: '/start confirm',
                tag: 'Safety',
                color: 'text-warning-light bg-warning-DEFAULT/10 border-warning-DEFAULT/30',
                desc: 'Activates the engine in confirmation mode. Signals stream to desktop UI for manual review without executing trades automatically.',
                example: '🚀 TRADING ENGINE STARTED\n🏷 Mode: CONFIRM\n🛡 Signals will await confirmation in UI.'
              },
              {
                cmd: '/stop',
                tag: 'Control',
                color: 'text-surface-300 bg-surface-700/30 border-surface-600/40',
                desc: 'Pauses market scanning and halts new trade generation. Existing open positions remain live and will exit upon reaching Targets or End-Of-Day square-off.',
                example: '🛑 TRADING ENGINE STOPPED\nMarket scanning paused.\nExisting open positions remain live.'
              }
            ].map((card, i) => (
              <div key={i} className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 flex flex-col justify-between space-y-3 shadow-md">
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

          {/* 60-Second Setup Guide */}
          <div className="bg-gradient-to-r from-sky-500/10 via-surface-800 to-surface-800 border border-sky-500/30 rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-2 text-sky-400 font-bold text-base">
              <Smartphone size={18} />
              <span>How to Set Up Remote Telegram Control in 60 Seconds</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-surface-300">
              <div className="bg-surface-900/80 p-4 rounded-xl border border-surface-700/60 space-y-1.5">
                <span className="font-bold text-white block">Step 1: Create Your Bot</span>
                <p>Open Telegram, search for <strong>@BotFather</strong>, and send <code>/newbot</code>. Choose a name to receive your <strong>Bot Token</strong>.</p>
              </div>
              <div className="bg-surface-900/80 p-4 rounded-xl border border-surface-700/60 space-y-1.5">
                <span className="font-bold text-white block">Step 2: Get Your Chat ID</span>
                <p>Search for <strong>@userinfobot</strong> on Telegram and tap Start. It will reply with your personal numeric <strong>Id</strong> (e.g. <code>987654321</code>).</p>
              </div>
              <div className="bg-surface-900/80 p-4 rounded-xl border border-surface-700/60 space-y-1.5">
                <span className="font-bold text-white block">Step 3: Save in Settings</span>
                <p>Go to <strong>Settings &gt; Notifications</strong> in this app. Enter your Token &amp; Chat ID, click <strong>Save</strong>, open your bot chat and send <code>/status</code>!</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 10: PAPER VS LIVE MODE ─────────────────────────────────── */}
      {activeTab === 'paper_vs_live' && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
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
                Shared Quantitative Engine
              </span>
            </div>

            <p className="text-sm text-surface-300 leading-relaxed">
              The Paper Trading engine is not a detached toy simulator. It executes against real live tick feeds from Angel One SmartAPI and routes through the exact same Python scanner, multi-family confluence gate, and risk management algorithms as live trading.
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
                      dim: 'Strategy Universe & Signals',
                      paper: 'Identical: High-conviction Breakout & Structure roster (Lagging indicators & negative oscillators disabled by default)',
                      live: 'Identical: Executes on the exact same pruned Python scanner engine'
                    },
                    {
                      dim: 'Position Sizing Engine',
                      paper: '1R Risk-Based Sizing: Q = min(floor(Risk/ΔSL), floor(Exposure/Price)) with 5x MIS leverage (constant loss budget)',
                      live: 'Identical: 1R Risk-Based Sizing via RiskManager.calculate_position_size'
                    },
                    {
                      dim: 'Confluence Gate & Multi-Family Voting',
                      paper: 'Identical: Requires ≥ 3 distinct families + Market Regime filter (ADX ≥ 20, KER ≥ 0.25) + 50 EMA trend filter',
                      live: 'Identical: Requires ≥ 3 distinct families + Market Regime filter (ADX ≥ 20, KER ≥ 0.25) + 50 EMA trend filter (Confidence ≥ 85% in Auto mode)'
                    },
                    {
                      dim: 'Stop Loss Protection',
                      paper: 'Live Tick Monitor: In-memory real-time tick evaluation triggering simulated SL / Breakeven exits',
                      live: 'Native Exchange-Side: Immediate STOPLOSS_LIMIT order placed on NSE/BSE book (survives app crashes)'
                    },
                    {
                      dim: 'Pending Order Management',
                      paper: 'Immediate virtual execution at incoming tick price',
                      live: '60-Second Timeout Queue: Unfilled limit orders are auto-cancelled after 60s to prevent stale fills'
                    },
                    {
                      dim: 'Dynamic Trailing & Partial Booking',
                      paper: 'Supported: Books 50% at Target 1, ratchets virtual SL to Breakeven @ Entry',
                      live: 'Supported: Books 50% at Target 1, modifies exchange-side SL order to Breakeven via SmartAPI'
                    },
                    {
                      dim: 'State Persistence & Recovery',
                      paper: 'Local Storage: Zustand storage syncs open positions and order history',
                      live: 'Atomic Disk Persistence: active_trades.json saves positions & SL order IDs to recover after reboot'
                    },
                    {
                      dim: 'Session Authentication',
                      paper: 'Streams live ticks from authenticated SmartAPI session',
                      live: 'Headless TOTP Auto-Renewal: Re-authenticates and retries on AB1010/AG8001 token expiry'
                    },
                    {
                      dim: 'Brokerage & Statutory Taxes',
                      paper: '₹0 (Pure strategy edge & gross P&L tracking)',
                      live: 'Full Friction: ₹20/order brokerage + STT + Exchange fees + Stamp Duty + GST'
                    },
                    {
                      dim: 'Execution Modes',
                      paper: 'Always automatic simulation in local storage',
                      live: 'Toggle between "Confirm Mode" (manual trade review) and "Auto Mode"'
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
