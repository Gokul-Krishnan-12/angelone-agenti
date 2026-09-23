"""
Scanner — multi-strategy market scanner with confluence gate and regime filter.

Architecture
------------
Each symbol is processed through the full enabled strategy suite.  Raw signals
are then filtered by a **Confluence Gate** before being forwarded to the
trading engine / UI:

1. Regime Filter   — symbols with ADX < 18 (volatile/choppy) are skipped for
                     new entries.
2. Market Hours    — no new entry signals in the first ``noEntryFirstMins``
                     minutes after market open (default 15 min = 9:15–9:30 IST).
3. Confluence Gate — signals for a given symbol+direction are grouped by
                     *signal family*.  Oscillator-family strategies (6 indicators)
                     count as ONE vote.  A minimum of 2 independent families must
                     agree before a signal is forwarded.
4. R:R Gate        — signals with risk-reward < ``minRiskReward`` (default 1.8)
                     are discarded.

Each forwarded signal is enriched with:
  • confluenceScore  — number of distinct voting families
  • familiesVoting   — list of family names
  • strategyCount    — total number of strategy signals in this direction
  • allStrategies    — names of all strategies that voted

Signal Families
---------------
  trend:     ema_crossover, supertrend, psar_trend, adx_momentum
  momentum:  macd_cross, rsi_reversal, tsi_cross
  oscillator: stochastic_reversal, stoc_rsi, cci_reversal, williams_r,
              awesome_oscillator, mfi_exhaustion   ← counts as 1 family
  breakout:  bollinger_breakout, donchian_breakout, keltner_breakout
  intraday:  vwap_bounce
  volume:    cmf_accumulation
  structure: institutional_absorption, order_block_fvg, volume_delta_divergence
"""

import datetime
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

from .config import config_manager
from .market_regime import classify_market_regime, is_trade_allowed_by_regime
from .smartapi_client import smart_api_client
from .strategies.adx_momentum import ADXMomentumStrategy
from .strategies.awesome_oscillator import AwesomeOscillatorStrategy
from .strategies.bollinger_breakout import BollingerBreakoutStrategy
from .strategies.cci_reversal import CCIReversalStrategy
from .strategies.cmf_accumulation import CMFAccumulationStrategy
from .strategies.cpr_breakout_reversal import CPRBreakoutReversalStrategy
from .strategies.donchian_breakout import DonchianBreakoutStrategy
from .strategies.ema_crossover import EMACrossoverStrategy
from .strategies.fixed_range_volume_profile import (
    FixedRangeVolumeProfileStrategy,
)
from .strategies.gap_fill import GapFillStrategy
from .strategies.institutional_absorption import InstitutionalAbsorptionStrategy
from .strategies.keltner_breakout import KeltnerBreakoutStrategy
from .strategies.liquidity_grab_reversal import LiquidityGrabReversalStrategy
from .strategies.macd_cross import MACDCrossStrategy
from .strategies.mfi_exhaustion import MFIExhaustionStrategy
from .strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from .strategies.order_block_fvg import OrderBlockFVGStrategy
from .strategies.psar_trend import PSARTrendStrategy
from .strategies.rsi_reversal import RSIReversalStrategy
from .strategies.stoc_rsi import StochRSIStrategy
from .strategies.stochastic_reversal import StochasticReversalStrategy
from .strategies.supertrend import SupertrendStrategy
from .strategies.tsi_cross import TSICrossStrategy
from .strategies.volume_delta_divergence import VolumeDeltaDivergenceStrategy
from .strategies.vwap_bounce import VWAPBounceStrategy
from .strategies.williams_r import WilliamsRStrategy

# ── Strategy family definitions ─────────────────────────────────────────────
# Each family counts as exactly ONE vote in the confluence score, regardless of
# how many individual strategies within that family fire.

STRATEGY_FAMILIES: Dict[str, Set[str]] = {
    "trend": {"ema_crossover", "supertrend", "psar_trend", "adx_momentum"},
    "momentum": {"macd_cross", "rsi_reversal", "tsi_cross"},
    "oscillator": {
        "stochastic_reversal",
        "stoc_rsi",
        "cci_reversal",
        "williams_r",
        "awesome_oscillator",
        "mfi_exhaustion",
    },
    "breakout": {
        "bollinger_breakout",
        "donchian_breakout",
        "keltner_breakout",
        "opening_range_breakout",
    },
    "intraday": {"vwap_bounce"},
    "volume": {"cmf_accumulation"},
    "structure": {
        "institutional_absorption",
        "order_block_fvg",
        "volume_delta_divergence",
        "cpr_breakout_reversal",
        "fixed_range_volume_profile",
    },
    # High-win-rate reversal strategies form their own family
    "reversal": {"liquidity_grab_reversal", "gap_fill"},
}

# ── Weighted confluence scoring ───────────────────────────────────────────────
# Families are weighted by their empirical alpha contribution from backtests.
# Breakout + momentum + structure families carry the most edge; oscillators
# (which are often correlated) carry less weight so multi-oscillator combos
# don’t artificially inflate the confluence score past the gate.
#
# Backtest evidence (60d high-beta universe):
#   breakout family  → +₹38,854 net   ⇒ weight 1.5×
#   structure family → +₹23,236 net   ⇒ weight 1.2×
#   momentum family  → +₹19,938 net   ⇒ weight 1.3×
#   volume family    → +₹9,029  net   ⇒ weight 1.0× (baseline)
#   trend family     → +₹12,645 net   ⇒ weight 1.1×
#   reversal family  → positive        ⇒ weight 1.2×
#   oscillator family→ lower alpha     ⇒ weight 0.7× (prevents oscillator echo)

FAMILY_WEIGHTS: Dict[str, float] = {
    "breakout": 1.5,
    "momentum": 1.3,
    "structure": 1.2,
    "reversal": 1.2,
    "trend": 1.1,
    "volume": 1.0,
    "intraday": 0.9,
    "oscillator": 0.7,   # correlated indicators; weighted down to avoid fake confluence
    "other": 0.8,
}


def _get_strategy_family(strategy_id: str) -> str:
    """Map a strategy ID to its signal family name."""
    for family, strats in STRATEGY_FAMILIES.items():
        if strategy_id in strats:
            return family
    return "other"


def _is_market_open_phase(no_entry_mins: int) -> bool:
    """
    Return True if the current time is within the no-entry window after
    market open (9:15 IST + no_entry_mins).
    """
    now = datetime.datetime.now()
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    no_entry_end = market_open + datetime.timedelta(minutes=no_entry_mins)
    return market_open <= now < no_entry_end


def _is_entry_window(no_entry_mins: int = 15, ker: float = 0.50) -> bool:
    """
    Return True if current time falls within the continuous intraday entry window.

    Intraday trading window:
      • Active continuously from market opening buffer (09:15 + no_entry_mins, e.g. 09:30)
        all the way through 15:00 IST (pre-square-off cutoff).
      • Midday restriction removed: technical confluence, regime gates, and 1:2 R:R geometry
        protect entries without arbitrary time-of-day lockouts.
    """
    now = datetime.datetime.now().time()
    market_open_t = datetime.time(9, 15)
    market_close_t = datetime.time(15, 0)  # No new entries in last 30 minutes

    # Outside market hours → don't gate (backtest / paper trading)
    if now < market_open_t or now > datetime.time(15, 30):
        return True

    start_min = 15 + max(0, no_entry_mins)
    start_hour = 9 + (start_min // 60)
    start_minute = start_min % 60
    window_start = datetime.time(start_hour, start_minute)

    # Active continuous intraday trading from window_start to 15:00 IST
    return window_start <= now <= market_close_t



# ─── Scanner ──────────────────────────────────────────────────────────────────


class Scanner:
    def __init__(self):
        self.strategies: Dict[str, Any] = {
            "ema_crossover": EMACrossoverStrategy(),
            "rsi_reversal": RSIReversalStrategy(),
            "vwap_bounce": VWAPBounceStrategy(),
            "supertrend": SupertrendStrategy(),
            "macd_cross": MACDCrossStrategy(),
            "bollinger_breakout": BollingerBreakoutStrategy(),
            "stochastic_reversal": StochasticReversalStrategy(),
            "adx_momentum": ADXMomentumStrategy(),
            "psar_trend": PSARTrendStrategy(),
            "donchian_breakout": DonchianBreakoutStrategy(),
            "cci_reversal": CCIReversalStrategy(),
            "williams_r": WilliamsRStrategy(),
            "mfi_exhaustion": MFIExhaustionStrategy(),
            "keltner_breakout": KeltnerBreakoutStrategy(),
            "awesome_oscillator": AwesomeOscillatorStrategy(),
            "tsi_cross": TSICrossStrategy(),
            "stoc_rsi": StochRSIStrategy(),
            "institutional_absorption": InstitutionalAbsorptionStrategy(),
            "order_block_fvg": OrderBlockFVGStrategy(),
            "cmf_accumulation": CMFAccumulationStrategy(),
            "volume_delta_divergence": VolumeDeltaDivergenceStrategy(),
            # ── High-win-rate strategies (new) ──────────────────────────
            "opening_range_breakout": OpeningRangeBreakoutStrategy(),
            "liquidity_grab_reversal": LiquidityGrabReversalStrategy(),
            "gap_fill": GapFillStrategy(),
            "cpr_breakout_reversal": CPRBreakoutReversalStrategy(),
            "fixed_range_volume_profile": FixedRangeVolumeProfileStrategy(),
        }
        self.candle_cache: Dict[Any, pd.DataFrame] = {}
        self.last_cache_time: Dict[Any, datetime.datetime] = {}

    # ──────────────────────────────────────────────────────────────────
    # Candle fetching
    # ──────────────────────────────────────────────────────────────────

    def _fetch_candles(
        self, instrument_token: Any, tradingsymbol: str
    ) -> Tuple[pd.DataFrame, bool]:
        now = datetime.datetime.now()

        from .config import config_manager
        risk_cfg = config_manager.get_risk_config()
        interval = (
            risk_cfg.get("candleInterval")
            or config_manager.config.get("candleInterval", "5minute")
        )
        if interval not in ("5minute", "15minute"):
            interval = "5minute"

        cache_key = (instrument_token, interval)
        # Use cache if less than 1 minute old
        if (
            cache_key in self.candle_cache
            and (
                now - self.last_cache_time.get(cache_key, datetime.datetime.min)
            ).seconds
            < 60
        ):
            return self.candle_cache[cache_key], True

        # Fetch 7 days for 15minute (~175 bars), 5 days for 5minute (~375 bars)
        days = 7 if interval == "15minute" else 5
        from_date = now - datetime.timedelta(days=days)
        to_date = now

        try:
            records = smart_api_client.get_historical_data(
                instrument_token, from_date, to_date, interval, exchange="NSE"
            )
            if not records:
                return pd.DataFrame(), False

            df = pd.DataFrame(records)
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            if "volume" in df.columns:
                df["volume"] = df["volume"].astype(float)

            self.candle_cache[cache_key] = df
            self.last_cache_time[cache_key] = now
            return df, False
        except Exception as e:
            logger.warning("Error fetching %s candles for %s: %s", interval, tradingsymbol, e)
            return pd.DataFrame(), False

    # ──────────────────────────────────────────────────────────────────
    # Confluence gate
    # ──────────────────────────────────────────────────────────────────

    def _apply_confluence_gate(
        self,
        dir_signals: List[Dict[str, Any]],
        min_confluence: int,
        min_rr: float = 2.0,
        df: Optional[pd.DataFrame] = None,
        min_sl_pct: float = 1.0,
        max_sl_pct: float = 1.8,
        trend_aligned: bool = True,
        regime_enabled: bool = True,
        regime_min_adx: float = 20.0,
        regime_min_ker: float = 0.35,
        regime_block_choppy: bool = True,
        pullback_entry_enabled: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Apply confluence, market regime, 1:2 R:R, and risk quality gates to a group of same-direction signals.

        Returns the highest-confidence signal enriched with confluence and regime metadata
        if the group passes, or None if it fails.
        """
        if not dir_signals:
            return None

        # ── 1. Trend Alignment Gate (against 20/50 EMA) ───────────────────
        direction = dir_signals[0].get("direction", "BUY")
        if trend_aligned and df is not None and len(df) >= 20:
            closes = df["close"]
            ema20 = closes.ewm(span=20, adjust=False).mean().iloc[-1]
            ema50 = (
                closes.ewm(span=50, adjust=False).mean().iloc[-1]
                if len(df) >= 50
                else ema20
            )
            curr_close = closes.iloc[-1]
            # Reject only when price is below BOTH 20 EMA and 50 EMA for longs, or above BOTH for shorts
            if direction == "BUY" and curr_close < ema50 and curr_close < ema20:
                return None  # reject confirmed counter-trend longs
            if direction == "SELL" and curr_close > ema50 and curr_close > ema20:
                return None  # reject confirmed counter-trend shorts


        # ── 2. Adaptive Weighted Confluence Score Gate ────────────────────
        # Each family that fires contributes its empirical weight to the score.
        # Minimum raw family count is still required; weighted score adds quality gate.
        families_seen: Set[str] = set()
        weighted_confluence: float = 0.0
        for sig in dir_signals:
            strat_id = sig.get("_strategy_id", "")
            fam = _get_strategy_family(strat_id)
            if fam not in families_seen:
                families_seen.add(fam)
                weighted_confluence += FAMILY_WEIGHTS.get(fam, 0.8)

        confluence_score = len(families_seen)  # raw family count for gate comparison
        if confluence_score < min_confluence:
            pass  # continue to regime block which sets effective_min_confluence

        # Take the signal with the highest confidence
        best = max(dir_signals, key=lambda s: s.get("confidence", 0))

        # ── 3. Market Regime Filter (suppress false-breakout churn in chop) ──
        regime_meta: Optional[Any] = None
        effective_min_confluence = min_confluence  # default
        if regime_enabled and df is not None and len(df) >= 20:
            regime_result = classify_market_regime(
                df, min_adx=regime_min_adx, min_ker=regime_min_ker
            )
            strat_id = best.get("_strategy_id", "")
            family = _get_strategy_family(strat_id)
            allowed, _ = is_trade_allowed_by_regime(
                regime_result,
                direction,
                family,
                block_choppy_breakouts=regime_block_choppy,
                strict_trend_alignment=trend_aligned,
            )
            if not allowed:
                return None
            regime_meta = regime_result

            if regime_result.regime in ("TRENDING_BULL", "TRENDING_BEAR"):
                from .config import config_manager as _cfg
                trending_min = int(
                    _cfg.get_risk_config().get("minConfluenceScoreTrending", 2)
                )
                effective_min_confluence = min(min_confluence, trending_min)

        # Apply the (possibly regime-adjusted) confluence threshold now
        if confluence_score < effective_min_confluence:
            return None

        # ── 3.5. Dynamic Microstructural Quality Gate ────────────────────
        # Rejects false-breakout traps based on empirical microstructural metrics:
        # RVOL < 1.2x, Rejection Wick > 25%, Local KER < 0.30, or Midday lull without surge.
        from .config import config_manager as _cfg_mgr
        risk_cfg = _cfg_mgr.get_risk_config()
        micro_metrics: Dict[str, Any] = {}
        strat_id = best.get("_strategy_id", "")
        family = _get_strategy_family(strat_id)
        if risk_cfg.get("microstructureFilterEnabled", True) and df is not None and len(df) >= 5:
            from .microstructure import evaluate_microstructure_quality
            min_rvol = float(risk_cfg.get("microstructureMinRvol", 1.2))
            min_ker = float(risk_cfg.get("microstructureMinKer", 0.30))
            max_wick = float(risk_cfg.get("microstructureMaxWick", 0.25))
            midday_boost = 2.2 if risk_cfg.get("microstructureMiddayGuard", True) else min_rvol
            max_gap = float(risk_cfg.get("maxExhaustionGapPct", 1.8))

            passed_micro, micro_reason, micro_metrics = evaluate_microstructure_quality(
                df=df,
                direction=direction,
                min_rvol=min_rvol,
                min_ker=min_ker,
                max_wick_ratio=max_wick,
                midday_rvol_boost=midday_boost,
                max_exhaustion_gap_pct=max_gap,
                strategy_family=family,
            )
            if not passed_micro:
                logger.info(
                    "Signal for %s rejected by Microstructural Quality Gate: %s",
                    best.get("tradingsymbol", "UNKNOWN"),
                    micro_reason,
                )
                return None

        # ── 4. Value Pullback Limit Entry & Volatility-Buffered Stop-Loss ──
        best = dict(best)
        entry_p = float(best.get("entryPrice", best.get("price", 0.0)))
        sl_p = float(best.get("stopLoss", best.get("sl", 0.0)))
        raw_target = float(best.get("target", 0.0))
        indicators = best.get("indicators", {})
        is_structural_target = bool(indicators.get("is_structural_target", False))

        is_pullback = False
        if df is not None and len(df) >= 5:
            from .strategy_engine import (
                calculate_pullback_limit_entry,
                calculate_volatility_buffered_sl,
            )

            # Optional Pullback Limit Entry (EMA20/VWAP/POC retest vs Direct Breakout Entry)
            if pullback_entry_enabled:
                pullback_entry = calculate_pullback_limit_entry(
                    df=df, direction=direction, breakout_level=entry_p
                )
                if pullback_entry > 0:
                    entry_p = pullback_entry
                    best["entryPrice"] = entry_p
                    is_pullback = True
            else:
                best["entryPrice"] = entry_p

            # Task 1: Add 0.5x ATR volatility buffer to structural stop losses
            buffered_sl = calculate_volatility_buffered_sl(
                df=df, direction=direction, raw_sl=sl_p, lookback=10, atr_multiplier=0.5
            )
            if buffered_sl > 0:
                sl_p = buffered_sl

        best["isPullbackEntry"] = is_pullback

        if entry_p > 0 and sl_p > 0:
            raw_risk = abs(entry_p - sl_p)
            current_sl_pct = (raw_risk / entry_p) * 100.0

            # Widen tight SL to minimum safe buffer (e.g. 1.0%) and cap wide SL (e.g. 1.8% max)
            if min_sl_pct > 0 and current_sl_pct < min_sl_pct:
                safe_risk = entry_p * (min_sl_pct / 100.0)
            elif max_sl_pct > 0 and current_sl_pct > max_sl_pct:
                safe_risk = entry_p * (max_sl_pct / 100.0)
            else:
                safe_risk = raw_risk

            if is_structural_target and raw_target > 0:
                # Structural Target (Mean Reversion strictly to POC, Pivot, or Fair Value):
                # Never overwrite with a synthetic trend target!
                structural_reward = abs(raw_target - entry_p)
                structural_rr = (structural_reward / safe_risk) if safe_risk > 0 else 0.0

                if structural_rr < 1.3:
                    logger.info(
                        "Signal for %s rejected: Insufficient structural RR (%.2f < 1.3)",
                        best.get("tradingsymbol", "UNKNOWN"),
                        structural_rr,
                    )
                    return None

                best["stopLoss"] = (
                    round(entry_p - safe_risk, 2)
                    if direction == "BUY"
                    else round(entry_p + safe_risk, 2)
                )
                best["target"] = round(raw_target, 2)
                best["riskReward"] = round(structural_rr, 2)
            else:
                # Directional / Breakout / Trend Continuation:
                # Enforce realistic intraday target expansion (eliminates impossible 8% targets)
                # 1. Cap target distance from entry: max 3.2% (or 1.8x ATR)
                atr_val = float(indicators.get("atr", 0.0))
                max_target_pct = float(risk_cfg.get("maxIntradayTargetPercent", 3.2))
                max_target_dist = entry_p * (max_target_pct / 100.0)
                if atr_val > 0:
                    max_target_dist = min(max_target_dist, 1.8 * atr_val)

                # 2. Cap total day expansion from day open: max 4.5% total move
                max_day_expansion_pct = float(risk_cfg.get("maxDayExpansionPercent", 4.5))
                today_open = float(micro_metrics.get("today_open", 0.0)) if micro_metrics else 0.0
                if today_open <= 0 and df is not None and len(df) > 0:
                    today_open = float(df["open"].iloc[0])

                target_dist = safe_risk * 2.0  # Exact 1:2 R:R geometry baseline

                if max_target_dist > 0:
                    target_dist = min(target_dist, max_target_dist)

                if today_open > 0 and max_day_expansion_pct > 0:
                    if direction == "BUY":
                        max_day_target = today_open * (1.0 + max_day_expansion_pct / 100.0)
                        if entry_p + target_dist > max_day_target:
                            target_dist = max(0.0, max_day_target - entry_p)
                    else:
                        min_day_target = today_open * (1.0 - max_day_expansion_pct / 100.0)
                        if entry_p - target_dist < min_day_target:
                            target_dist = max(0.0, entry_p - min_day_target)

                # Check if remaining intraday runway supports at least min_rr
                effective_rr = (target_dist / safe_risk) if safe_risk > 0 else 0.0
                if effective_rr < min_rr:
                    logger.info(
                        "Signal for %s rejected by Intraday Expansion Guard: Realistic target yields RR=%.2f < %.2f (day runway exhausted)",
                        best.get("tradingsymbol", "UNKNOWN"),
                        effective_rr,
                        min_rr,
                    )
                    return None

                if direction == "BUY":
                    best["stopLoss"] = round(entry_p - safe_risk, 2)
                    best["target"] = round(entry_p + target_dist, 2)
                else:
                    best["stopLoss"] = round(entry_p + safe_risk, 2)
                    best["target"] = round(entry_p - target_dist, 2)

                best["riskReward"] = round(effective_rr, 2)

            best["stopLossPercent"] = round((safe_risk / entry_p) * 100.0, 2)
            best["targetPercent"] = round(
                (abs(best["target"] - entry_p) / entry_p) * 100.0, 2
            )

        # Enrich the chosen signal with confluence and regime metadata
        best["confluenceScore"] = confluence_score
        best["weightedConfluenceScore"] = round(weighted_confluence, 2)
        best["familiesVoting"] = sorted(families_seen)
        best["strategyCount"] = len(dir_signals)
        best["allStrategies"] = [
            s.get("strategy", s.get("_strategy_id", "")) for s in dir_signals
        ]

        # Multi-strategy confluence calibration: reflect true combination rather than single default
        unique_strat_names = list(dict.fromkeys(
            s.get("strategy", s.get("_strategy_id", "")) for s in dir_signals if s.get("strategy")
        ))
        if len(unique_strat_names) >= 2:
            other_names = [n for n in unique_strat_names if n != best.get("strategy")]
            if other_names:
                best["compositeStrategy"] = f"{best.get('strategy')} + {', '.join(other_names)}"
                # Multi-family confidence boost (+2% per additional independent family)
                best["confidence"] = min(92, best.get("confidence", 80) + (confluence_score - 1) * 2)
        if regime_meta is not None:
            best["marketRegime"] = regime_meta.regime
            best["adx"] = regime_meta.adx
            best["ker"] = regime_meta.ker

        if micro_metrics:
            best["rvol"] = micro_metrics.get("rvol", 1.0)
            best["wickRatio"] = micro_metrics.get("wick_ratio", 0.0)
            best["localKer"] = micro_metrics.get("local_ker", 0.5)

        active_interval = (
            risk_cfg.get("candleInterval")
            or _cfg_mgr.config.get("candleInterval", "5minute")
        )
        best["candleInterval"] = active_interval
        best["timeframe"] = "15m" if active_interval == "15minute" else "5m"

        best.pop("_strategy_id", None)
        return best

    # ──────────────────────────────────────────────────────────────────
    # Main watchlist scan
    # ──────────────────────────────────────────────────────────────────

    def scan_watchlist(
        self, symbols: List[str], on_signal=None
    ) -> List[Dict[str, Any]]:

        all_signals: List[Dict[str, Any]] = []
        strategy_config = config_manager.get_strategy_config()
        risk_config = config_manager.get_risk_config()
        min_confluence = int(risk_config.get("minConfluenceScore", 3))
        min_rr = float(risk_config.get("minRiskReward", 2.0))
        no_entry_mins = int(risk_config.get("noEntryFirstMins", 15))
        min_sl_pct = float(risk_config.get("minStopLossPercent", 1.0))
        max_sl_pct = float(risk_config.get("maxStopLossPercent", 1.8))
        trend_aligned = bool(risk_config.get("trendAlignmentFilter", True))
        regime_enabled = bool(risk_config.get("marketRegimeFilterEnabled", True))
        regime_min_adx = float(risk_config.get("marketRegimeMinADX", 20.0))
        regime_min_ker = float(risk_config.get("marketRegimeMinKER", 0.35))
        regime_block_choppy = bool(
            risk_config.get("marketRegimeBlockChoppyBreakouts", True)
        )
        pullback_entry_enabled = bool(
            risk_config.get("pullbackEntryEnabled", False)
        )

        def process_symbol(symbol: str) -> List[Dict[str, Any]]:
            # ── Market hours gate (first N minutes) ───────────────────
            if _is_market_open_phase(no_entry_mins):
                return []

            # ── Time-window gate (high-probability entry windows only) ─
            if not _is_entry_window(no_entry_mins):
                return []

            token = smart_api_client.resolve_token(symbol)
            if not token:
                return []

            df, was_cached = self._fetch_candles(token, symbol)
            if not was_cached:
                time.sleep(0.35)
            if df.empty:
                return []

            # ── 15:15 Intraday Cutoff Gate ────────────────────────────
            # Do not generate intraday entry signals from candles at or after 3:15 PM IST
            if "date" in df.columns and len(df) > 0:
                try:
                    last_ts_str = str(df["date"].iloc[-1])
                    if len(last_ts_str) >= 16:
                        last_time_str = last_ts_str[11:16]
                        if last_time_str >= "15:15":
                            return []
                except Exception:
                    pass

            # ── Regime detection & KER push for midday gate ──────────────
            from .strategies.utils import compute_regime
            from .market_regime import calculate_ker as _calc_ker
            from .risk_manager import risk_manager as _risk_mgr

            regime = compute_regime(df)

            # Push symbol-level KER to risk_manager so that can_trade()'s midday
            # chop gate becomes regime-aware (only blocks when KER < 0.30)
            if len(df) >= 21:
                sym_ker = _calc_ker(df["close"], period=20)
                _risk_mgr.set_market_ker(sym_ker)
            else:
                _risk_mgr.set_market_ker(0.0)  # unknown → safe block

            # ── Run all enabled strategies ─────────────────────────────
            buy_signals: List[Dict[str, Any]] = []
            sell_signals: List[Dict[str, Any]] = []

            for strat_id, strategy in self.strategies.items():
                cfg = strategy_config.get(strat_id, {})
                if not cfg.get("enabled", False):
                    continue
                # In choppy regime (ADX < 18), skip pure trend-following strategies
                # but allow breakout, oscillator, structure, and reversal setups to fire
                if regime == "volatile" and _get_strategy_family(strat_id) == "trend":
                    continue
                try:
                    strat_signals = strategy.calculate_signals(df, symbol)
                    for sig in strat_signals:
                        sig = dict(sig)
                        sig["_strategy_id"] = strat_id
                        if sig.get("direction") == "BUY":
                            buy_signals.append(sig)
                        elif sig.get("direction") == "SELL":
                            sell_signals.append(sig)
                except Exception:
                    pass

            # Respect SmartAPI rate limits (max 3 historical requests/second)
            if not was_cached:
                time.sleep(1.0)

            # ── Confluence & Quality gate ──────────────────────────────
            validated: List[Dict[str, Any]] = []
            for dir_signals in (buy_signals, sell_signals):
                if not dir_signals:
                    continue
                validated_sig = self._apply_confluence_gate(
                    dir_signals,
                    min_confluence,
                    min_rr,
                    df=df,
                    min_sl_pct=min_sl_pct,
                    max_sl_pct=max_sl_pct,
                    trend_aligned=trend_aligned,
                    regime_enabled=regime_enabled,
                    regime_min_adx=regime_min_adx,
                    regime_min_ker=regime_min_ker,
                    regime_block_choppy=regime_block_choppy,
                    pullback_entry_enabled=pullback_entry_enabled,
                )
                if validated_sig is not None:
                    validated.append(validated_sig)

            return validated

        for symbol in symbols:
            try:
                signals = process_symbol(symbol)
                if signals:
                    if on_signal:
                        for sig in signals:
                            on_signal(sig)
                    all_signals.extend(signals)
            except Exception as e:
                import sys

                print(f"Error processing {symbol}: {e}", file=sys.stderr)

        all_signals.sort(
            key=lambda x: (
                x.get("weightedConfluenceScore", x.get("confluenceScore", 0)) * 100
                + x.get("confidence", 0)
            ),
            reverse=True,
        )
        return all_signals

    # ──────────────────────────────────────────────────────────────────
    # Position re-evaluation (no confluence gate — used for monitoring)
    # ──────────────────────────────────────────────────────────────────

    def evaluate_position(
        self, tradingsymbol: str, instrument_token: Any
    ) -> Dict[str, Any]:
        """
        Re-evaluate a single symbol against all enabled strategies.
        Returns a directional summary for thesis-invalidation checks.
        Confluence gate is NOT applied here; this is for monitoring, not entry.
        """
        strategy_config = config_manager.get_strategy_config()

        df, _ = self._fetch_candles(instrument_token, tradingsymbol)
        if df.empty:
            return {"buy_signals": 0, "sell_signals": 0, "strategies": []}

        buy_signals = 0
        sell_signals = 0
        triggered_strategies = []

        for strat_id, strategy in self.strategies.items():
            cfg = strategy_config.get(strat_id, {})
            if not cfg.get("enabled", False):
                continue

            try:
                signals = strategy.calculate_signals(df, tradingsymbol)
                for sig in signals:
                    if sig.get("direction") == "BUY":
                        buy_signals += 1
                        triggered_strategies.append(
                            {
                                "strategy": strat_id,
                                "direction": "BUY",
                                "confidence": sig.get("confidence", 0),
                            }
                        )
                    elif sig.get("direction") == "SELL":
                        sell_signals += 1
                        triggered_strategies.append(
                            {
                                "strategy": strat_id,
                                "direction": "SELL",
                                "confidence": sig.get("confidence", 0),
                            }
                        )
            except Exception:
                pass

        return {
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "strategies": triggered_strategies,
        }


scanner = Scanner()
