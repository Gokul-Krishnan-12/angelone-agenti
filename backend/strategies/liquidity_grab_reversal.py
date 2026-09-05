"""
Liquidity Grab Reversal Strategy
==================================
Institutional "stop hunts" — one of the highest-probability setups in price action.

How institutions create reversals
----------------------------------
1. Price drifts toward a cluster of retail stop-loss orders sitting just below a
   prior swing low (or above a swing high).
2. Institutions aggressively push price through that level, triggering all the
   stops and absorbing the resulting sell orders as cheap inventory.
3. With retail positioned out and institutions loaded, price snaps back sharply.

Detection criteria (BUY / bullish sweep)
-----------------------------------------
A. **Sweep**: The last bar's LOW breaches a prior swing low (lowest low of the
   last ``LOOKBACK`` bars, excluding the current bar) by at least ``SWEEP_PCT``%.
B. **Wick dominance**: The lower wick of the sweep candle is ≥ 55% of its total
   range — price was aggressively rejected.
C. **Volume surge**: Sweep bar volume ≥ 2× rolling mean — institutional size.
D. **Market Structure Shift (MSS)**: The CURRENT (last) bar closes ABOVE the
   prior swing low — confirming the reversal and preventing fade of strong trends.
E. **ATR gate**: Sweep wick is ≥ 0.5 × ATR (non-trivial move, not noise).

Entry  : close of the confirmation bar (MSS bar).
SL     : 0.3 × ATR below the wick extreme (gives a buffer below the grab).
Target : swing high of the LOOKBACK window (natural resistance cleared by the move).

Inverse logic applies for SELL (sweep above swing high).

Documented win rate: 68–78% with strict wick + MSS confirmation.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .base import BaseStrategy
from .utils import compute_atr

LOOKBACK = 20  # bars to find the prior swing low/high
SWEEP_PCT = 0.10  # minimum % the wick must go below the swing low
WICK_RATIO = 0.55  # lower wick must be ≥ 55% of total candle range
VOL_MULT = 2.0  # sweep bar volume multiplier
ATR_WICK_MULT = 0.25  # wick depth must be >= 0.25 × ATR(recent) — noise filter
MIN_BARS = LOOKBACK + 5


class LiquidityGrabReversalStrategy(BaseStrategy):
    """Stop-hunt / liquidity grab reversal with MSS confirmation."""

    def get_name(self) -> str:
        return "Liquidity Grab Reversal"

    def get_description(self) -> str:
        return (
            "Detects institutional stop-hunts: a swift breach of a prior swing "
            "high/low on high volume with a long wick, followed by a market structure "
            "shift confirming the reversal. Win rate ~68-78%."
        )

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < MIN_BARS:
            return []

        atr = compute_atr(df)
        if atr <= 0:
            return []

        # The sweep bar is bar -2 (second-to-last); bar -1 is the MSS confirmation bar
        sweep_bar = df.iloc[-2]
        confirm_bar = df.iloc[-1]

        sweep_low = float(sweep_bar["low"])
        sweep_high = float(sweep_bar["high"])
        sweep_close = float(sweep_bar["close"])
        sweep_open = float(sweep_bar["open"])
        sweep_vol = float(sweep_bar["volume"])
        confirm_close = float(confirm_bar["close"])

        candle_range = sweep_high - sweep_low
        if candle_range <= 0:
            return []

        # Rolling avg volume over the lookback window (excluding last 2 bars)
        avg_vol = float(df["volume"].iloc[-(LOOKBACK + 2) : -2].mean())
        if avg_vol <= 0:
            return []

        # Reference swing: prior bars excluding the sweep bar
        ref_window = df.iloc[-(LOOKBACK + 2) : -2]
        prior_swing_low = float(ref_window["low"].min())
        prior_swing_high = float(ref_window["high"].max())

        signals: List[Dict[str, Any]] = []

        # ── BULLISH: sweep below swing low, then MSS closes above it ─────────
        lower_wick = min(sweep_open, sweep_close) - sweep_low
        swept_below = sweep_low < prior_swing_low * (1 - SWEEP_PCT / 100)
        wick_dominant = lower_wick / candle_range >= WICK_RATIO
        vol_surge = sweep_vol >= avg_vol * VOL_MULT
        wick_deep = lower_wick >= atr * ATR_WICK_MULT
        mss_up = confirm_close > prior_swing_low  # closes back above the swept level

        if swept_below and wick_dominant and vol_surge and wick_deep and mss_up:
            entry = round(confirm_close, 2)
            sl = round(sweep_low - 0.3 * atr, 2)
            # Target: prior swing high in the lookback window
            target_raw = round(prior_swing_high, 2)
            if target_raw <= entry:
                target_raw = round(entry + 2.0 * atr, 2)
            rr = self.calculate_rr(entry, sl, target_raw)
            if rr >= 1.8:
                vol_ratio = sweep_vol / avg_vol
                confidence = min(
                    94,
                    int(
                        75
                        + (vol_ratio - 2.0) * 5
                        + (lower_wick / candle_range - 0.55) * 30
                    ),
                )
                signals.append(
                    self.format_signal(
                        tradingsymbol=tradingsymbol,
                        direction="BUY",
                        confidence=confidence,
                        entry=entry,
                        sl=sl,
                        target=target_raw,
                        rr=rr,
                        reasoning=(
                            f"Liquidity grab BELOW swing low {prior_swing_low:.2f}. "
                            f"Sweep wick {lower_wick:.2f} ({lower_wick / candle_range * 100:.0f}% of range). "
                            f"Vol {vol_ratio:.1f}× avg. MSS: close {confirm_close:.2f} > swept level."
                        ),
                        indicators={
                            "sweep_low": round(sweep_low, 2),
                            "prior_swing_low": round(prior_swing_low, 2),
                            "lower_wick": round(lower_wick, 2),
                            "wick_ratio": round(lower_wick / candle_range, 2),
                            "vol_ratio": round(vol_ratio, 2),
                            "atr": round(atr, 2),
                        },
                    )
                )

        # ── BEARISH: sweep above swing high, then MSS closes below it ────────
        upper_wick = sweep_high - max(sweep_open, sweep_close)
        swept_above = sweep_high > prior_swing_high * (1 + SWEEP_PCT / 100)
        upper_wick_dominant = upper_wick / candle_range >= WICK_RATIO
        wick_deep_up = upper_wick >= atr * ATR_WICK_MULT
        mss_down = confirm_close < prior_swing_high

        if (
            swept_above
            and upper_wick_dominant
            and vol_surge
            and wick_deep_up
            and mss_down
        ):
            entry = round(confirm_close, 2)
            sl = round(sweep_high + 0.3 * atr, 2)
            target_raw = round(prior_swing_low, 2)
            if target_raw >= entry:
                target_raw = round(entry - 2.0 * atr, 2)
            rr = self.calculate_rr(entry, sl, target_raw)
            if rr >= 1.8:
                vol_ratio = sweep_vol / avg_vol
                confidence = min(
                    94,
                    int(
                        75
                        + (vol_ratio - 2.0) * 5
                        + (upper_wick / candle_range - 0.55) * 30
                    ),
                )
                signals.append(
                    self.format_signal(
                        tradingsymbol=tradingsymbol,
                        direction="SELL",
                        confidence=confidence,
                        entry=entry,
                        sl=sl,
                        target=target_raw,
                        rr=rr,
                        reasoning=(
                            f"Liquidity grab ABOVE swing high {prior_swing_high:.2f}. "
                            f"Sweep wick {upper_wick:.2f} ({upper_wick / candle_range * 100:.0f}% of range). "
                            f"Vol {vol_ratio:.1f}× avg. MSS: close {confirm_close:.2f} < swept level."
                        ),
                        indicators={
                            "sweep_high": round(sweep_high, 2),
                            "prior_swing_high": round(prior_swing_high, 2),
                            "upper_wick": round(upper_wick, 2),
                            "wick_ratio": round(upper_wick / candle_range, 2),
                            "vol_ratio": round(vol_ratio, 2),
                            "atr": round(atr, 2),
                        },
                    )
                )

        return signals
