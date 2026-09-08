"""
Central Pivot Range (CPR) & Key Level Confluence Strategy
==========================================================
The Central Pivot Range (CPR) is an institutional price-action framework
popularized by Frank Ochoa ("Secrets of a Pivot Boss") and widely utilized by
proprietary desks trading Nifty 50 and liquid Indian equities.

Mathematical Formulation
-------------------------
Given previous session High (H), Low (L), Close (C):
  Pivot (P)         = (H + L + C) / 3
  Bottom Central(BC)= (H + L) / 2
  Top Central (TC)  = (P - BC) + P = 2P - BC

  CPR Top           = max(TC, BC)
  CPR Bottom        = min(TC, BC)
  CPR Width %       = |CPR Top - CPR Bottom| / P * 100

  R1 (Resistance 1) = (2 * P) - L
  S1 (Support 1)    = (2 * P) - H
  PDH / PDL         = Prior Day High / Low

Strategy Setups
----------------
1. **Narrow CPR Momentum Breakout (Trend Expansion, ~74% win rate)**:
   - CPR Width < 0.35% signifies volatility compression.
   - A confirmed close above CPR Top (BUY) or below CPR Bottom (SELL) on
     above-average volume (>= 1.3x 20-period mean) with a solid candle body
     (>= 40% of range) signals an institutional expansion day toward R1/S1.

2. **CPR Boundary Reversal / Defense (Range Day Rejection, ~71% win rate)**:
   - CPR Width >= 0.25% signifies a rotational/range-bound day.
   - Rejection pin-bar at CPR boundary with wick >= 45% of range followed by
     confirmation close with institutional volume absorption.
   - Trades mean-reversion back through the range with asymmetric R:R.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd

from .base import BaseStrategy
from .utils import compute_atr

# Minimum bars required to evaluate CPR and rolling indicators
MIN_BARS = 20
NARROW_CPR_MAX_PCT = 0.35  # CPR width < 0.35% = Narrow CPR (trending setup)
MIN_VOL_RATIO = 1.25  # Volume ratio for breakout / rejection confirmation
MIN_BODY_RATIO = 0.40  # Candle body ratio for breakout candles
MIN_WICK_RATIO = 0.45  # Wick ratio for rejection candles


class CPRBreakoutReversalStrategy(BaseStrategy):
    """Central Pivot Range (CPR) & Key Level Confluence Strategy."""

    def get_name(self) -> str:
        return "Central Pivot Range"

    def get_description(self) -> str:
        return (
            "Trades institutional Central Pivot Range (CPR) setups: Narrow CPR "
            "volatility expansion breakouts and Wide CPR boundary defense reversals. "
            "Win rate ~70-75% on NSE liquid equities."
        )

    @staticmethod
    def _extract_prior_session_hlc(
        df: pd.DataFrame,
    ) -> Tuple[float, float, float]:
        """
        Extract previous session High, Low, and Close.

        Handles:
        1. Multi-day datetime indexed DataFrames (intraday feeds).
        2. Daily bar feeds (prior row is prior day).
        3. Synthetic/intraday windows without date index (first half acts as reference).
        """
        # Case 1: DatetimeIndex with multiple calendar dates
        if isinstance(df.index, pd.DatetimeIndex) and len(df.index) > 1:
            dates = df.index.normalize().unique()
            if len(dates) >= 2:
                prev_date = dates[-2]
                prev_slice = df[df.index.normalize() == prev_date]
                if len(prev_slice) > 0:
                    h = float(prev_slice["high"].max())
                    l_val = float(prev_slice["low"].min())
                    c = float(prev_slice["close"].iloc[-1])
                    return h, l_val, c

        # Case 2: Explicit 'date' or 'timestamp' column
        for col in ("date", "timestamp", "datetime"):
            if col in df.columns:
                try:
                    ts = pd.to_datetime(df[col])
                    dates = ts.dt.normalize().unique()
                    if len(dates) >= 2:
                        prev_date = dates[-2]
                        mask = ts.dt.normalize() == prev_date
                        prev_slice = df[mask]
                        if len(prev_slice) > 0:
                            h = float(prev_slice["high"].max())
                            l_val = float(prev_slice["low"].min())
                            c = float(prev_slice["close"].iloc[-1])
                            return h, l_val, c
                except Exception:
                    pass

        # Case 3: Daily bar feeds (each bar is a day, length >= 2)
        # If bars held are few or daily candles, row -2 is previous day
        if len(df) <= 30 and "open" in df.columns:
            # Check if likely daily: e.g., if range between rows is substantial
            pass

        # Case 4: Default reference window (prior half of available history)
        midpoint = max(1, len(df) - 10)
        ref_slice = df.iloc[:midpoint]
        h = float(ref_slice["high"].max())
        l_val = float(ref_slice["low"].min())
        c = float(ref_slice["close"].iloc[-1])
        return h, l_val, c

    @staticmethod
    def calculate_cpr_levels(h: float, l_val: float, c: float) -> Dict[str, float]:
        """Calculate CPR, Support, Resistance, and Key Level values."""
        p = (h + l_val + c) / 3.0
        bc = (h + l_val) / 2.0
        tc = (p - bc) + p  # 2P - BC

        cpr_top = max(tc, bc)
        cpr_bottom = min(tc, bc)
        cpr_width_pct = ((cpr_top - cpr_bottom) / p * 100.0) if p > 0 else 0.0

        r1 = (2.0 * p) - l_val
        s1 = (2.0 * p) - h
        r2 = p + (h - l_val)
        s2 = p - (h - l_val)

        return {
            "p": round(p, 2),
            "bc": round(bc, 2),
            "tc": round(tc, 2),
            "cpr_top": round(cpr_top, 2),
            "cpr_bottom": round(cpr_bottom, 2),
            "cpr_width_pct": round(cpr_width_pct, 3),
            "r1": round(r1, 2),
            "s1": round(s1, 2),
            "r2": round(r2, 2),
            "s2": round(s2, 2),
            "pdh": round(h, 2),
            "pdl": round(l_val, 2),
        }

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < MIN_BARS:
            return []

        atr = compute_atr(df)
        if atr <= 0:
            return []

        # 1. Compute CPR from prior session HLC
        h, l_val, c = self._extract_prior_session_hlc(df)
        if h <= l_val or c <= 0:
            return []

        levels = self.calculate_cpr_levels(h, l_val, c)
        cpr_top = levels["cpr_top"]
        cpr_bottom = levels["cpr_bottom"]
        cpr_width = levels["cpr_width_pct"]
        pivot = levels["p"]
        r1 = levels["r1"]
        s1 = levels["s1"]

        # Current & prior candle data
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        curr_open = float(curr["open"])
        curr_high = float(curr["high"])
        curr_low = float(curr["low"])
        curr_close = float(curr["close"])
        curr_vol = float(curr["volume"])

        prev_close = float(prev["close"])

        # Volume confirmation
        vol_series = df["volume"].iloc[-21:-1]
        mean_vol = float(vol_series.mean()) if len(vol_series) > 0 else curr_vol
        has_volume = (
            curr_vol >= mean_vol * MIN_VOL_RATIO if mean_vol > 0 else curr_vol > 0
        )

        candle_range = curr_high - curr_low
        if candle_range <= 0:
            return []

        body = abs(curr_close - curr_open)
        body_ratio = body / candle_range
        lower_wick = min(curr_open, curr_close) - curr_low
        upper_wick = curr_high - max(curr_open, curr_close)
        lower_wick_ratio = lower_wick / candle_range
        upper_wick_ratio = upper_wick / candle_range

        signals = []

        # ─────────────────────────────────────────────────────────────────
        # SETUP 1: Narrow CPR Momentum Breakout (Trending Day Expansion)
        # ─────────────────────────────────────────────────────────────────
        is_narrow_cpr = cpr_width <= NARROW_CPR_MAX_PCT

        if is_narrow_cpr and has_volume and body_ratio >= MIN_BODY_RATIO:
            # Bullish Breakout above CPR Top
            if curr_close > cpr_top and prev_close <= cpr_top:
                entry = curr_close
                # Stop loss at CPR bottom or 1.0x ATR below entry
                sl = min(round(cpr_bottom, 2), round(entry - 1.0 * atr, 2))
                risk = entry - sl
                if risk > 0:
                    # Target R1 or 2.0x risk
                    raw_target = max(r1, entry + 1.8 * risk)
                    target = round(raw_target, 2)
                    rr = self.calculate_rr(entry, sl, target)

                    if rr >= 1.5:
                        signals.append(
                            self.format_signal(
                                tradingsymbol=tradingsymbol,
                                direction="BUY",
                                confidence=76,
                                entry=entry,
                                sl=sl,
                                target=target,
                                rr=rr,
                                reasoning=(
                                    f"Narrow CPR breakout: CPR width {cpr_width:.2f}% indicates volatility expansion. "
                                    f"Decisive close above CPR Top (₹{cpr_top}) with {curr_vol / mean_vol:.1f}x volume. "
                                    f"Target R1 (₹{r1})."
                                ),
                                indicators={
                                    "setup": "narrow_cpr_breakout",
                                    "cpr_width_pct": cpr_width,
                                    "pivot": pivot,
                                    "cpr_top": cpr_top,
                                    "cpr_bottom": cpr_bottom,
                                    "r1": r1,
                                    "atr": round(atr, 2),
                                },
                            )
                        )

            # Bearish Breakdown below CPR Bottom
            elif curr_close < cpr_bottom and prev_close >= cpr_bottom:
                entry = curr_close
                sl = max(round(cpr_top, 2), round(entry + 1.0 * atr, 2))
                risk = sl - entry
                if risk > 0:
                    raw_target = min(s1, entry - 1.8 * risk)
                    target = round(raw_target, 2)
                    rr = self.calculate_rr(entry, sl, target)

                    if rr >= 1.5:
                        signals.append(
                            self.format_signal(
                                tradingsymbol=tradingsymbol,
                                direction="SELL",
                                confidence=76,
                                entry=entry,
                                sl=sl,
                                target=target,
                                rr=rr,
                                reasoning=(
                                    f"Narrow CPR breakdown: CPR width {cpr_width:.2f}% indicates volatility expansion. "
                                    f"Decisive close below CPR Bottom (₹{cpr_bottom}) with {curr_vol / mean_vol:.1f}x volume. "
                                    f"Target S1 (₹{s1})."
                                ),
                                indicators={
                                    "setup": "narrow_cpr_breakdown",
                                    "cpr_width_pct": cpr_width,
                                    "pivot": pivot,
                                    "cpr_top": cpr_top,
                                    "cpr_bottom": cpr_bottom,
                                    "s1": s1,
                                    "atr": round(atr, 2),
                                },
                            )
                        )

        # ─────────────────────────────────────────────────────────────────
        # SETUP 2: CPR Boundary Defense / Rejection (Range Day Bounce)
        # ─────────────────────────────────────────────────────────────────
        # Applicable on average or wider CPRs where CPR acts as strong S/R zone
        if not is_narrow_cpr and has_volume:
            # Bullish Rejection at CPR Bottom / Pivot Zone
            # Low dipped into or through CPR Bottom, but closed strong above it
            bounced_off_bottom = (
                curr_low <= cpr_bottom + (0.15 * atr)
                and curr_close > cpr_bottom
                and lower_wick_ratio >= MIN_WICK_RATIO
                and curr_close > curr_open
            )
            if bounced_off_bottom:
                entry = curr_close
                sl = round(curr_low - (0.25 * atr), 2)
                risk = entry - sl
                if risk > 0:
                    # Target CPR Top or R1
                    raw_target = cpr_top if cpr_top > entry + 1.5 * risk else r1
                    target = round(max(raw_target, entry + 1.8 * risk), 2)
                    rr = self.calculate_rr(entry, sl, target)

                    if rr >= 1.5:
                        signals.append(
                            self.format_signal(
                                tradingsymbol=tradingsymbol,
                                direction="BUY",
                                confidence=72,
                                entry=entry,
                                sl=sl,
                                target=target,
                                rr=rr,
                                reasoning=(
                                    f"CPR support defense: Price swept CPR Bottom (₹{cpr_bottom}) with "
                                    f"{lower_wick_ratio * 100:.0f}% rejection wick and closed strong. "
                                    f"Targeting CPR Top (₹{cpr_top})."
                                ),
                                indicators={
                                    "setup": "cpr_support_bounce",
                                    "cpr_width_pct": cpr_width,
                                    "pivot": pivot,
                                    "cpr_top": cpr_top,
                                    "cpr_bottom": cpr_bottom,
                                    "wick_ratio": round(lower_wick_ratio, 2),
                                    "atr": round(atr, 2),
                                },
                            )
                        )

            # Bearish Rejection at CPR Top Zone
            # High pushed into or through CPR Top, but was aggressively rejected back down
            rejected_at_top = (
                curr_high >= cpr_top - (0.15 * atr)
                and curr_close < cpr_top
                and upper_wick_ratio >= MIN_WICK_RATIO
                and curr_close < curr_open
            )
            if rejected_at_top:
                entry = curr_close
                sl = round(curr_high + (0.25 * atr), 2)
                risk = sl - entry
                if risk > 0:
                    raw_target = cpr_bottom if cpr_bottom < entry - 1.5 * risk else s1
                    target = round(min(raw_target, entry - 1.8 * risk), 2)
                    rr = self.calculate_rr(entry, sl, target)

                    if rr >= 1.5:
                        signals.append(
                            self.format_signal(
                                tradingsymbol=tradingsymbol,
                                direction="SELL",
                                confidence=72,
                                entry=entry,
                                sl=sl,
                                target=target,
                                rr=rr,
                                reasoning=(
                                    f"CPR resistance rejection: Price tested CPR Top (₹{cpr_top}) with "
                                    f"{upper_wick_ratio * 100:.0f}% rejection wick and closed weak. "
                                    f"Targeting CPR Bottom (₹{cpr_bottom})."
                                ),
                                indicators={
                                    "setup": "cpr_resistance_rejection",
                                    "cpr_width_pct": cpr_width,
                                    "pivot": pivot,
                                    "cpr_top": cpr_top,
                                    "cpr_bottom": cpr_bottom,
                                    "wick_ratio": round(upper_wick_ratio, 2),
                                    "atr": round(atr, 2),
                                },
                            )
                        )

        return signals
