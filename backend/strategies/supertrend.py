"""
Supertrend Strategy — with volume confirmation on flip candle.

Changes from v1
---------------
• Volume on flip candle must be ≥ 1.5 × 20-period average.
  A Supertrend flip without participation from larger players is a false signal.
• Strong-close confirmation: the flip candle must close in the top/bottom 40 %
  of its range (bullish for BUY, bearish for SELL).
• ADX threshold unchanged at 25.
• SL remains at the Supertrend band (structural level — no change, it's already good).
"""

from typing import Any, Dict, List

import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange

from .base import BaseStrategy

_MIN_VOL_RATIO = 1.5  # volume must be 1.5× avg on the flip candle
_MIN_CLOSE_PCT = 0.40  # close must be in top/bottom 40 % of candle range


class SupertrendStrategy(BaseStrategy):
    def get_name(self) -> str:
        return "Supertrend"

    def get_description(self) -> str:
        return (
            "Supertrend(10,3) direction flip confirmed by ADX > 25, "
            "volume ≥ 1.5× average on the flip candle, and a strong close."
        )

    def calculate_supertrend(
        self, df: pd.DataFrame, period: int = 10, multiplier: int = 3
    ):
        atr = AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"], window=period
        ).average_true_range()

        hl2 = (df["high"] + df["low"]) / 2
        final_upperband = hl2 + (multiplier * atr)
        final_lowerband = hl2 - (multiplier * atr)

        supertrend = [True] * len(df)

        for i in range(1, len(df)):
            curr, prev = i, i - 1

            if df["close"].iloc[curr] > final_upperband.iloc[prev]:
                supertrend[curr] = True
            elif df["close"].iloc[curr] < final_lowerband.iloc[prev]:
                supertrend[curr] = False
            else:
                supertrend[curr] = supertrend[prev]

                if (
                    supertrend[curr]
                    and final_lowerband.iloc[curr] < final_lowerband.iloc[prev]
                ):
                    final_lowerband.iloc[curr] = final_lowerband.iloc[prev]
                if (
                    not supertrend[curr]
                    and final_upperband.iloc[curr] > final_upperband.iloc[prev]
                ):
                    final_upperband.iloc[curr] = final_upperband.iloc[prev]

        return supertrend, final_lowerband, final_upperband

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < 30:
            return []

        signals: List[Dict[str, Any]] = []
        df = df.copy()

        adx = ADXIndicator(
            high=df["high"], low=df["low"], close=df["close"], window=14
        ).adx()
        df["adx"] = adx

        supertrend, lowerband, upperband = self.calculate_supertrend(df, 10, 3)
        df["supertrend"] = supertrend
        df["lowerband"] = lowerband
        df["upperband"] = upperband

        vol_sma = df["volume"].rolling(window=20).mean()
        df["vol_sma"] = vol_sma

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # ── Regime gate ────────────────────────────────────────────────
        if last["adx"] <= 25:
            return []

        # ── Volume gate on the flip candle ─────────────────────────────
        vol_ratio = last["volume"] / last["vol_sma"] if last["vol_sma"] > 0 else 1.0
        if vol_ratio < _MIN_VOL_RATIO:
            return []

        candle_range = float(last["high"]) - float(last["low"])

        # ── BUY: Supertrend flipped bullish ────────────────────────────
        if not prev["supertrend"] and last["supertrend"]:
            # Strong close: close must be in top 40 % of candle range
            if candle_range > 0:
                close_position = (
                    float(last["close"]) - float(last["low"])
                ) / candle_range
                if close_position < (1.0 - _MIN_CLOSE_PCT):
                    return []

            entry = float(last["close"])
            sl = float(last["lowerband"])
            sl = min(sl, entry * 0.985)  # ensure SL isn't too far
            target = self.calculate_target(entry, sl)
            rr = self.calculate_rr(entry, sl, target)
            confidence = min(100, int(70 + (last["adx"] - 25)))

            signals.append(
                self.format_signal(
                    tradingsymbol,
                    "BUY",
                    confidence,
                    entry,
                    sl,
                    target,
                    rr,
                    f"Supertrend flipped bullish. ADX {last['adx']:.1f}, "
                    f"volume {vol_ratio:.1f}× avg, strong close.",
                    {
                        "adx": round(float(last["adx"]), 1),
                        "vol_ratio": round(vol_ratio, 2),
                        "lowerband": round(float(last["lowerband"]), 2),
                    },
                )
            )

        # ── SELL: Supertrend flipped bearish ───────────────────────────
        elif prev["supertrend"] and not last["supertrend"]:
            if candle_range > 0:
                close_position = (
                    float(last["close"]) - float(last["low"])
                ) / candle_range
                if close_position > _MIN_CLOSE_PCT:
                    return []

            entry = float(last["close"])
            sl = float(last["upperband"])
            sl = max(sl, entry * 1.015)
            target = self.calculate_target(entry, sl)
            rr = self.calculate_rr(entry, sl, target)
            confidence = min(100, int(70 + (last["adx"] - 25)))

            signals.append(
                self.format_signal(
                    tradingsymbol,
                    "SELL",
                    confidence,
                    entry,
                    sl,
                    target,
                    rr,
                    f"Supertrend flipped bearish. ADX {last['adx']:.1f}, "
                    f"volume {vol_ratio:.1f}× avg, strong close.",
                    {
                        "adx": round(float(last["adx"]), 1),
                        "vol_ratio": round(vol_ratio, 2),
                        "upperband": round(float(last["upperband"]), 2),
                    },
                )
            )

        return signals
