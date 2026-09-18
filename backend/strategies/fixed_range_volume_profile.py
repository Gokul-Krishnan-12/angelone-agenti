"""
Fixed Range Volume Profile (FRVP) Strategy
===========================================
Auction Market Theory (AMT) implementation using Point of Control (POC),
Value Area High (VAH), and Value Area Low (VAL).

The Value Area defines the price range where 68-70% of volume occurred over
a fixed lookback window (default: 40 bars).

Key Setups:
1. VAH Breakout (BUY): Price accepts above Value Area High on volume expansion.
   Stop loss placed below POC / Value Area boundary.
2. VAL Breakdown (SELL): Price breaks below Value Area Low on volume expansion.
   Stop loss placed above POC / Value Area boundary.
3. Value Area Mean Reversion (BUY/SELL): Rejections at VAL bouncing back into POC,
   or rejections at VAH rejecting back toward POC.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .base import BaseStrategy
from .utils import compute_atr, compute_relative_volume, compute_volume_profile

LOOKBACK_BARS = 40
MIN_BARS = 25


class FixedRangeVolumeProfileStrategy(BaseStrategy):
    """Fixed Range Volume Profile Strategy using Auction Market Theory."""

    def get_name(self) -> str:
        return "Fixed Range Volume Profile"

    def get_description(self) -> str:
        return (
            "Detects institutional auction acceptance and rejections using Point of Control (POC), "
            "Value Area High (VAH), and Value Area Low (VAL) over a fixed rolling range."
        )

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if df is None or len(df) < MIN_BARS:
            return []

        # Compute volume profile over recent fixed window
        profile = compute_volume_profile(df, n_bars=LOOKBACK_BARS, n_bins=20)
        poc = profile["poc"]
        vah = profile["value_area_high"]
        val = profile["value_area_low"]

        if vah <= val or poc <= 0:
            return []

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        curr_close = float(curr["close"])
        curr_open = float(curr["open"])
        curr_high = float(curr["high"])
        curr_low = float(curr["low"])
        prev_close = float(prev["close"])

        atr = compute_atr(df, period=14)
        if atr <= 0 or pd.isna(atr):
            atr = curr_close * 0.01

        rvol = compute_relative_volume(df, period=20)
        candle_range = max(0.01, curr_high - curr_low)
        lower_wick = max(0.0, min(curr_open, curr_close) - curr_low)
        upper_wick = max(0.0, curr_high - max(curr_open, curr_close))

        signals: List[Dict[str, Any]] = []

        # ── Setup 1: Bullish VAH Breakout (Auction Expansion Upward) ─────────
        if (
            prev_close <= vah
            and curr_close > vah
            and curr_close > curr_open
            and rvol >= 1.15
        ):
            sl = round(max(poc, vah - 1.2 * atr), 2)
            if sl >= curr_close:
                sl = round(curr_close - 1.5 * atr, 2)
            risk = abs(curr_close - sl)
            target = round(curr_close + risk * 2.2, 2)
            rr = self.calculate_rr(curr_close, sl, target)

            signals.append(
                self.format_signal(
                    tradingsymbol=tradingsymbol,
                    direction="BUY",
                    confidence=85,
                    entry=curr_close,
                    sl=sl,
                    target=target,
                    rr=rr,
                    reasoning=f"Bullish VAH breakout ({curr_close:.2f} > VAH {vah:.2f}, POC: {poc:.2f}, RVOL: {rvol:.2f}x)",
                    indicators={
                        "poc": poc,
                        "vah": vah,
                        "val": val,
                        "rvol": round(rvol, 2),
                        "atr": round(atr, 2),
                        "setup": "VAH_BREAKOUT",
                    },
                )
            )

        # ── Setup 2: Bearish VAL Breakdown (Auction Expansion Downward) ───────
        elif (
            prev_close >= val
            and curr_close < val
            and curr_close < curr_open
            and rvol >= 1.15
        ):
            sl = round(min(poc, val + 1.2 * atr), 2)
            if sl <= curr_close:
                sl = round(curr_close + 1.5 * atr, 2)
            risk = abs(sl - curr_close)
            target = round(curr_close - risk * 2.2, 2)
            rr = self.calculate_rr(curr_close, sl, target)

            signals.append(
                self.format_signal(
                    tradingsymbol=tradingsymbol,
                    direction="SELL",
                    confidence=85,
                    entry=curr_close,
                    sl=sl,
                    target=target,
                    rr=rr,
                    reasoning=f"Bearish VAL breakdown ({curr_close:.2f} < VAL {val:.2f}, POC: {poc:.2f}, RVOL: {rvol:.2f}x)",
                    indicators={
                        "poc": poc,
                        "vah": vah,
                        "val": val,
                        "rvol": round(rvol, 2),
                        "atr": round(atr, 2),
                        "setup": "VAL_BREAKDOWN",
                    },
                )
            )

        # ── Setup 3: Value Area Low Rejection & Mean Reversion (BUY) ─────────
        elif (
            curr_low <= val
            and curr_close > val
            and curr_close > curr_open
            and (lower_wick / candle_range) >= 0.35
        ):
            sl = round(curr_low - 0.4 * atr, 2)
            risk = abs(curr_close - sl)
            # First target POC, extended target VAH
            target = round(max(poc, curr_close + risk * 2.0), 2)
            rr = self.calculate_rr(curr_close, sl, target)

            signals.append(
                self.format_signal(
                    tradingsymbol=tradingsymbol,
                    direction="BUY",
                    confidence=80,
                    entry=curr_close,
                    sl=sl,
                    target=target,
                    rr=rr,
                    reasoning=f"VAL rejection bounce ({curr_low:.2f} swept VAL {val:.2f}, closed {curr_close:.2f}, POC target: {poc:.2f})",
                    indicators={
                        "poc": poc,
                        "vah": vah,
                        "val": val,
                        "rvol": round(rvol, 2),
                        "atr": round(atr, 2),
                        "setup": "VAL_REJECTION",
                    },
                )
            )

        # ── Setup 4: Value Area High Rejection & Mean Reversion (SELL) ────────
        elif (
            curr_high >= vah
            and curr_close < vah
            and curr_close < curr_open
            and (upper_wick / candle_range) >= 0.35
        ):
            sl = round(curr_high + 0.4 * atr, 2)
            risk = abs(sl - curr_close)
            # First target POC, extended target VAL
            target = round(min(poc, curr_close - risk * 2.0), 2)
            rr = self.calculate_rr(curr_close, sl, target)

            signals.append(
                self.format_signal(
                    tradingsymbol=tradingsymbol,
                    direction="SELL",
                    confidence=80,
                    entry=curr_close,
                    sl=sl,
                    target=target,
                    rr=rr,
                    reasoning=f"VAH rejection ({curr_high:.2f} swept VAH {vah:.2f}, closed {curr_close:.2f}, POC target: {poc:.2f})",
                    indicators={
                        "poc": poc,
                        "vah": vah,
                        "val": val,
                        "rvol": round(rvol, 2),
                        "atr": round(atr, 2),
                        "setup": "VAH_REJECTION",
                    },
                )
            )

        return signals
