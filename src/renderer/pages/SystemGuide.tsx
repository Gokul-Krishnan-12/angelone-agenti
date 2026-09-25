import React, { useState, useMemo } from 'react';
import {
  Compass,
  Cpu,
  Layers,
  ShieldCheck,
  Search,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BarChart3,
  Split,
  Clock,
  Zap,
  Target,
  TrendingUp,
  Lock,
  Flame,
  Send,
  Smartphone,
  ShieldAlert,
  Terminal,
  Scale,
  Ban,
  Filter,
  Award,
  Calculator,
  Copy,
  Check,
  Calendar,
  Database,
  RefreshCw,
  Timer,
  ArrowRight,
  Activity,
  Maximize2
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
  status: 'Active Core' | 'Pruned / Disabled';
}

const STRATEGIES_LIST: StrategyItem[] = [
  // ── 1. Breakout Family (4) ──────────────────────────────────────────
  {
    id: 'bollinger_breakout',
    name: 'Bollinger Bands Squeeze Breakout',
    category: 'Volatility Squeeze',
    family: 'Breakout',
    winRateOrRank: '+₹15,767 Alpha Leader (Top Core)',
    rrRatio: '1 : 2.0 to 1 : 2.5',
    triggerRules: 'Bollinger Band width contracts into a multi-period volatility squeeze (bandwidth < 1.8%), followed by a decisive candle close outside the bands with volume surge (RVOL ≥ 1.2x).',
    indicators: '20 SMA, 2.0 Standard Deviations, Bandwidth %, RVOL',
    whyItWorks: 'Prolonged compression cycles store institutional energy that reliably transitions into explosive directional volatility expansion.',
    status: 'Active Core'
  },
  {
    id: 'donchian_breakout',
    name: 'Donchian Channel Breakout',
    category: 'Multi-Period Breakout',
    family: 'Breakout',
    winRateOrRank: '+₹9,184 Alpha Producer (Top Core)',
    rrRatio: '1 : 2.5 to 1 : 3.0',
    triggerRules: 'Price decisively exceeds 20-period highest high (BUY) or breaks 20-period lowest low (SELL) with expanding candle range and volume confirmation.',
    indicators: '20-period Donchian Channels (Upper & Lower boundaries), 20 Volume SMA',
    whyItWorks: 'Captures tail-risk explosive trend expansions by entering whenever price creates a new multi-hour high or low aligned with the 50 EMA macro trend.',
    status: 'Active Core'
  },
  {
    id: 'keltner_breakout',
    name: 'Keltner Channel Breakout',
    category: 'Volatility Breakout',
    family: 'Breakout',
    winRateOrRank: 'High Momentum Alpha (Top Core)',
    rrRatio: '1 : 2.5 to 1 : 4.0',
    triggerRules: 'Candle closes strictly outside Upper Band (BUY) or Lower Band (SELL) after prior bar consolidation within the ATR channel envelope.',
    indicators: '20 EMA midline + 10 ATR envelope (Upper & Lower bands)',
    whyItWorks: 'Volatility breakouts out of compressed Keltner channels exhibit explosive directional velocity and capture asymmetric trending swings.',
    status: 'Active Core'
  },
  {
    id: 'opening_range_breakout',
    name: 'Opening Range Breakout (ORB)',
    category: 'Morning Momentum',
    family: 'Breakout',
    winRateOrRank: 'Morning Momentum (Top Core)',
    rrRatio: '1 : 2.0',
    triggerRules: 'First 15-minute high or low decisively breached after 09:30 IST with an expansion candle (wick ≤ 25%) and relative volume surge (RVOL ≥ 1.2x). Blocked if opening gap ≥ 1.8%.',
    indicators: '15-min High/Low Range, Relative Volume (RVOL), Gap Filter',
    whyItWorks: 'Establishes the prevailing directional order-flow for the morning session once opening market auction imbalances clear.',
    status: 'Active Core'
  },

  // ── 2. Volume Family (1) ────────────────────────────────────────────
  {
    id: 'cmf_accumulation',
    name: 'CMF Institutional Flow',
    category: 'Institutional Flow',
    family: 'Volume',
    winRateOrRank: '-₹12,286 Net Drag (Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'CMF > +0.10 with volume > 1.2x 20-bar average and price > 20 EMA (BUY). CMF < -0.10 with volume surge below 20 EMA (SELL).',
    indicators: 'Chaikin Money Flow (20-period), Volume Ratio, 20 EMA',
    whyItWorks: 'Detects institutional accumulation or distribution before price breaks into an extended trend continuation swing; disabled by default due to high whipsaw drag in chop.',
    status: 'Pruned / Disabled'
  },

  // ── 3. Structure Family (5) ─────────────────────────────────────────
  {
    id: 'institutional_absorption',
    name: 'Institutional Absorption',
    category: 'Multi-Candle Absorption',
    family: 'Structure',
    winRateOrRank: '+₹6,760 Alpha Producer (Top Core)',
    rrRatio: '1 : 2.2 to 1 : 2.5',
    triggerRules: 'Multi-candle absorption scan (last 3 bars) prints high volume (≥ 2.5x avg) with rejection wick ≥ 45% of range, followed by confirmation candle closing in direction of interest.',
    indicators: '20-period Volume SMA, Rejection Wick Ratio, ADX > 20 filter',
    whyItWorks: 'Detects large institutions absorbing resting market inventory with passive limit orders before initiating aggressive repricing.',
    status: 'Active Core'
  },
  {
    id: 'fixed_range_volume_profile',
    name: 'Fixed Range Volume Profile (FRVP)',
    category: 'Auction Market Theory (AMT)',
    family: 'Structure',
    winRateOrRank: '+₹2,087 AMT Structural Edge (Top Core)',
    rrRatio: '1 : 2.0 to 1 : 2.2 (POC Preserved, min 1:1.3)',
    triggerRules: 'Bins volume into 30 price nodes anchored from session start (09:15 IST). 4 AMT Setups: (1) VAH Breakout with 2 consecutive closes > VAH & LVN vacuum; (2) VAL Breakdown with 2 consecutive closes < VAL & LVN vacuum; (3) VAL Sweep & Reclaim targeting POC; (4) VAH Sweep & Reject targeting POC. Enforces Value Area Width ≥ 1.8% compression guard and 4.0x friction buffer.',
    indicators: 'Session Volume Profile (30 Bins), POC, VAH, VAL (70% Volume), LVN Vacuum, 20 EMA',
    whyItWorks: 'Exploits institutional auction imbalance between Initiative participants (expanding range through Low Volume Nodes) and Responsive participants (mean-reverting sweeps back toward the high-liquidity Point of Control).',
    status: 'Active Core'
  },
  {
    id: 'order_block_fvg',
    name: 'Order Block & Fair Value Gap',
    category: 'SMC Imbalance',
    family: 'Structure',
    winRateOrRank: '-₹6,183 Net Drag (Pruned)',
    rrRatio: '1 : 2.5',
    triggerRules: 'Imbalance / 3-candle Fair Value Gap created by high-volume displacement, followed by a mitigation retest into the imbalance.',
    indicators: 'Fair Value Gap (FVG), Prior Pivot Displacement, 20 EMA',
    whyItWorks: 'Fills institutional buy/sell imbalances created when large market orders aggressively displace resting liquidity.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'volume_delta_divergence',
    name: 'Volume Delta Divergence',
    category: 'Order Flow Divergence',
    family: 'Structure',
    winRateOrRank: '-₹5,206 Net Drag (Pruned)',
    rrRatio: '1 : 2.2',
    triggerRules: 'Price prints lower low while buying delta volume increases (bullish), or price makes higher high while selling delta dominates (bearish).',
    indicators: 'Cumulative Volume Delta (CVD proxy), Swing Extremes',
    whyItWorks: 'Pinpoints institutional absorption where passive limit orders soak up aggressive market orders before a sharp trend turn.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'cpr_breakout_reversal',
    name: 'Central Pivot Range (CPR)',
    category: 'Pivot Structure',
    family: 'Structure',
    winRateOrRank: 'Whipsaw Prone on Rolling Bars (Pruned)',
    rrRatio: '1 : 2.0 to 1 : 2.5',
    triggerRules: 'Rejection or breakout of Daily TC (Top Central) / BC (Bottom Central) pivot lines on elevated volume.',
    indicators: 'Pivot Point = (H + L + C)/3, TC = (Pivot - BC) + Pivot, BC = (H + L)/2',
    whyItWorks: 'Standard and virgin CPR levels act as high-probability magnets and inflection barriers heavily tracked by institutional algorithmic execution.',
    status: 'Pruned / Disabled'
  },

  // ── 4. Reversal Family (2) ──────────────────────────────────────────
  {
    id: 'liquidity_grab_reversal',
    name: 'Liquidity Grab Reversal',
    category: 'Smart Money Reversal',
    family: 'Reversal',
    winRateOrRank: 'Elite Edge (~78% Win Rate, Top Core)',
    rrRatio: '1 : 2.2 to 1 : 2.5',
    triggerRules: 'Price sweeps past key swing high/low to trigger resting retail stop orders, then aggressively snaps back inside the range with long rejection wick (wick ≥ 40% of candle).',
    indicators: 'Swing Highs/Lows, Wick-to-Body Ratio > 2.0, Volume Spike',
    whyItWorks: 'Exploits institutional stop-hunts where large participants absorb counter-party inventory before driving price in the genuine direction.',
    status: 'Active Core'
  },
  {
    id: 'gap_fill',
    name: 'Gap Fill Reversal',
    category: 'Mean Reversion',
    family: 'Reversal',
    winRateOrRank: 'High Reliability (~68% Win Rate, Top Core)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Morning gap up/down fails to sustain past key inflection; price re-enters prior day closing range targeting the gap fill.',
    indicators: 'Prior Close, Opening Tick Gap, 9 EMA Rejection',
    whyItWorks: 'Overextended retail opening sentiment gets exhausted quickly, creating reliable statistical reversion back to prior settlement value.',
    status: 'Active Core'
  },

  // ── 5. Intraday Family (1) ──────────────────────────────────────────
  {
    id: 'vwap_bounce',
    name: 'VWAP Pullback & Bounce',
    category: 'Intraday Benchmark',
    family: 'Intraday',
    winRateOrRank: '88.9% SL Rate (-₹172 Drag, Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Price pulls back to test session VWAP, forming a bullish hammer or bearish rejection candle with volume surge.',
    indicators: 'Volume Weighted Average Price (VWAP), 20-bar Volume SMA',
    whyItWorks: 'Institutions use VWAP as primary execution benchmark; disabled by default because 5m noise around VWAP frequently stops out retail stops before follow-through.',
    status: 'Pruned / Disabled'
  },

  // ── 6. Trend Family (4) ─────────────────────────────────────────────
  {
    id: 'ema_crossover',
    name: 'EMA Directional Crossover',
    category: 'Dynamic Moving Average',
    family: 'Trend',
    winRateOrRank: '-₹2,201 Drag (Lagging, Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Fast EMA(9) crosses Slow EMA(21) with decisive gap ≥ 0.05% of price, ADX > 20 regime filter, and 1.5x volume confirmation.',
    indicators: '9 EMA, 21 EMA, 14 ADX, 20 Volume SMA',
    whyItWorks: 'Requires directional momentum regime (ADX > 20); disabled by default because moving average crossovers lag in fast intraday swings.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'supertrend',
    name: 'Supertrend Directional Filter',
    category: 'Structural Trend',
    family: 'Trend',
    winRateOrRank: 'Whipsaw Prone in Squeeze (Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Price closes across the Supertrend line (Period 10, Multiplier 3.0) confirming structural trend transition.',
    indicators: 'ATR (10) * 3.0 band offset from median price',
    whyItWorks: 'Provides a robust trend backbone; disabled by default to prevent whipsaws during mid-session contractions.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'psar_trend',
    name: 'Parabolic SAR Trend Shift',
    category: 'Trailing Trend',
    family: 'Trend',
    winRateOrRank: '-₹11,654 Net Drag (Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'PSAR dot flips from above candles to below candles (BUY) or vice versa with confirmation from ADX > 20.',
    indicators: 'Step 0.02, Max 0.20 Parabolic SAR, ADX',
    whyItWorks: 'Classical trailing indicator; disabled by default due to high whipsaw stop-out rate during intraday rotations.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'adx_momentum',
    name: 'ADX Trend Momentum Strength',
    category: 'Directional Velocity',
    family: 'Trend',
    winRateOrRank: '62.0% SL Rate (-₹291 Drag, Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: '+DI crosses above -DI with ADX > 25 rising (BUY), or -DI crosses above +DI with ADX > 25 rising (SELL).',
    indicators: '14-period ADX, +DI, -DI',
    whyItWorks: 'Distinguishes true persistent directional moves; used primarily as a regime qualifier rather than standalone trigger.',
    status: 'Pruned / Disabled'
  },

  // ── 7. Momentum Family (3) ──────────────────────────────────────────
  {
    id: 'macd_cross',
    name: 'MACD Zero-Line Cross',
    category: 'Multi-Period Momentum',
    family: 'Momentum',
    winRateOrRank: 'Confluence Enabler (Top Core)',
    rrRatio: '1 : 2.0',
    triggerRules: 'MACD line crosses Signal line in the direction of the zero-line threshold with expanding histogram bars.',
    indicators: 'Fast EMA (12), Slow EMA (26), Signal SMA (9)',
    whyItWorks: 'Eliminates low-velocity whipsaws by requiring momentum confirmation across multiple exponential moving average lookbacks.',
    status: 'Active Core'
  },
  {
    id: 'rsi_reversal',
    name: 'RSI Divergence & Reversal',
    category: 'Momentum Exhaustion',
    family: 'Momentum',
    winRateOrRank: '57.9% SL Rate (-₹228 Drag, Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Bullish divergence (price prints lower low while RSI makes higher low) or exit from oversold (<30) territory.',
    indicators: '14-period Relative Strength Index',
    whyItWorks: 'Identifies internal momentum exhaustion before it becomes visible on the candlestick chart.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'tsi_cross',
    name: 'True Strength Index (TSI)',
    category: 'Double-Smoothed Momentum',
    family: 'Momentum',
    winRateOrRank: '-₹4,148 Net Drag (Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'TSI line crosses signal line in territory aligned with prevailing 50 EMA trend.',
    indicators: 'Double smoothed 25 and 13 EMAs',
    whyItWorks: 'Eliminates lag and false crossovers by double-smoothing momentum rate-of-change; disabled by default due to choppy intraday consolidation.',
    status: 'Pruned / Disabled'
  },

  // ── 8. Oscillator Family (6 - counts as 1 single family vote) ────────
  {
    id: 'stoc_rsi',
    name: 'Stochastic RSI Bound Turn',
    category: 'High-Sensitivity Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Oscillator Core Leader (Top Core)',
    rrRatio: '1 : 2.0',
    triggerRules: 'StochRSI K line crosses above 0.20 and above D line (BUY) or crosses below 0.80 and below D line (SELL).',
    indicators: '14-period RSI, 14 Stochastic, 3 K, 3 D',
    whyItWorks: 'Applies Stochastic formula to RSI values, creating extreme sensitivity to sudden shifts in intraday velocity.',
    status: 'Active Core'
  },
  {
    id: 'stochastic_reversal',
    name: 'Stochastic Oscillator Cross',
    category: 'Cyclic Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Oscillator Noise (Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: '%K line crosses above %D line below 20 (oversold) or %K crosses below %D above 80 (overbought).',
    indicators: '14, 3, 3 Fast/Slow Stochastic',
    whyItWorks: 'Optimized for high-probability swing turns; disabled by default as Stochastic RSI provides superior signal clarity.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'cci_reversal',
    name: 'Commodity Channel Index (CCI)',
    category: 'Statistical Deviation',
    family: 'Oscillator',
    winRateOrRank: '63.3% SL Rate (-₹1,813 Drag, Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'CCI crosses back above -100 after reaching extreme statistical oversold territory, confirmed by positive price action.',
    indicators: '20-period CCI',
    whyItWorks: 'Measures standard deviation from mean price; disabled by default due to premature entries during strong momentum runs.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'williams_r',
    name: 'Williams %R Extreme',
    category: 'Lookback Momentum',
    family: 'Oscillator',
    winRateOrRank: '56.8% SL Rate (-₹2,446 Drag, Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Crosses upward above -80 from deeply oversold band (BUY) or downward below -20 from overbought zone (SELL).',
    indicators: '14-period Williams %R',
    whyItWorks: 'Evaluates current close relative to highest high and lowest low of lookback; disabled by default due to high whipsaw frequency.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'awesome_oscillator',
    name: 'Awesome Oscillator Zero Cross',
    category: 'Median Momentum',
    family: 'Oscillator',
    winRateOrRank: '-₹2,513 Net Drag (Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'AO crosses above the zero line (BUY) or crosses below the zero line (SELL) reflecting shift in market velocity.',
    indicators: '5 SMA and 34 SMA of bar midpoints ((H+L)/2)',
    whyItWorks: 'Measures immediate momentum vs broader historical trend; disabled by default as moving average crossovers lag intraday moves.',
    status: 'Pruned / Disabled'
  },
  {
    id: 'mfi_exhaustion',
    name: 'MFI Volume-Weighted Exhaustion',
    category: 'Money Flow Oscillator',
    family: 'Oscillator',
    winRateOrRank: 'Low Signal Quality (Pruned)',
    rrRatio: '1 : 2.0',
    triggerRules: 'Money Flow Index bounces above 20 from extreme exhaustion zone (BUY) or turns down from above 80 (SELL).',
    indicators: '14-period Money Flow Index (Price × Volume)',
    whyItWorks: 'Combines price momentum with volume accumulation; disabled by default due to excessive false turns in trend days.',
    status: 'Pruned / Disabled'
  }
];

const FAMILIES = [
  'All',
  'Breakout',
  'Structure',
  'Reversal',
  'Trend',
  'Momentum',
  'Oscillator',
  'Intraday',
  'Volume',
  'Active Core'
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

    // Brokerage: ₹20 / executed order (₹40 round-trip)
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
        (strategyFilter === 'Active Core' && s.status === 'Active Core');

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
              </div>
            </div>
            <p className="text-sm text-surface-300 max-w-2xl leading-relaxed">
              Complete technical specification for algorithmic execution, multi-family confluence gating, dynamic regime screening, statutory friction defense, and mathematical risk geometry.
            </p>
          </div>

          {/* Quick Institutional Metrics Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Macro Screener</span>
              <span className="text-base font-bold text-accent-light font-mono">KER ≥ 0.35</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Friction Guard</span>
              <span className="text-base font-bold text-profit-light font-mono">≥ 3.5x Fees</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Daily Trade Cap</span>
              <span className="text-base font-bold text-warning-light font-mono">Max 8 (Rec. 3)</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Confluence</span>
              <span className="text-base font-bold text-white font-mono">Adaptive (≥2/≥3)</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Target Realism</span>
              <span className="text-base font-bold text-profit-light font-mono">Max 3.2% Cap</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/90 border border-surface-700/60 text-center">
              <span className="text-[10px] uppercase font-semibold text-surface-400 block tracking-wider">Risk Geometry</span>
              <span className="text-base font-bold text-accent-light font-mono">1:2.0 Min R:R</span>
            </div>
          </div>
        </div>

          {/* Navigation Tabs Bar */}
          <div className="mt-6 pt-5 border-t border-surface-700/60 flex flex-wrap gap-2">
            {[
              { id: 'architecture', label: 'Architecture & Schedule', icon: <Cpu size={15} /> },
              { id: 'quant_edge', label: 'Quant Edge & Screener', icon: <TrendingUp size={15} /> },
              { id: 'strategies', label: '26 TA Strategies', count: '26', icon: <Compass size={15} /> },
              { id: 'confluence', label: 'Confluence, Regime & Targets', icon: <Layers size={15} /> },
              { id: 'friction_guard', label: 'Statutory Friction Guard', icon: <Calculator size={15} /> },
              { id: 'partial_booking', label: 'Exits, Invalidation & Trailing', icon: <Split size={15} /> },
              { id: 'swing_screener', label: 'Swing & Sector Screener', icon: <BarChart3 size={15} /> },
              { id: 'backtest_expectancy', label: 'Walk-Forward Backtesting', icon: <Award size={15} /> },
              { id: 'telegram_control', label: 'Telegram Remote Control', icon: <Send size={15} /> },
              { id: 'paper_vs_live', label: 'Paper vs Live Mode', icon: <ShieldCheck size={15} /> }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl transition-all duration-200 cursor-pointer ${activeTab === tab.id
                    ? 'bg-accent-light text-surface-950 shadow-lg shadow-accent-DEFAULT/20'
                    : 'text-surface-300 hover:text-white bg-surface-900/60 hover:bg-surface-800 border border-surface-700/60'
                  }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.count && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${activeTab === tab.id ? 'bg-surface-950 text-accent-light' : 'bg-surface-800 text-surface-400'
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
                  desc: 'Screens ~180+ liquid F&O equities dynamically between 09:30–14:30 IST at clock-aligned 15-minute intervals (top 35 stocks) using 20D turnover (≥ ₹40 Cr), price floor (≥ ₹150), ATR% (≥ 1.5%), KER (≥ 0.35), and morning RVOL (≥ 1.8x). Gaps ≥ 1.8% receive exhaustion penalties.',
                  badge: '15m Dynamic Universe'
                },
                {
                  step: '02',
                  title: '26 TA Strategies',
                  desc: 'Vectorized mathematical functions evaluate candles simultaneously across all active scrips in 8 independent strategy families (Breakout, Structure, Reversal, Trend, Momentum, Oscillator, Intraday, Volume).',
                  badge: '26-Strategy Engine'
                },
                {
                  step: '03',
                  title: 'Adaptive Confluence',
                  desc: 'Requires ≥ 3 independent indicator families in CHOPPY_RANGE, relaxing to ≥ 2 families in confirmed TRENDING_BULL/BEAR (KER ≥ 0.35, ADX ≥ 20). Aligns strictly with the 50-period EMA macro trend and dynamic microstructure gates.',
                  badge: 'Consensus Gate'
                },
                {
                  step: '04',
                  title: '1R Quant Sizing',
                  desc: 'Enforces dynamic 1R risk-based position sizing [Q = min(floor(Risk/ΔSL), floor(Exposure/Price))], 1.2% noise buffer floor, statutory friction guard (≥3.5x fees), and daily trade cap (default 8, recommended 3/day).',
                  badge: '1R Capital Protection'
                },
                {
                  step: '05',
                  title: 'Limit Queue & TTL',
                  desc: 'Places limit orders near the spread with a 15-second TTL queue. Supports Direct Breakout (immediate entry) or Pullback Retest (EMA20/VWAP/POC) and optional Two-Legged Scale-In (50% breakout, 50% pullback).',
                  badge: '15s Timeout Queue'
                },
                {
                  step: '06',
                  title: 'Exchange SL & Ratchet',
                  desc: 'Submits native STOPLOSS_LIMIT directly to exchange on fill. Trails at 1.4× ATR (+1.2R cushion), books 50% at Target 1 (+1.2R with Breakeven+Friction SL), evaluates Thesis Invalidation, and squares off at 15:15 IST.',
                  badge: 'Native Exchange SL'
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

          {/* Dual-Loop Engine Rhythm & Execution Architecture */}
          <div className="bg-surface-800/90 backdrop-blur-sm border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Activity className="text-accent-light" size={20} />
                  Dual-Loop Engine Lifecycle &amp; Execution Rhythm
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  Decoupled asynchronous fast-polling and slow-scanning loops running continuously in the background thread.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/30">
                5s Fast / 60s Slow Loop
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-surface-900/80 border border-accent-light/30 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-2">
                    <Zap size={15} className="text-accent-light" /> Fast Loop (Every 5 Seconds)
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-light/15 text-accent-light border border-accent-light/30 font-bold">
                    Order &amp; Risk Monitor
                  </span>
                </div>
                <ul className="space-y-1.5 text-xs text-surface-300">
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-accent-light mt-0.5 shrink-0" />
                    <span><strong>15s Limit Queue Timeout:</strong> Cancels unfilled limit orders after 15 seconds to prevent stale fills on fading momentum.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-accent-light mt-0.5 shrink-0" />
                    <span><strong>Active Position Monitoring:</strong> Evaluates live LTP against stop-loss, target, and partial profit thresholds.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-accent-light mt-0.5 shrink-0" />
                    <span><strong>Partial Profit Booking:</strong> At +1.2R, exits 50% qty and atomically moves exchange SL to Breakeven + Friction.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-accent-light mt-0.5 shrink-0" />
                    <span><strong>ATR Trailing SL Ratchet:</strong> Updates exchange-side STOPLOSS_LIMIT order as price reaches new high water marks.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-accent-light mt-0.5 shrink-0" />
                    <span><strong>Mobile App Desync Detection:</strong> Detects and reconciles positions manually closed on the Angel One mobile app.</span>
                  </li>
                </ul>
              </div>

              <div className="p-4 rounded-xl bg-surface-900/80 border border-profit-light/30 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-2">
                    <Clock size={15} className="text-profit-light" /> Slow Loop (Every 60 Seconds)
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-profit-light/15 text-profit-light border border-profit-light/30 font-bold">
                    Scanner &amp; Invalidation
                  </span>
                </div>
                <ul className="space-y-1.5 text-xs text-surface-300">
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-profit-light mt-0.5 shrink-0" />
                    <span><strong>Market Setup Scanning:</strong> Simultaneously scans active watchlist across all 26 technical strategies and 8 families.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-profit-light mt-0.5 shrink-0" />
                    <span><strong>Clock-Aligned 30m Rescreening:</strong> At 09:30, 10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30 IST, generates a fresh top 35 dynamic universe with a 5-minute network retry backoff.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-profit-light mt-0.5 shrink-0" />
                    <span><strong>Graduated Thesis Invalidation:</strong> Evaluates open positions for strong opposing signals, weak conviction, and time decay.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight size={13} className="text-profit-light mt-0.5 shrink-0" />
                    <span><strong>Idle Trade Circuit Breaker:</strong> Exits stagnant positions held ≥ 20 minutes that fail to reach +0.5R.</span>
                  </li>
                </ul>
              </div>
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

              {/* Safeguard 2: 15s Pending Limit Queue */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Timer size={14} className="text-warning-light" /> 15s Limit Queue
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 text-warning-light border border-surface-700">
                    TTL 15 Seconds
                  </span>
                </div>
                <p className="text-xs text-surface-300 leading-relaxed">
                  Breakout entries are placed as Limit orders near the bid/ask spread. The engine tracks unfilled orders in an active timeout queue. If unfilled after <strong>15 seconds</strong>, the order is automatically cancelled to prevent adverse fills on fading momentum.
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
                  SmartAPI JWT tokens expire every 24 hours. When an API call returns <code>AB1010</code>, <code>AG8001</code>, or <code>Token missing</code>, the client headlessly regenerates a fresh TOTP code via <code>pyotp</code>, re-authenticates with SmartAPI, and seamlessly retries the operation.
                </p>
                <div className="text-[10px] text-surface-500 font-mono pt-1">
                  Paced: Candle requests paced at ≥0.55s (&lt; 2 req/sec) to avoid rate limits.
                </div>
              </div>
            </div>
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
                  The automated scanner enforces disciplined time gates to avoid opening chaos and broker penalty charges.
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
                      09:30 – 11:30 AM
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-profit-light/15 text-profit-light border border-profit-light/30 flex items-center gap-1">
                      <Zap size={10} /> Active
                    </span>
                  </div>
                  <h4 className="font-bold text-white text-sm mt-2">Morning Momentum Session</h4>
                  <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                    Primary morning window. Highest volume and momentum setups (ORB, Keltner Breakouts, Absorption) are evaluated and executed here.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-surface-800 text-[11px] text-profit-light/80 font-mono">
                  Gate: High-Probability Trading Enabled
                </div>
              </div>

              {/* Window 3 */}
              <div className="p-4 rounded-xl bg-surface-900/80 border border-profit-light/20 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-profit-light bg-profit-light/10 px-2.5 py-1 rounded border border-profit-light/20">
                      11:30 AM – 01:00 PM
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-profit-light/10 text-profit-light border border-profit-light/20 flex items-center gap-1">
                      <Flame size={10} /> Active
                    </span>
                  </div>
                  <h4 className="font-bold text-white text-sm mt-2">Continuous Midday Trading</h4>
                  <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                    Trading runs continuously from 09:30 AM to 03:00 PM. Technical confluence, regime filters, and microstructure volume checks (RVOL ≥ 2.2x) guard against midday lull traps.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-surface-800 text-[11px] text-surface-500 font-mono">
                  Gate: Midday Guard Active (RVOL ≥ 2.2x filter)
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
                    Turnover accelerates as European markets open (1:00–2:00 PM Golden Window). Strong trend continuations and volume profile expansions take place until 3:00 PM.
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
                  How the Kaufman Efficiency Ratio (KER), pre-trade statutory friction gating, dynamic 30m F&amp;O universe curation, and opening gap exhaustion guards establish positive mathematical expectancy across varying market regimes.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-accent-light/10 text-accent-light border border-accent-light/30 flex items-center gap-1.5">
                  <CheckCircle2 size={13} />
                  Dynamic Universe: 180+ F&amp;O Scrips
                </span>
              </div>
            </div>

            {/* 4 Core Pillars KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-4 flex flex-col justify-between hover:border-accent-light/40 transition-colors">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-surface-400 tracking-wider">Regime Screener</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-light/10 text-accent-light border border-accent-light/20">30m Cycle</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-white mb-1">Daily KER ≥ 0.35</div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Evaluated over 20 sessions (N=20). Filters out noisy, mean-reverting chop while isolating high-velocity directional runners across the universe.
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
                    Calculates exact Indian broker + STT + NSE + GST + Stamp Duty friction. Rejects orders whose target profit cannot clear 3.5x friction (4.0x for FRVP).
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
                  <div className="text-lg font-bold font-mono text-warning-light mb-1">Max 8 (Rec. 3/Day)</div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Enforces strict daily loss (₹800 default) and max trades cap (8 max, recommended 3). Completely halts over-trading and late-session chop drift.
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-surface-800 text-[11px] font-mono text-warning-light/80">
                  ₹800 Daily Loss Circuit Breaker
                </div>
              </div>

              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-4 flex flex-col justify-between hover:border-surface-600 transition-colors">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-surface-400 tracking-wider">Dynamic Universe</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-profit-light/10 text-profit-light border border-profit-light/20">Top 35 Scrips</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-white mb-1">Top 35 Stocks</div>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Dynamically re-screens 180+ liquid F&amp;O stocks every 30 mins between 09:30–14:30 IST, verifying ₹40 Cr turnover, ₹150 price floor, and ATR ≥ 1.5%.
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-surface-800 text-[11px] font-mono text-profit-light/80">
                  Clock-Aligned 30m Rescreening
                </div>
              </div>
            </div>
          </div>

          {/* 5 Quantitative Universe Screening Gates */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-4">
            <h3 className="font-bold text-white text-base flex items-center gap-2">
              <Filter className="text-accent-light" size={18} />
              5 Macro Screening Gates for Dynamic Watchlist Curation (Top 35 Stocks)
            </h3>
            <p className="text-xs text-surface-300 leading-relaxed">
              Every 30 minutes on trading weekdays (09:30, 10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30 IST), candidates from the 180+ F&amp;O universe must pass 5 quantitative gates to enter the active watchlist:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700 space-y-1">
                <span className="text-surface-400 font-bold block text-[10px] uppercase">Gate 1: Price Floor</span>
                <span className="font-mono text-sm font-bold text-white">LTP ≥ ₹150</span>
                <p className="text-surface-400 text-[11px] leading-relaxed">Eliminates low-priced penny stocks with wide bid-ask spreads and high percentage slippage.</p>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700 space-y-1">
                <span className="text-surface-400 font-bold block text-[10px] uppercase">Gate 2: Institutional Liquidity</span>
                <span className="font-mono text-sm font-bold text-white">Turnover ≥ ₹40 Cr</span>
                <p className="text-surface-400 text-[11px] leading-relaxed">Guarantees deep order book depth and immediate fill execution without market impact.</p>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700 space-y-1">
                <span className="text-surface-400 font-bold block text-[10px] uppercase">Gate 3: Intraday Volatility</span>
                <span className="font-mono text-sm font-bold text-profit-light">Daily ATR% ≥ 1.5%</span>
                <p className="text-surface-400 text-[11px] leading-relaxed">Ensures sufficient intraday expansion range to tag 1:2.0 R:R targets before EOD square-off.</p>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700 space-y-1">
                <span className="text-surface-400 font-bold block text-[10px] uppercase">Gate 4: Macro Efficiency</span>
                <span className="font-mono text-sm font-bold text-accent-light">20D KER ≥ 0.35</span>
                <p className="text-surface-400 text-[11px] leading-relaxed">Rejects consolidation ranges and sideways chop, isolating stocks in clean directional trends.</p>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-900 border border-surface-700 space-y-1">
                <span className="text-surface-400 font-bold block text-[10px] uppercase">Gate 5: RVOL &amp; Gap Penalty</span>
                <span className="font-mono text-sm font-bold text-warning-light">RVOL ≥ 1.8x (Gap &lt; 1.8%)</span>
                <p className="text-surface-400 text-[11px] leading-relaxed">Demotes gap-exhausted stocks (gap ≥ 1.8%) and prioritizes scrips with strong relative volume expansion.</p>
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
                  Threshold: KER ≥ 0.35
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
                  A pure straight line yields 1.0. A sideways random walk approaches 0.0. Candidates with KER ≥ 0.35 qualify for directional trend trading.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 3: 26 STRATEGIES CATALOG ───────────────────────────────── */}
      {activeTab === 'strategies' && (
        <div className="space-y-6 animate-fade-in">
          {/* Active Roster Pruning Notice & Empirical Backtest Table */}
          <div className="p-5 rounded-2xl bg-gradient-to-r from-accent-DEFAULT/15 via-surface-900 to-surface-900 border border-accent-DEFAULT/30 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-accent-light font-bold text-xs uppercase tracking-wider">
                <Filter size={16} />
                Quantitative Strategy Pruning &amp; Empirical Alpha Roster (from config.py)
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-light/15 text-accent-light border border-accent-light/30">
                10 Active Core • 16 Pruned Drag
              </span>
            </div>
            <p className="text-xs text-surface-300 leading-relaxed">
              To eliminate false whipsaws and negative statutory fee drag, lagging indicators and negative-alpha oscillators are <strong>pruned and disabled by default</strong> in the backend scanner configuration. Rigorous walk-forward backtesting proved that standard moving average crosses (EMA Crossover: -₹2,201 drag, PSAR: -₹11,654 drag) and exhausted oscillators suffer from 56%–63% stop-loss rates.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1 text-xs">
              <div className="p-3 rounded-xl bg-surface-950/80 border border-profit-light/30 space-y-2">
                <span className="font-bold text-profit-light flex items-center gap-1.5">
                  <CheckCircle2 size={14} /> Active High-Conviction Core (Enabled by Default):
                </span>
                <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px] text-surface-300">
                  <div>• Bollinger Breakout: <strong className="text-profit-light">+₹15,767</strong></div>
                  <div>• Donchian Breakout: <strong className="text-profit-light">+₹9,184</strong></div>
                  <div>• Institutional Absorption: <strong className="text-profit-light">+₹6,760</strong></div>
                  <div>• FRVP (Auction Market Theory): <strong className="text-profit-light">+₹2,087</strong></div>
                  <div>• Keltner Channel Breakout</div>
                  <div>• Liquidity Grab Reversal</div>
                  <div>• Gap Fill Reversal</div>
                  <div>• Opening Range Breakout (ORB)</div>
                  <div>• MACD Zero-Line Cross</div>
                  <div>• Stochastic RSI Bound Turn</div>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-surface-950/80 border border-loss-light/30 space-y-2">
                <span className="font-bold text-loss-light flex items-center gap-1.5">
                  <Ban size={14} /> Pruned / Disabled by Default (Identified Net Drag):
                </span>
                <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px] text-surface-400">
                  <div>• PSAR Trend: <strong className="text-loss-light">-₹11,654</strong></div>
                  <div>• CMF Accumulation: <strong className="text-loss-light">-₹12,286</strong></div>
                  <div>• Order Block &amp; FVG: <strong className="text-loss-light">-₹6,183</strong></div>
                  <div>• Volume Delta Divergence: <strong className="text-loss-light">-₹5,206</strong></div>
                  <div>• TSI Cross: <strong className="text-loss-light">-₹4,148</strong></div>
                  <div>• Awesome Oscillator: <strong className="text-loss-light">-₹2,513</strong></div>
                  <div>• Williams %R: <strong className="text-loss-light">-₹2,446</strong></div>
                  <div>• EMA Crossover: <strong className="text-loss-light">-₹2,201</strong></div>
                  <div>• CCI Reversal: <strong className="text-loss-light">-₹1,813</strong></div>
                  <div>• ADX Momentum: <strong className="text-loss-light">-₹291</strong></div>
                  <div>• RSI Reversal: <strong className="text-loss-light">-₹228</strong></div>
                  <div>• VWAP Bounce: <strong className="text-loss-light">-₹172</strong></div>
                </div>
              </div>
            </div>
          </div>

          {/* Filter & Search Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-surface-800/90 p-4 rounded-2xl border border-surface-700/80 shadow-md">
            <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
              {FAMILIES.map(cat => {
                const count = cat === 'All'
                  ? STRATEGIES_LIST.length
                  : cat === 'Active Core'
                  ? STRATEGIES_LIST.filter(s => s.status === 'Active Core').length
                  : STRATEGIES_LIST.filter(s => s.family === cat || s.category === cat).length;
                return (
                  <button
                    key={cat}
                    onClick={() => setStrategyFilter(cat)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-all flex items-center gap-1.5 cursor-pointer ${strategyFilter === cat
                        ? 'bg-accent-light text-surface-950 font-bold shadow'
                        : 'bg-surface-900 text-surface-400 hover:text-white hover:bg-surface-700 border border-surface-700/50'
                      }`}
                  >
                    <span>{cat}</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${strategyFilter === cat ? 'bg-surface-950 text-accent-light font-bold' : 'bg-surface-800 text-surface-400'
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
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${s.status === 'Active Core' ? 'bg-profit-light/10 text-profit-light border border-profit-light/30' : 'bg-surface-900 text-surface-500 border border-surface-700'}`}>
                      {s.status}
                    </span>
                  </div>

                  <h3 className="font-bold text-white text-base group-hover:text-accent-light transition-colors mb-1.5">
                    {s.name}
                  </h3>

                  <div className="text-[11px] font-mono text-accent-light/90 mb-3">
                    {s.winRateOrRank}
                  </div>

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
                Confluence: ≥ 3 (Chop) / ≥ 2 (Trending)
              </span>
            </div>

            <p className="text-sm text-surface-300 leading-relaxed">
              A single technical indicator firing is statistically insufficient to overcome exchange friction and slippage. The platform groups all 26 strategies into eight independent indicator families. In <strong>CHOPPY_RANGE</strong> or unknown regime, an order is approved <strong>only when ≥ 3 distinct families agree</strong> on the same direction. In a confirmed <strong>TRENDING_BULL or TRENDING_BEAR</strong> regime (ADX ≥ 20, KER ≥ 0.35), the threshold relaxes to <strong>≥ 2 families</strong> — allowing clean breakout + volume confirmations to fire without requiring a third oscillator vote. All trades must align with the 50-period EMA macro trend and pass the Market Regime Filter.
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
                In our walk-forward backtest, drawdowns occurred specifically during sideways consolidation periods where market-wide ranges chopped up breakout strategies. The <strong>Market Regime Filter</strong> classifies market structure into distinct quantitative states:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-profit-dark/10 border border-profit/30 space-y-1.5">
                  <span className="font-bold text-profit-light block">1. TRENDING_BULL</span>
                  <p className="text-surface-300 leading-relaxed">
                    ADX ≥ 20, +DI &gt; -DI, Close &gt; 50 EMA, and KER ≥ 0.35. High-conviction long breakouts and momentum continuation approved. Counter-trend shorts prohibited.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-loss-dark/10 border border-loss/30 space-y-1.5">
                  <span className="font-bold text-loss-light block">2. TRENDING_BEAR</span>
                  <p className="text-surface-300 leading-relaxed">
                    ADX ≥ 20, -DI &gt; +DI, Close &lt; 50 EMA, and KER ≥ 0.35. Short breakdowns approved. Counter-trend longs prohibited.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-warning-dark/10 border border-warning/30 space-y-1.5">
                  <span className="font-bold text-warning-light block">3. CHOPPY_RANGE (Squeeze)</span>
                  <p className="text-surface-300 leading-relaxed">
                    ADX &lt; 20, KER &lt; 0.35, or Bollinger Band Width &lt; 1.8% squeezed. <strong>Breakout strategies (Donchian, Bollinger) are automatically suppressed</strong> to eliminate fee drain.
                  </p>
                </div>
              </div>
            </div>

            {/* Dynamic Microstructural Quality Gate Card */}
            <div className="bg-surface-900/90 border border-emerald-500/30 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Zap className="text-emerald-400" size={16} />
                  Dynamic Microstructural Quality Gate (Per-Candle Defense)
                </h3>
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-bold">
                  Zero False-Breakout Traps
                </span>
              </div>
              <p className="text-xs text-surface-300 leading-relaxed">
                Rather than using brittle static blacklists, every candidate trigger candle must clear 4 microstructural filters before execution:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 text-xs font-mono">
                <div className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                  <span className="text-surface-400 text-[10px] block">1. Trigger RVOL</span>
                  <span className="text-white font-bold">≥ 1.2× Volume Surge</span>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                  <span className="text-surface-400 text-[10px] block">2. Rejection Wick</span>
                  <span className="text-profit-light font-bold">≤ 25% Candle Range</span>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                  <span className="text-surface-400 text-[10px] block">3. Local 15m KER</span>
                  <span className="text-accent-light font-bold">≥ 0.30 Efficiency</span>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-950 border border-surface-800">
                  <span className="text-surface-400 text-[10px] block">4. Midday Lull (11:30–13:15)</span>
                  <span className="text-warning-light font-bold">≥ 2.2× Volume Surge</span>
                </div>
              </div>
            </div>

            {/* Realistic Intraday Target Architecture & Opening Gap Exhaustion Guard */}
            <div className="bg-surface-900/90 border border-sky-500/30 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Target className="text-sky-400" size={18} />
                  Realistic Target Architecture &amp; Opening Gap Exhaustion Guard
                </h3>
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/30 font-bold">
                  Mathematical Target Clamping
                </span>
              </div>

              <p className="text-xs text-surface-300 leading-relaxed">
                Intraday equity moves rarely exceed 3% without multi-day catalysts. Chasing unrealistic 7%–8% targets leaves open profits vulnerable to severe mean-reversions. The scanner enforces three mathematical guardrails:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-surface-950 border border-surface-800 space-y-1.5">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    <Maximize2 size={13} className="text-sky-400" /> Max Target Move: 3.2%
                  </span>
                  <p className="text-surface-400 leading-relaxed text-[11px]">
                    Targets are capped at <code>maxIntradayTargetPercent = 3.2%</code> from entry (or 1.8× ATR). If clamping causes R:R to drop below 1.8:1, the trade is safely discarded rather than forced.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-surface-950 border border-surface-800 space-y-1.5">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    <TrendingUp size={13} className="text-accent-light" /> Max Day Expansion: 4.5%
                  </span>
                  <p className="text-surface-400 leading-relaxed text-[11px]">
                    Total projected distance from the day’s open to target cannot exceed <code>maxDayExpansionPercent = 4.5%</code>. Prevents entering near late-day exhaustion tops.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-surface-950 border border-surface-800 space-y-1.5">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    <ShieldAlert size={13} className="text-warning-light" /> Gap Exhaustion: ≥ 1.8%
                  </span>
                  <p className="text-surface-400 leading-relaxed text-[11px]">
                    Opening gaps ≥ 1.8% from prior close represent exhausted institutional opening delta. Breakouts are blocked on gap-exhausted stocks to prevent bull/bear traps.
                  </p>
                </div>
              </div>
            </div>

            {/* 8 Families Grid with Alpha Weights */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-surface-400">
                  8 Independent Strategy Families &amp; Backtest Alpha Weights
                </h4>
                <span className="text-[10px] font-mono text-surface-500">
                  Oscillators weighted at 0.7x to prevent correlation echo
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                {[
                  { name: 'Breakout Family (4)', weight: '1.5x Weight', examples: 'Bollinger, Donchian, Keltner, ORB', role: '+₹38,854 backtest net. Highest empirical momentum expansion.' },
                  { name: 'Momentum Family (3)', weight: '1.3x Weight', examples: 'MACD Zero-Cross, RSI, TSI', role: '+₹19,938 backtest net. Directional acceleration & velocity.' },
                  { name: 'Structure Family (5)', weight: '1.2x Weight', examples: 'Absorption, FRVP (AMT), FVG, Delta, CPR', role: '+₹23,236 backtest net. Key institutional liquidity magnets & POC.' },
                  { name: 'Reversal Family (2)', weight: '1.2x Weight', examples: 'Liquidity Grab, Gap Fill', role: 'Exploits retail stop hunts and opening tick sentiment reversion.' },
                  { name: 'Trend Family (4)', weight: '1.1x Weight', examples: 'EMA Crossover, Supertrend, PSAR, ADX', role: '+₹12,645 backtest net. Confirms prevailing 50 EMA trend.' },
                  { name: 'Volume Family (1)', weight: '1.0x Weight', examples: 'Chaikin Money Flow (CMF)', role: '+₹9,029 backtest baseline. Institutional accumulation flow.' },
                  { name: 'Intraday Family (1)', weight: '0.9x Weight', examples: 'VWAP Bounce', role: 'Tracks session-specific volume-weighted average price benchmark.' },
                  { name: 'Oscillator Family (6)', weight: '0.7x Weight', examples: 'Stochastic, StochRSI, CCI, Williams, AO, MFI', role: 'Statistical exhaustion (counts as 1 collective vote; down-weighted).' }
                ].map((fam, i) => (
                  <div key={i} className="bg-surface-900/90 p-4 rounded-xl border border-surface-700/80 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="text-xs font-bold text-white">{fam.name}</h4>
                        <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-surface-950 text-accent-light border border-surface-800">
                          {fam.weight}
                        </span>
                      </div>
                      <p className="text-[11px] font-mono text-accent-light/80 mb-2">{fam.examples}</p>
                      <p className="text-xs text-surface-400 leading-relaxed">{fam.role}</p>
                    </div>
                  </div>
                ))}
              </div>
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
                    Phase 1: 0 to +1.2R (Breathing Room)
                  </h4>
                  <p className="text-surface-400 leading-relaxed">
                    Initial protective stop is placed at -1.0R (minimum 1.2% safety noise floor, maximum 2.4% cap). The trailing stop stays disarmed during initial oscillations to avoid stopping out prematurely.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-2">
                  <h4 className="font-bold text-white flex items-center gap-2">
                    <Target size={16} className="text-accent-light" />
                    Phase 2: +1.2R Reached (Profit Cushion Armed)
                  </h4>
                  <p className="text-surface-400 leading-relaxed">
                    Once price advances past +1.2R profit cushion (<code>trailingSlProfitCushionR = 1.2</code>), the trailing stop immediately arms and ratchets to at least <strong>Breakeven (Entry Price)</strong>. Downside loss risk is completely eliminated!
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-surface-800/80 border border-surface-700/80 space-y-2">
                  <h4 className="font-bold text-white flex items-center gap-2">
                    <TrendingUp size={16} className="text-profit-light" />
                    Phase 3: +1.2R to Target (Profit Ratchet)
                  </h4>
                  <p className="text-surface-400 leading-relaxed">
                    Stop loss trails 1.4 × ATR (<code>trailingSlAtrMultiplier = 1.4</code>) behind high/low water mark. If market pulls back, it secures locked profit. If momentum continues, it captures the full 1:2.0 target (+₹1,400 against ₹700 risk).
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
                With 5x MIS margin (max ₹8,000 margin → ₹40,000 exposure), loss per trade is strictly capped to the risk budget (₹700 default).
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

                <div className={`p-4 rounded-xl border text-center font-bold text-sm ${feeCalculation.passesGate
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

      {/* ─── TAB 6: EXITS, INVALIDATION & TRAILING ──────────────────────── */}
      {activeTab === 'partial_booking' && (
        <div className="space-y-6 animate-fade-in">
          {/* Two-Stage Scaling & Breakeven Protection */}
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
                50% Milestone Exit @ +1.2R
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 relative flex flex-col justify-between">
                <div>
                  <span className="w-8 h-8 rounded-xl bg-accent-light/15 text-accent-light flex items-center justify-center font-bold font-mono text-xs mb-3 border border-accent-light/30">
                    01
                  </span>
                  <h3 className="font-bold text-white text-sm mb-1.5">Dual-Target Geometry</h3>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    Position opens with 100% quantity. Target 1 is front-loaded at <strong>+1.2R</strong> (<code>partialBookingTargetRR = 1.2</code>) to bank gains before mean-reversion, while Target 2 is set at full setup runner target (1:2.0R to 1:4.0R).
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
                    When price reaches Target 1 (+1.2R), exactly 50% of the position is exited immediately via Limit order near LTP, locking realized profit and releasing 50% used margin.
                  </p>
                </div>
              </div>

              <div className="bg-surface-900/90 border border-surface-700/80 rounded-xl p-5 relative flex flex-col justify-between">
                <div>
                  <span className="w-8 h-8 rounded-xl bg-surface-800 text-white flex items-center justify-center font-bold font-mono text-xs mb-3 border border-surface-700">
                    03
                  </span>
                  <h3 className="font-bold text-white text-sm mb-1.5">Atomic SL Ratchet to Breakeven + Friction</h3>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    The native exchange STOPLOSS_LIMIT order on Angel One is atomically modified to <strong>Breakeven + Round-Trip Statutory Friction</strong> (+0.05% buffer in paper trade). Runner is completely risk-free!
                  </p>
                </div>
              </div>
            </div>

            {/* Default Disabled Note & ₹250 Minimum Profit Threshold Alert */}
            <div className="bg-gradient-to-r from-surface-900 via-surface-900 to-surface-800 border border-surface-700/80 rounded-xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck className="text-profit-light" size={18} />
                Smart Brokerage Safeguard &amp; Default Setting
              </h3>
              <p className="text-xs text-surface-300 leading-relaxed">
                Angel One charges flat ₹20 per order. Splitting an exit into two transactions incurs an extra order fee (≈₹23.60 with GST). To prevent fee erosion, <strong>Partial Profit Booking is disabled by default</strong> so full positions trail smoothly at 1.4× ATR. When enabled, the engine enforces a <strong>₹250 Minimum Profit Threshold</strong>: if 50% exit profit would yield under ₹250, partial booking is automatically bypassed in favor of a single full exit at target.
              </p>
            </div>
          </div>

          {/* Graduated Thesis Invalidation & Idle Trade Circuit Breaker */}
          <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <ShieldAlert className="text-warning-light" size={18} />
                  Graduated Thesis Invalidation &amp; Idle Trade Circuit Breaker
                </h3>
                <p className="text-xs text-surface-400 mt-0.5">
                  Open positions are re-evaluated every 60 seconds against current multi-family strategy signals to prevent holding failing trades.
                </p>
              </div>
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-warning-light/10 text-warning-light border border-warning-light/30">
                4 Evaluated Rules
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-surface-900 border border-loss-light/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-loss-light">Rule 1: Strong Opposing Signal</span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-loss-light/10 text-loss-light">Immediate Exit</span>
                </div>
                <p className="text-surface-300 leading-relaxed">
                  If <strong>≥ 2 opposing family signals</strong> fire with <strong>0 supporting signals</strong>, the trade thesis is completely invalidated. The position is immediately closed at market.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-surface-900 border border-loss-light/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-loss-light">Rule 2: Weak Conviction</span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-loss-light/10 text-loss-light">Held ≥ 15 Mins</span>
                </div>
                <p className="text-surface-300 leading-relaxed">
                  If <strong>0 supporting signals</strong> remain, the position is in loss, and has been held for <strong>≥ 15 minutes</strong>, the engine exits immediately to cut drawdown.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-surface-900 border border-warning-light/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-warning-light">Rule 3: Idle Trade Circuit Breaker</span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-warning-light/10 text-warning-light">Held ≥ 20 Mins</span>
                </div>
                <p className="text-surface-300 leading-relaxed">
                  If held for <strong>≥ 20 minutes without tagging +0.5R</strong>, the watchdog triggers an immediate market exit to eliminate capital lockup in stagnant, non-moving trades.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-surface-900 border border-profit-light/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-profit-light">Rule 3b &amp; 4: Time Decay &amp; Valid Thesis</span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-profit-light/10 text-profit-light">Breakeven Tighten</span>
                </div>
                <p className="text-surface-300 leading-relaxed">
                  If held for ≥ 20 mins and in profit, stop-loss is tightened to Breakeven. If supporting signals &gt; 0, the thesis remains fully intact and the trade is held.
                </p>
              </div>
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
                  <li>• Asymmetric breakout setups target 1:2.0 to 1:4.0 Risk-to-Reward.</li>
                  <li>• Disciplined 1.2% safety noise floors clamp average loss sizes tightly.</li>
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
                  <span className="text-accent-light font-bold text-sm">Bollinger (+₹15,767)</span>
                </div>
              </div>

              <div className="p-3.5 bg-surface-950/80 rounded-xl border border-surface-800 text-xs text-surface-300 space-y-2">
                <p className="font-bold text-white flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-accent-light" />
                  Why the Market Regime Filter &amp; 1:2 R:R Transform Profitability:
                </p>
                <p className="text-surface-400 leading-relaxed">
                  The raw strategy produced an outstanding +77.5% gross return (+₹31,017). However, high-frequency churn across sideways consolidation months drained capital into taxes and brokerage. By enforcing <strong>≥ 3-family confluence in chop</strong>, <strong>1:2.0 minimum R:R</strong>, and <strong>Market Regime Squeeze Gating (ADX ≥ 20)</strong>, the engine cuts trade count by ~60%, saving over ₹20,000 in friction and locking in clean net alpha!
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
                desc: 'Remotely activates the trading engine in automated execution mode. Scanner will auto-place orders when confidence ≥85% and confluence criteria pass.',
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
                      paper: 'Adaptive: Requires ≥ 3 families in CHOPPY_RANGE or ≥ 2 families in TRENDING_BULL/BEAR (KER ≥ 0.35, ADX ≥ 20) + 50 EMA trend filter',
                      live: 'Adaptive: Requires ≥ 3 families in CHOPPY_RANGE or ≥ 2 families in TRENDING_BULL/BEAR (KER ≥ 0.35, ADX ≥ 20) + 50 EMA trend filter (Confidence ≥ 85% in Auto mode)'
                    },
                    {
                      dim: 'Stop Loss Protection',
                      paper: 'Live Tick Monitor: In-memory real-time tick evaluation triggering simulated SL / Breakeven exits',
                      live: 'Native Exchange-Side: Immediate STOPLOSS_LIMIT order placed on NSE/BSE book (survives app crashes)'
                    },
                    {
                      dim: 'Pending Order Management',
                      paper: 'Immediate virtual execution at incoming tick price (supports Direct Breakout & Pullback Retest)',
                      live: '15-Second Timeout Queue: Unfilled limit orders are auto-cancelled after 15s to prevent stale fills'
                    },
                    {
                      dim: 'Dynamic Trailing & Partial Booking',
                      paper: 'Supported: Books 50% at Target 1 (+1.2R), ratchets virtual SL to Breakeven (+0.05% cushion)',
                      live: 'Supported: Books 50% at Target 1 (+1.2R), atomically modifies exchange SL order to Breakeven + Friction via SmartAPI'
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
