"""
Backtest Engine — walk-forward simulation of all 21 strategies.

How it works
------------
For each symbol and each bar index `i` (starting after `min_bars`):
  1. Slice the DataFrame to df[:i] (simulating "we only know the past").
  2. Run all enabled strategies through the confluence gate.
  3. If a signal fires:
     - Entry price = next bar's open (df[i+1].open) — realistic fill assumption.
     - Initial SL and target from the signal.
     - ATR trailing SL: on each subsequent bar, ratchet the SL.
     - Exit when: SL hit, target hit, square-off time reached, or end of data.
  4. Record the trade with all metadata.

Key assumptions / simplifications
-----------------------------------
- No slippage beyond the next-bar open.  Real slippage will be worse on 5-min.
- One position per symbol at a time (no pyramiding).
- Square-off time: 15:00 on the same day (IST) for intraday, end-of-data for daily.
- Position size: constant ₹10,000 per trade for P&L calculation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from ..market_regime import classify_market_regime, is_trade_allowed_by_regime
from ..scanner import _get_strategy_family

# ── Import strategies and scanner logic ─────────────────────────────────────
from ..strategies.adx_momentum import ADXMomentumStrategy
from ..strategies.awesome_oscillator import AwesomeOscillatorStrategy
from ..strategies.bollinger_breakout import BollingerBreakoutStrategy
from ..strategies.cci_reversal import CCIReversalStrategy
from ..strategies.cmf_accumulation import CMFAccumulationStrategy
from ..strategies.donchian_breakout import DonchianBreakoutStrategy
from ..strategies.ema_crossover import EMACrossoverStrategy
from ..strategies.institutional_absorption import InstitutionalAbsorptionStrategy
from ..strategies.keltner_breakout import KeltnerBreakoutStrategy
from ..strategies.macd_cross import MACDCrossStrategy
from ..strategies.mfi_exhaustion import MFIExhaustionStrategy
from ..strategies.cpr_breakout_reversal import CPRBreakoutReversalStrategy
from ..strategies.fixed_range_volume_profile import (
    FixedRangeVolumeProfileStrategy,
)
from ..strategies.gap_fill import GapFillStrategy
from ..strategies.liquidity_grab_reversal import LiquidityGrabReversalStrategy
from ..strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from ..strategies.order_block_fvg import OrderBlockFVGStrategy
from ..strategies.psar_trend import PSARTrendStrategy
from ..strategies.rsi_reversal import RSIReversalStrategy
from ..strategies.stoc_rsi import StochRSIStrategy
from ..strategies.stochastic_reversal import StochasticReversalStrategy
from ..strategies.supertrend import SupertrendStrategy
from ..strategies.tsi_cross import TSICrossStrategy
from ..strategies.utils import compute_atr
from ..strategies.volume_delta_divergence import VolumeDeltaDivergenceStrategy
from ..strategies.vwap_bounce import VWAPBounceStrategy
from ..strategies.williams_r import WilliamsRStrategy

# ── Strategy registry ────────────────────────────────────────────────────────

ALL_STRATEGIES: Dict[str, Any] = {
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
    "cpr_breakout_reversal": CPRBreakoutReversalStrategy(),
    "opening_range_breakout": OpeningRangeBreakoutStrategy(),
    "liquidity_grab_reversal": LiquidityGrabReversalStrategy(),
    "gap_fill": GapFillStrategy(),
    "fixed_range_volume_profile": FixedRangeVolumeProfileStrategy(),
}

# ── Statutory Indian Market Friction Calculator ──────────────────────────────


def compute_statutory_friction(
    entry_price: float, exit_price: float, qty: int
) -> float:
    """Compute round-trip friction for NSE Cash Intraday MIS trade."""
    buy_turnover = round(entry_price * qty, 2)
    sell_turnover = round(exit_price * qty, 2)
    total_turnover = round(buy_turnover + sell_turnover, 2)

    # Angel One Intraday: Lower of ₹20 or 0.1% per executed order (min ₹5)
    buy_brokerage = max(5.0, min(20.0, round(buy_turnover * 0.001, 2)))
    sell_brokerage = max(5.0, min(20.0, round(sell_turnover * 0.001, 2)))
    brokerage = round(buy_brokerage + sell_brokerage, 2)

    stt = round(sell_turnover * 0.00025, 2)  # 0.025% on sell
    exchange_fee = round(total_turnover * 0.0000297, 2)  # 0.00297% (SEBI True-to-Label NSE Cash Intraday)
    sebi_charge = round(total_turnover * 0.000001, 2)  # ₹10 / crore
    stamp_duty = round(buy_turnover * 0.00003, 2)  # 0.003% on buy
    gst = round((brokerage + exchange_fee + sebi_charge) * 0.18, 2)
    return round(brokerage + stt + exchange_fee + sebi_charge + stamp_duty + gst, 2)


# ── Trade data class ─────────────────────────────────────────────────────────


@dataclass
class BacktestTrade:
    symbol: str
    direction: str  # 'BUY' or 'SELL'
    entry_bar: int
    entry_price: float
    initial_sl: float
    final_sl: float  # may differ if trailing SL kicked in
    target: float
    target1: float = 0.0
    target2: float = 0.0
    partial_booked: bool = False
    partial_exit_price: float = 0.0
    partial_pnl_rs: float = 0.0
    exit_price: float = 0.0
    exit_reason: str = "EOD"  # 'TARGET', 'SL', 'BREAKEVEN_SL', 'TRAILING_SL', 'SQUAREOFF', 'EOD'
    bars_held: int = 0
    pnl_pct: float = 0.0  # % return on position
    pnl_rs: float = 0.0  # Gross ₹ P&L
    friction_rs: float = 0.0  # Indian statutory friction (brokerage, STT, turnover, GST)
    net_pnl_rs: float = 0.0  # Realized net ₹ P&L after friction
    entry_time: str = ""  # ISO timestamp of entry
    rr_achieved: float = 0.0  # actual R:R achieved
    confluence_score: int = 0
    families_voting: List[str] = field(default_factory=list)
    strategies_voting: List[str] = field(default_factory=list)
    confidence: int = 0


# ── Confluence gate (mirrors scanner.py logic, offline) ─────────────────────


def _apply_confluence(
    signals: List[Dict],
    direction: str,
    min_confluence: int = 3,
    min_confluence_trending: int = 3,  # raised to 3 across all regimes
    min_rr: float = 2.0,
    df: Optional[pd.DataFrame] = None,
    trend_aligned: bool = True,
    min_sl_pct: float = 1.0,
    max_sl_pct: float = 1.8,
    regime_enabled: bool = True,
    regime_min_adx: float = 20.0,
    regime_min_ker: float = 0.35,
    regime_block_choppy: bool = True,
) -> Optional[Dict]:
    dir_signals = [s for s in signals if s.get("direction") == direction]
    if not dir_signals:
        return None

    # Trend alignment gate (against 50 EMA)
    if trend_aligned and df is not None and len(df) >= 50:
        closes = df["close"]
        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
        curr_close = closes.iloc[-1]
        if direction == "BUY" and curr_close < ema50:
            return None  # avoid counter-trend buy
        if direction == "SELL" and curr_close > ema50:
            return None  # avoid counter-trend sell

    families_seen: set = set()
    for sig in dir_signals:
        strat_id = sig.get("_strat_id", "")
        families_seen.add(_get_strategy_family(strat_id))

    family_count = len(families_seen)
    if family_count < min(min_confluence, min_confluence_trending):
        return None

    best = max(dir_signals, key=lambda s: s.get("confidence", 0))

    # Market Regime Filter: suppress false breakout churn during chop
    regime_meta = None
    effective_min_confluence = min_confluence  # default (all regimes)
    if regime_enabled and df is not None and len(df) >= 20:
        regime_result = classify_market_regime(
            df, min_adx=regime_min_adx, min_ker=regime_min_ker
        )
        strat_id = best.get("_strat_id", "")
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
            effective_min_confluence = min(min_confluence, min_confluence_trending)

    # Apply the confluence threshold
    if family_count < effective_min_confluence:
        return None

    best = dict(best)
    entry_p = float(best.get("entryPrice", best.get("price", 0.0)))
    sl_p = float(best.get("stopLoss", best.get("sl", 0.0)))
    raw_target = float(best.get("target", 0.0))

    if df is not None and len(df) >= 5:
        from ..strategy_engine import (
            calculate_pullback_limit_entry,
            calculate_volatility_buffered_sl,
        )

        pullback_entry = calculate_pullback_limit_entry(
            df=df, direction=direction, breakout_level=entry_p
        )
        if pullback_entry > 0:
            entry_p = pullback_entry
            best["entryPrice"] = entry_p

        buffered_sl = calculate_volatility_buffered_sl(
            df=df, direction=direction, raw_sl=sl_p, lookback=10, atr_multiplier=0.85
        )
        if buffered_sl > 0:
            sl_p = buffered_sl

    # Safe minimum & maximum stop-loss buffer & 1:2 R:R geometry
    if entry_p > 0 and sl_p > 0:
        raw_risk = abs(entry_p - sl_p)
        current_sl_pct = (raw_risk / entry_p) * 100.0
        if min_sl_pct > 0 and current_sl_pct < min_sl_pct:
            safe_risk = entry_p * (min_sl_pct / 100.0)
        elif max_sl_pct > 0 and current_sl_pct > max_sl_pct:
            safe_risk = entry_p * (max_sl_pct / 100.0)
        else:
            safe_risk = raw_risk

        raw_reward = abs(raw_target - entry_p) if raw_target > 0 else 0.0
        raw_rr = (raw_reward / safe_risk) if safe_risk > 0 else 0.0
        target_multiplier = max(min_rr, 2.0, raw_rr)

        if direction == "BUY":
            best["stopLoss"] = round(entry_p - safe_risk, 2)
            best["target"] = round(entry_p + safe_risk * target_multiplier, 2)
        else:
            best["stopLoss"] = round(entry_p + safe_risk, 2)
            best["target"] = round(entry_p - safe_risk * target_multiplier, 2)

        best["riskReward"] = round(target_multiplier, 2)

    best["confluenceScore"] = len(families_seen)
    best["familiesVoting"] = sorted(families_seen)
    best["strategyNames"] = [
        s.get("strategy", s.get("_strat_id", "")) for s in dir_signals
    ]
    if regime_meta is not None:
        best["marketRegime"] = regime_meta.regime
    return best


# ── Backtest engine ──────────────────────────────────────────────────────────


class BacktestEngine:
    def __init__(
        self,
        min_confluence: int = 3,
        min_confluence_trending: int = 3,
        min_rr: float = 2.0,
        capital_per_trade: float = 20_000.0,
        trailing_sl_multiplier: float = 2.2,
        min_bars: int = 60,
        trail_after_r: float = 1.0,
        trend_aligned: bool = True,
        min_sl_pct: float = 1.2,
        max_sl_pct: float = 2.4,
        max_trades_per_day: int = 4,
        enforce_friction_guard: bool = True,
        friction_multiple: float = 3.5,
        disabled_strategies: Optional[Set[str]] = None,
        regime_enabled: bool = True,
        regime_min_adx: float = 20.0,
        regime_min_ker: float = 0.35,
        regime_block_choppy: bool = True,
        partial_booking_enabled: bool = True,
        partial_target_rr: float = 1.0,
        partial_booking_ratio: float = 0.5,
    ):
        self.min_confluence = min_confluence
        self.min_confluence_trending = min_confluence_trending
        self.min_rr = min_rr
        self.capital = capital_per_trade
        self.tsl_mult = trailing_sl_multiplier
        self.min_bars = min_bars
        self.trail_after_r = trail_after_r
        self.trend_aligned = trend_aligned
        self.min_sl_pct = min_sl_pct
        self.max_sl_pct = max_sl_pct
        self.max_trades_per_day = max_trades_per_day
        self.enforce_friction_guard = enforce_friction_guard
        self.friction_multiple = friction_multiple
        self.regime_enabled = regime_enabled
        self.regime_min_adx = regime_min_adx
        self.regime_min_ker = regime_min_ker
        self.regime_block_choppy = regime_block_choppy
        self.partial_booking_enabled = partial_booking_enabled
        self.partial_target_rr = partial_target_rr
        self.partial_booking_ratio = partial_booking_ratio

        if disabled_strategies is not None:
            self.disabled_strats = set(disabled_strategies)
        else:
            try:
                from ..config import config_manager

                strat_cfg = config_manager.get_strategy_config()
                self.disabled_strats = {
                    s_id
                    for s_id, cfg in strat_cfg.items()
                    if not cfg.get("enabled", True)
                }
            except Exception:
                self.disabled_strats = {
                    "williams_r",
                    "cci_reversal",
                    "adx_momentum",
                    "rsi_reversal",
                    "vwap_bounce",
                    "mfi_exhaustion",
                    "stochastic_reversal",
                    "supertrend",
                    "psar_trend",
                    "macd_cross",
                    "ema_crossover",
                    "awesome_oscillator",
                    "stoc_rsi",
                    "institutional_absorption",
                    "cpr_breakout_reversal",
                    "order_block_fvg",
                    "opening_range_breakout",
                }

    def _run_strategies(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Run all strategies on df and return tagged signal list."""
        signals = []
        for strat_id, strat in ALL_STRATEGIES.items():
            if self.disabled_strats and strat_id in self.disabled_strats:
                continue
            try:
                strat_signals = strat.calculate_signals(df.copy(), symbol)
                for sig in strat_signals:
                    sig = dict(sig)
                    sig["_strat_id"] = strat_id
                    signals.append(sig)
            except Exception:
                pass
        return signals

    def _update_trailing_sl(
        self,
        trade_sl: float,
        hwm: float,
        lwm: float,
        ltp: float,
        direction: str,
        atr: float,
        entry_price: float,
        trade_risk: float,
    ):
        """Return (new_sl, new_hwm, new_lwm). Ratchets favorably once profit threshold is reached."""
        distance = atr * self.tsl_mult
        threshold = trade_risk * self.trail_after_r if self.trail_after_r > 0 else 0.0

        if direction == "BUY":
            hwm = max(hwm, ltp)
            # Only activate trailing SL once trade advances at least threshold into profit
            if (hwm - entry_price) >= threshold:
                new_sl = round(max(trade_sl, entry_price, hwm - distance), 2)
                if new_sl > trade_sl:
                    return new_sl, hwm, lwm
        else:
            lwm = min(lwm, ltp)
            # Only activate trailing SL once trade drops at least threshold into profit
            if (entry_price - lwm) >= threshold:
                new_sl = round(min(trade_sl, entry_price, lwm + distance), 2)
                if new_sl < trade_sl:
                    return new_sl, hwm, lwm

        return trade_sl, hwm, lwm

    def run_symbol(self, df: pd.DataFrame, symbol: str) -> List[BacktestTrade]:
        """Run walk-forward backtest for a single symbol."""
        trades: List[BacktestTrade] = []
        in_trade = False
        n = len(df)

        if n < self.min_bars + 2:
            return trades

        # Walk forward bar by bar
        i = self.min_bars
        while i < n - 1:
            if in_trade:
                i += 1
                continue  # position management handled inside trade loop below

            # Run strategies on recent rolling window up to bar i (150 bars is optimal for 50-EMA and TA indicators)
            window = df.iloc[max(0, i - 150) : i].copy()
            raw_signals = self._run_strategies(window, symbol)

            # Try BUY then SELL confluence gate
            chosen = None
            for direction in ("BUY", "SELL"):
                chosen = _apply_confluence(
                    raw_signals,
                    direction,
                    min_confluence=self.min_confluence,
                    min_confluence_trending=self.min_confluence_trending,
                    min_rr=self.min_rr,
                    df=window,
                    trend_aligned=self.trend_aligned,
                    min_sl_pct=self.min_sl_pct,
                    max_sl_pct=self.max_sl_pct,
                    regime_enabled=self.regime_enabled,
                    regime_min_adx=self.regime_min_adx,
                    regime_min_ker=self.regime_min_ker,
                    regime_block_choppy=self.regime_block_choppy,
                )
                if chosen:
                    break

            if not chosen:
                i += 1
                continue

            # Entry execution (simulating pullback limit fill)
            entry_bar = i
            next_bar = df.iloc[i + 1]
            next_open = float(next_bar["open"])
            next_low = float(next_bar["low"])
            next_high = float(next_bar["high"])
            direction = chosen["direction"]
            signal_entry = float(chosen.get("entryPrice", next_open))

            if signal_entry > 0:
                if direction == "BUY":
                    entry_price = signal_entry if next_low <= signal_entry else next_open
                else:
                    entry_price = signal_entry if next_high >= signal_entry else next_open
            else:
                entry_price = next_open

            initial_sl = float(chosen.get("stopLoss", chosen.get("sl", 0)))
            target = float(chosen.get("target", 0))
            atr = float(chosen.get("indicators", {}).get("atr", 0)) or compute_atr(
                window
            )

            if initial_sl <= 0 or target <= 0:
                i += 1
                continue

            # Adjust SL/target from signal price to actual entry
            if (
                signal_entry > 0
                and abs(signal_entry - entry_price) / signal_entry < 0.02
            ):
                # Small gap — keep signal levels
                pass
            else:
                # Re-anchor to actual entry
                risk = abs(signal_entry - initial_sl)
                if direction == "BUY":
                    initial_sl = round(entry_price - risk, 2)
                    target = round(entry_price + risk * 2.0, 2)
                else:
                    initial_sl = round(entry_price + risk, 2)
                    target = round(entry_price - risk * 2.0, 2)

            trade_risk = abs(entry_price - initial_sl)
            qty = max(1, int(self.capital / entry_price))

            # Compute Target 1 (+1.0R) and Target 2 (+2.0R)
            if direction == "BUY":
                target1 = round(entry_price + (trade_risk * self.partial_target_rr), 2)
                target2 = round(entry_price + (trade_risk * max(self.min_rr, 2.0)), 2)
            else:
                target1 = round(entry_price - (trade_risk * self.partial_target_rr), 2)
                target2 = round(entry_price - (trade_risk * max(self.min_rr, 2.0)), 2)

            # Pre-trade Friction Guard Check (reject if payoff < 3.5x friction)
            if self.enforce_friction_guard:
                est_friction = compute_statutory_friction(entry_price, target2, qty)
                expected_gain = abs(target2 - entry_price) * qty
                if expected_gain < (self.friction_multiple * est_friction):
                    i += 1
                    continue

            # Manage trade bar-by-bar with Partial Booking (+1.2R) & Breakeven SL
            trade_sl = initial_sl
            hwm = entry_price
            lwm = entry_price
            exit_price = entry_price
            exit_reason = "EOD"
            in_trade = True

            partial_booked = False
            partial_exit_price = 0.0
            partial_pnl_rs = 0.0
            leg1_qty = (
                int(qty * self.partial_booking_ratio)
                if self.partial_booking_enabled and qty >= 2
                else 0
            )
            leg2_qty = qty - leg1_qty

            j = i + 2  # first management bar

            while j < n:
                bar = df.iloc[j]
                lo = float(bar["low"])
                hi = float(bar["high"])
                close = float(bar["close"])

                # Update ATR periodically (every 10 bars) for trailing SL
                if (j - i) % 10 == 0:
                    atr = compute_atr(df.iloc[:j]) or atr

                # ── Check Target 1 (+1.2R) for Partial Booking ───────
                if (
                    self.partial_booking_enabled
                    and not partial_booked
                    and leg1_qty > 0
                ):
                    if direction == "BUY" and hi >= target1:
                        partial_booked = True
                        partial_exit_price = target1
                        partial_pnl_rs = (target1 - entry_price) * leg1_qty
                        trade_sl = max(trade_sl, entry_price)  # Move SL to Breakeven
                    elif direction == "SELL" and lo <= target1:
                        partial_booked = True
                        partial_exit_price = target1
                        partial_pnl_rs = (entry_price - target1) * leg1_qty
                        trade_sl = min(trade_sl, entry_price)  # Move SL to Breakeven

                # ── Check Exit Conditions for Remaining Runner ────────
                if direction == "BUY":
                    if hi >= target2:
                        exit_price = target2
                        exit_reason = "TARGET"
                        break
                    if lo <= trade_sl:
                        exit_price = trade_sl
                        if partial_booked and trade_sl >= entry_price:
                            exit_reason = "BREAKEVEN_SL"
                        elif trade_sl > initial_sl:
                            exit_reason = "TRAILING_SL"
                        else:
                            exit_reason = "SL"
                        break
                else:
                    if lo <= target2:
                        exit_price = target2
                        exit_reason = "TARGET"
                        break
                    if hi >= trade_sl:
                        exit_price = trade_sl
                        if partial_booked and trade_sl <= entry_price:
                            exit_reason = "BREAKEVEN_SL"
                        elif trade_sl < initial_sl:
                            exit_reason = "TRAILING_SL"
                        else:
                            exit_reason = "SL"
                        break

                # Ratchet trailing SL with profit cushion
                trade_sl, hwm, lwm = self._update_trailing_sl(
                    trade_sl,
                    hwm,
                    lwm,
                    close,
                    direction,
                    atr,
                    entry_price,
                    trade_risk,
                )

                j += 1

            if exit_reason == "EOD":
                exit_price = float(df.iloc[-1]["close"])

            # ── Calculate Combined P&L and Statutory Friction ────────
            if partial_booked and leg1_qty > 0:
                leg2_pnl_rs = (
                    (exit_price - entry_price) * leg2_qty
                    if direction == "BUY"
                    else (entry_price - exit_price) * leg2_qty
                )
                pnl_rs = round(partial_pnl_rs + leg2_pnl_rs, 2)
                fric_leg1 = compute_statutory_friction(
                    entry_price, partial_exit_price, leg1_qty
                )
                fric_leg2 = compute_statutory_friction(
                    entry_price, exit_price, leg2_qty
                )
                friction_rs = round(fric_leg1 + fric_leg2, 2)
                net_pnl_rs = round(pnl_rs - friction_rs, 2)
                pnl_pct = round((pnl_rs / (qty * entry_price)) * 100, 2)
            else:
                pnl_rs = round(
                    (
                        (exit_price - entry_price)
                        if direction == "BUY"
                        else (entry_price - exit_price)
                    )
                    * qty,
                    2,
                )
                friction_rs = compute_statutory_friction(entry_price, exit_price, qty)
                net_pnl_rs = round(pnl_rs - friction_rs, 2)
                pnl_pct = round((pnl_rs / (qty * entry_price)) * 100, 2)

            risk_per_unit = abs(entry_price - initial_sl)
            reward_per_unit = abs(exit_price - entry_price)
            rr_achieved = (
                round(reward_per_unit / risk_per_unit, 2) if risk_per_unit > 0 else 0.0
            )

            entry_dt = ""
            if "datetime" in df.columns:
                entry_dt = str(df.iloc[entry_bar + 1]["datetime"])
            elif isinstance(df.index, pd.DatetimeIndex):
                entry_dt = str(df.index[entry_bar + 1])
            else:
                entry_dt = f"Bar_{entry_bar + 1:04d}"

            trades.append(
                BacktestTrade(
                    symbol=symbol,
                    direction=direction,
                    entry_bar=entry_bar,
                    entry_price=round(entry_price, 2),
                    initial_sl=round(initial_sl, 2),
                    final_sl=round(trade_sl, 2),
                    target=round(target, 2),
                    target1=round(target1, 2),
                    target2=round(target2, 2),
                    partial_booked=partial_booked,
                    partial_exit_price=round(partial_exit_price, 2),
                    partial_pnl_rs=round(partial_pnl_rs, 2),
                    exit_price=round(exit_price, 2),
                    exit_reason=exit_reason,
                    bars_held=j - (i + 1),
                    pnl_pct=pnl_pct,
                    pnl_rs=pnl_rs,
                    friction_rs=friction_rs,
                    net_pnl_rs=net_pnl_rs,
                    entry_time=entry_dt,
                    rr_achieved=rr_achieved,
                    confluence_score=chosen.get("confluenceScore", 0),
                    families_voting=chosen.get("familiesVoting", []),
                    strategies_voting=chosen.get("strategyNames", []),
                    confidence=chosen.get("confidence", 0),
                )
            )

            in_trade = False
            i = j + 1  # resume scan after the trade ends

        return trades

    def run(self, symbol_dfs: Dict[str, pd.DataFrame]) -> List[BacktestTrade]:
        """Run backtest across all symbols. Returns all trades."""
        all_trades: List[BacktestTrade] = []
        total = len(symbol_dfs)
        for idx, (symbol, df) in enumerate(symbol_dfs.items(), 1):
            print(
                f"  [{idx}/{total}] Backtesting {symbol} ({len(df)} bars)...",
                end=" ",
                flush=True,
            )
            if df.empty or len(df) < self.min_bars + 2:
                print("skipped (insufficient data)")
                continue
            trades = self.run_symbol(df, symbol)
            print(f"{len(trades)} trade(s)")
            all_trades.extend(trades)

        # Enforce max trades per day across portfolio
        if self.max_trades_per_day > 0 and all_trades:
            all_trades.sort(key=lambda t: t.entry_time)
            filtered_trades: List[BacktestTrade] = []
            daily_counts: Dict[str, int] = defaultdict(int)
            for t in all_trades:
                day_key = t.entry_time[:10] if len(t.entry_time) >= 10 else "UNKNOWN"
                if daily_counts[day_key] < self.max_trades_per_day:
                    daily_counts[day_key] += 1
                    filtered_trades.append(t)
            all_trades = filtered_trades

        return all_trades
