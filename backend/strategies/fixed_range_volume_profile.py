"""
Fixed Range Volume Profile (FRVP) Strategy — High-Conviction Auction Market Theory (AMT)
========================================================================================
Implements institutional Auction Market Theory using Point of Control (POC),
Value Area High (VAH), and Value Area Low (VAL).

Key Enhancements (High-Conviction Upgrade):
1. Anchored Session Profile (09:15 IST) with rolling fallback (80 bars, 30 bins).
2. Pre-Trade Value Area Compression Guard: VA_Width >= 1.8 * ATR to prevent chop whipsaws.
3. Low Volume Node (LVN) Vacuum Filter: Rejects breakouts directly into dense absorption nodes.
4. 2-Bar Acceptance & Initiative Candle Validation for Breakouts (Setups 1 & 2).
5. Liquidity Sweep Mean Reversions (Setups 3 & 4) strictly targeting POC with RR >= 1.3.
6. Midday Value Lull (11:30–13:30 IST) & Friction Buffering.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import BaseStrategy
from .utils import (
    compute_atr,
    compute_relative_volume,
    compute_volume_profile,
    is_initiative_candle,
    is_lvn_vacuum,
)

LOOKBACK_BARS = 80
MIN_BARS = 25


class FixedRangeVolumeProfileStrategy(BaseStrategy):
    """High-Conviction Fixed Range Volume Profile Strategy using Auction Market Theory."""

    def get_name(self) -> str:
        return "Fixed Range Volume Profile"

    def get_description(self) -> str:
        return (
            "Detects high-conviction institutional auction acceptance and rejections using "
            "Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL) "
            "with LVN vacuum and 2-bar acceptance filtering."
        )

    def _get_bar_time(self, df: pd.DataFrame, idx: int = -1) -> Optional[datetime.time]:
        """Extract time-of-day for the specified candle index."""
        try:
            if "datetime" in df.columns:
                dt = pd.to_datetime(df["datetime"].iloc[idx])
                return dt.time()
            if "timestamp" in df.columns:
                dt = pd.to_datetime(df["timestamp"].iloc[idx])
                return dt.time()
            if isinstance(df.index, pd.DatetimeIndex):
                return df.index[idx].time()
        except Exception:
            pass
        return None

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if df is None or len(df) < MIN_BARS:
            return []

        # Module A: Compute volume profile (anchored session or rolling fallback, 30 bins)
        profile = compute_volume_profile(
            df, n_bars=LOOKBACK_BARS, n_bins=30, anchor_session=True
        )
        poc = float(profile["poc"])
        vah = float(profile["value_area_high"])
        val = float(profile["value_area_low"])

        if vah <= val or poc <= 0:
            return []

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        prev_2 = df.iloc[-3] if len(df) >= 3 else prev

        curr_close = float(curr["close"])
        curr_open = float(curr["open"])
        curr_high = float(curr["high"])
        curr_low = float(curr["low"])
        curr_vol = float(curr.get("volume", 0.0))

        prev_close = float(prev["close"])
        prev_vol = float(prev.get("volume", 1.0))
        prev_2_close = float(prev_2["close"])

        atr = compute_atr(df, period=14)
        if atr <= 0 or pd.isna(atr):
            atr = curr_close * 0.01

        candle_range = max(0.01, curr_high - curr_low)
        rvol = compute_relative_volume(df, period=20)

        # Module B: Pre-Trade Gating (Value Area Compression Guard)
        va_width = (vah - val) / atr
        is_va_compressed = va_width < 1.8

        # Execution Guardrail: Midday Value Lull (11:30 - 13:30 IST)
        bar_time = self._get_bar_time(df, -1)
        if bar_time is None:
            # Fallback to current system time in IST
            now_ist = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            )
            bar_time = now_ist.time()

        is_midday_lull = (
            bar_time is not None
            and datetime.time(11, 30) <= bar_time <= datetime.time(13, 30)
        )

        # Execution Guardrail: Friction Buffer (net gain to Target 1 >= 4.0x round-trip friction)
        # Indian intraday cash equity friction (brokerage + STT + turnover + GST + slippage) ~ 0.09%
        friction_per_share = curr_close * 0.0009

        signals: List[Dict[str, Any]] = []

        # ── Setup 1: Bullish VAH Breakout (Auction Expansion Upward) ─────────
        if (
            not is_va_compressed
            and not is_midday_lull
            and prev_2_close <= vah
            and prev_close > vah
            and curr_close > vah
            and is_initiative_candle(curr, "BUY")
            and rvol >= 1.65
            and curr_vol >= prev_vol * 1.25
            and is_lvn_vacuum(profile, "BUY")
        ):
            sl = round(vah - 0.8 * atr, 2)
            # Never set SL above entry or into POC if within 0.5 * ATR of entry
            if abs(curr_close - poc) <= 0.5 * atr or sl >= curr_close:
                sl = round(curr_close - 1.2 * atr, 2)

            risk = abs(curr_close - sl)
            target = round(curr_close + risk * 2.0, 2)
            rr = self.calculate_rr(curr_close, sl, target)

            # Target 1 is at +1.2R
            target1_gain = risk * 1.2
            if target1_gain >= 4.0 * friction_per_share and risk > 0:
                signals.append(
                    self.format_signal(
                        tradingsymbol=tradingsymbol,
                        direction="BUY",
                        confidence=88,
                        entry=curr_close,
                        sl=sl,
                        target=target,
                        rr=rr,
                        reasoning=(
                            f"High-conviction VAH breakout with 2-bar acceptance & LVN vacuum "
                            f"(entry: {curr_close:.2f} > VAH: {vah:.2f}, POC: {poc:.2f}, "
                            f"RVOL: {rvol:.2f}x, vol surge: {curr_vol / max(1.0, prev_vol):.2f}x)"
                        ),
                        indicators={
                            "poc": poc,
                            "vah": vah,
                            "val": val,
                            "va_width": round(va_width, 2),
                            "rvol": round(rvol, 2),
                            "atr": round(atr, 2),
                            "setup": "VAH_BREAKOUT",
                            "is_structural_target": False,
                        },
                    )
                )

        # ── Setup 2: Bearish VAL Breakdown (Auction Expansion Downward) ───────
        elif (
            not is_va_compressed
            and not is_midday_lull
            and prev_2_close >= val
            and prev_close < val
            and curr_close < val
            and is_initiative_candle(curr, "SELL")
            and rvol >= 1.65
            and curr_vol >= prev_vol * 1.25
            and is_lvn_vacuum(profile, "SELL")
        ):
            sl = round(val + 0.8 * atr, 2)
            if abs(poc - curr_close) <= 0.5 * atr or sl <= curr_close:
                sl = round(curr_close + 1.2 * atr, 2)

            risk = abs(sl - curr_close)
            target = round(curr_close - risk * 2.0, 2)
            rr = self.calculate_rr(curr_close, sl, target)

            target1_gain = risk * 1.2
            if target1_gain >= 4.0 * friction_per_share and risk > 0:
                signals.append(
                    self.format_signal(
                        tradingsymbol=tradingsymbol,
                        direction="SELL",
                        confidence=88,
                        entry=curr_close,
                        sl=sl,
                        target=target,
                        rr=rr,
                        reasoning=(
                            f"High-conviction VAL breakdown with 2-bar acceptance & LVN vacuum "
                            f"(entry: {curr_close:.2f} < VAL: {val:.2f}, POC: {poc:.2f}, "
                            f"RVOL: {rvol:.2f}x, vol surge: {curr_vol / max(1.0, prev_vol):.2f}x)"
                        ),
                        indicators={
                            "poc": poc,
                            "vah": vah,
                            "val": val,
                            "va_width": round(va_width, 2),
                            "rvol": round(rvol, 2),
                            "atr": round(atr, 2),
                            "setup": "VAL_BREAKDOWN",
                            "is_structural_target": False,
                        },
                    )
                )

        # ── Setup 3: Liquidity Sweep (BUY — VAL Sweep & Rejection) ───────────
        # Mean-reversion setups are permitted even during midday lull and compression
        elif (
            curr_low <= (val - 0.2 * atr)
            and curr_close > val
            and curr_close > curr_open
            and ((min(curr_open, curr_close) - curr_low) / candle_range) >= 0.40
        ):
            sl = round(curr_low - 0.3 * atr, 2)
            risk = abs(curr_close - sl)
            # Primary target is strictly the Point of Control (POC)
            target = round(poc, 2)

            # Geometry Filter: (POC - entry) / risk >= 1.3
            structural_reward = poc - curr_close
            structural_rr = (structural_reward / risk) if risk > 0 else 0.0

            if (
                structural_rr >= 1.3
                and structural_reward >= 4.0 * friction_per_share
                and target > curr_close
            ):
                rr = round(structural_rr, 2)
                signals.append(
                    self.format_signal(
                        tradingsymbol=tradingsymbol,
                        direction="BUY",
                        confidence=84,
                        entry=curr_close,
                        sl=sl,
                        target=target,
                        rr=rr,
                        reasoning=(
                            f"VAL liquidity sweep & rejection bounce (low: {curr_low:.2f} swept VAL: {val:.2f}, "
                            f"closed: {curr_close:.2f}, structural POC target: {poc:.2f}, RR: {rr:.2f})"
                        ),
                        indicators={
                            "poc": poc,
                            "vah": vah,
                            "val": val,
                            "rvol": round(rvol, 2),
                            "atr": round(atr, 2),
                            "setup": "VAL_REJECTION",
                            "is_structural_target": True,
                        },
                    )
                )

        # ── Setup 4: Liquidity Sweep (SELL — VAH Sweep & Rejection) ──────────
        elif (
            curr_high >= (vah + 0.2 * atr)
            and curr_close < vah
            and curr_close < curr_open
            and ((curr_high - max(curr_open, curr_close)) / candle_range) >= 0.40
        ):
            sl = round(curr_high + 0.3 * atr, 2)
            risk = abs(sl - curr_close)
            # Primary target is strictly the Point of Control (POC)
            target = round(poc, 2)

            # Geometry Filter: (entry - POC) / risk >= 1.3
            structural_reward = curr_close - poc
            structural_rr = (structural_reward / risk) if risk > 0 else 0.0

            if (
                structural_rr >= 1.3
                and structural_reward >= 4.0 * friction_per_share
                and target < curr_close
            ):
                rr = round(structural_rr, 2)
                signals.append(
                    self.format_signal(
                        tradingsymbol=tradingsymbol,
                        direction="SELL",
                        confidence=84,
                        entry=curr_close,
                        sl=sl,
                        target=target,
                        rr=rr,
                        reasoning=(
                            f"VAH liquidity sweep & rejection (high: {curr_high:.2f} swept VAH: {vah:.2f}, "
                            f"closed: {curr_close:.2f}, structural POC target: {poc:.2f}, RR: {rr:.2f})"
                        ),
                        indicators={
                            "poc": poc,
                            "vah": vah,
                            "val": val,
                            "rvol": round(rvol, 2),
                            "atr": round(atr, 2),
                            "setup": "VAH_REJECTION",
                            "is_structural_target": True,
                        },
                    )
                )

        return signals
