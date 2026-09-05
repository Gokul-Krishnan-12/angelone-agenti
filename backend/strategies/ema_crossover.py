"""
EMA Crossover Strategy — calibrated for quality over quantity.

Changes from v1
---------------
• ADX(14) > 20 gate: only trade in directional regimes, not sideways markets.
• Decisive cross check: the EMA gap (fast − slow) must be ≥ 0.05 % of price
  to prevent micro-touches that immediately reverse.
• Volume raised to 1.5× average (from merely > average).
• Stop-loss placed at the slow EMA value (structural level) instead of a flat %.
• Confidence formula updated; base confidence raised to 68.
"""

from typing import Any, Dict, List

import pandas as pd
from ta.trend import ADXIndicator, EMAIndicator

from .base import BaseStrategy

_MIN_GAP_PCT = 0.0005  # 0.05 % decisive-cross threshold
_MIN_VOL_RATIO = 1.5  # volume must be 1.5× the 20-period average


class EMACrossoverStrategy(BaseStrategy):
    def get_name(self) -> str:
        return "EMA Crossover"

    def get_description(self) -> str:
        return (
            "Fast EMA(9) crosses Slow EMA(21) with ADX > 20 regime filter, "
            "decisive gap check, and 1.5× volume confirmation."
        )

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < 30:
            return []

        signals: List[Dict[str, Any]] = []
        df = df.copy()

        # Indicators
        fast_ema = EMAIndicator(close=df["close"], window=9).ema_indicator()
        slow_ema = EMAIndicator(close=df["close"], window=21).ema_indicator()
        vol_sma = df["volume"].rolling(window=20).mean()
        adx = ADXIndicator(
            high=df["high"], low=df["low"], close=df["close"], window=14
        ).adx()

        df["fast_ema"] = fast_ema
        df["slow_ema"] = slow_ema
        df["vol_sma"] = vol_sma
        df["adx"] = adx

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # ── Regime gate ────────────────────────────────────────────────
        if pd.isna(last["adx"]) or last["adx"] < 20:
            return []

        # ── Volume gate ────────────────────────────────────────────────
        vol_ratio = last["volume"] / last["vol_sma"] if last["vol_sma"] > 0 else 1.0
        if vol_ratio < _MIN_VOL_RATIO:
            return []

        # ── BUY: EMA 9 crossed above EMA 21 ───────────────────────────
        if prev["fast_ema"] <= prev["slow_ema"] and last["fast_ema"] > last["slow_ema"]:
            gap = last["fast_ema"] - last["slow_ema"]
            # Decisive-cross: gap must be large enough relative to price
            if gap < last["close"] * _MIN_GAP_PCT:
                return []

            entry = float(last["close"])
            # Structural SL: at the slow EMA (momentum invalidated if price drops below it)
            sl = round(float(last["slow_ema"]) * 0.999, 2)
            sl = min(sl, entry * 0.985)  # cap at -1.5 % if slow EMA is far
            risk = max(entry - sl, entry * 0.003)
            target = round(entry + risk * 2.0, 2)
            rr = self.calculate_rr(entry, sl, target)
            confidence = min(100, int(68 + (vol_ratio - 1.5) * 8))

            signals.append(
                self.format_signal(
                    tradingsymbol,
                    "BUY",
                    confidence,
                    entry,
                    sl,
                    target,
                    rr,
                    f"EMA 9 crossed above EMA 21 decisively (gap {gap:.2f}). "
                    f"Volume {vol_ratio:.2f}×, ADX {last['adx']:.1f}.",
                    {
                        "fast_ema": round(float(last["fast_ema"]), 2),
                        "slow_ema": round(float(last["slow_ema"]), 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "adx": round(float(last["adx"]), 1),
                    },
                )
            )

        # ── SELL: EMA 9 crossed below EMA 21 ──────────────────────────
        elif (
            prev["fast_ema"] >= prev["slow_ema"] and last["fast_ema"] < last["slow_ema"]
        ):
            gap = last["slow_ema"] - last["fast_ema"]
            if gap < last["close"] * _MIN_GAP_PCT:
                return []

            entry = float(last["close"])
            sl = round(float(last["slow_ema"]) * 1.001, 2)
            sl = max(sl, entry * 1.015)
            risk = max(sl - entry, entry * 0.003)
            target = round(entry - risk * 2.0, 2)
            rr = self.calculate_rr(entry, sl, target)
            confidence = min(100, int(68 + (vol_ratio - 1.5) * 8))

            signals.append(
                self.format_signal(
                    tradingsymbol,
                    "SELL",
                    confidence,
                    entry,
                    sl,
                    target,
                    rr,
                    f"EMA 9 crossed below EMA 21 decisively (gap {gap:.2f}). "
                    f"Volume {vol_ratio:.2f}×, ADX {last['adx']:.1f}.",
                    {
                        "fast_ema": round(float(last["fast_ema"]), 2),
                        "slow_ema": round(float(last["slow_ema"]), 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "adx": round(float(last["adx"]), 1),
                    },
                )
            )

        return signals
