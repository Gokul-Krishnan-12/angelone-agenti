"""
VWAP Bounce Strategy — tighter proximity, delta confirmation.

Changes from v1
---------------
• VWAP proximity tightened from 0.2 % to 0.15 % to avoid trading on
  candles that merely had the VWAP somewhere in their range.
• Previous candle must also have been near VWAP (≤ 0.3 % away), confirming
  the level is being actively defended (two-touch confirmation).
• Per-candle delta confirmation: buying pressure must outweigh selling on the
  signal candle (for BUY) and vice versa for SELL.
• Volume ≥ 1.2 × average (active participation at VWAP).
• ATR-calibrated SL instead of flat %.
"""

from typing import Any, Dict, List

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volume import VolumeWeightedAveragePrice

from .base import BaseStrategy
from .utils import compute_delta

_PROXIMITY_PCT = 0.0015  # current bar within 0.15 % of VWAP
_PREV_PROXIMITY_PCT = 0.003  # previous bar within 0.3 % of VWAP (two-touch)
_MIN_VOL_RATIO = 1.2  # minimum relative volume at the VWAP touch


class VWAPBounceStrategy(BaseStrategy):
    def get_name(self) -> str:
        return "VWAP Bounce"

    def get_description(self) -> str:
        return (
            "Price bounces from VWAP with trend alignment, delta confirmation, "
            "two-touch validation, and ATR-calibrated stop-loss."
        )

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < 30:
            return []

        signals: List[Dict[str, Any]] = []
        df = df.copy()

        vwap = VolumeWeightedAveragePrice(
            high=df["high"], low=df["low"], close=df["close"], volume=df["volume"]
        ).volume_weighted_average_price()

        rsi = RSIIndicator(close=df["close"], window=14).rsi()
        fast_ema = EMAIndicator(close=df["close"], window=9).ema_indicator()
        slow_ema = EMAIndicator(close=df["close"], window=21).ema_indicator()
        vol_sma = df["volume"].rolling(window=20).mean()
        delta = compute_delta(df)

        df["vwap"] = vwap
        df["rsi"] = rsi
        df["fast_ema"] = fast_ema
        df["slow_ema"] = slow_ema
        df["vol_sma"] = vol_sma
        df["delta"] = delta

        last = df.iloc[-1]
        prev = df.iloc[-2]

        last_vwap = float(last["vwap"])
        if last_vwap <= 0:
            return []

        # ── Proximity check ────────────────────────────────────────────
        dist_to_vwap = abs(float(last["close"]) - last_vwap) / last_vwap
        if dist_to_vwap > _PROXIMITY_PCT:
            return []

        # ── Two-touch: previous bar also near VWAP ─────────────────────
        prev_dist = abs(float(prev["close"]) - last_vwap) / last_vwap
        if prev_dist > _PREV_PROXIMITY_PCT:
            return []

        # ── Volume gate ────────────────────────────────────────────────
        vol_ratio = (
            float(last["volume"]) / float(last["vol_sma"])
            if last["vol_sma"] > 0
            else 1.0
        )
        if vol_ratio < _MIN_VOL_RATIO:
            return []

        entry = float(last["close"])
        current_delta = float(last["delta"])

        # ── BUY ────────────────────────────────────────────────────────
        if (
            last["close"] > last["open"]  # bullish candle
            and last["rsi"] > 40  # not deeply oversold (trend intact)
            and last["fast_ema"] > last["slow_ema"]  # uptrend
            and last["close"] >= last_vwap  # above VWAP
            and current_delta > 0  # net buying pressure
        ):
            sl = self.calculate_atr_stop_loss(df, entry, "BUY", multiplier=1.2)
            risk = max(entry - sl, entry * 0.003)
            target = round(entry + risk * 2.0, 2)
            rr = self.calculate_rr(entry, sl, target)

            signals.append(
                self.format_signal(
                    tradingsymbol,
                    "BUY",
                    82,
                    entry,
                    sl,
                    target,
                    rr,
                    f"Bullish VWAP bounce (two-touch). Delta positive ({current_delta:.0f}), "
                    f"RSI {last['rsi']:.0f}, volume {vol_ratio:.1f}×.",
                    {
                        "vwap": round(last_vwap, 2),
                        "rsi": round(float(last["rsi"]), 1),
                        "delta": round(current_delta, 0),
                        "vol_ratio": round(vol_ratio, 2),
                    },
                )
            )

        # ── SELL ───────────────────────────────────────────────────────
        elif (
            last["close"] < last["open"]
            and last["rsi"] < 60
            and last["fast_ema"] < last["slow_ema"]
            and last["close"] <= last_vwap
            and current_delta < 0
        ):
            sl = self.calculate_atr_stop_loss(df, entry, "SELL", multiplier=1.2)
            risk = max(sl - entry, entry * 0.003)
            target = round(entry - risk * 2.0, 2)
            rr = self.calculate_rr(entry, sl, target)

            signals.append(
                self.format_signal(
                    tradingsymbol,
                    "SELL",
                    82,
                    entry,
                    sl,
                    target,
                    rr,
                    f"Bearish VWAP rejection (two-touch). Delta negative ({current_delta:.0f}), "
                    f"RSI {last['rsi']:.0f}, volume {vol_ratio:.1f}×.",
                    {
                        "vwap": round(last_vwap, 2),
                        "rsi": round(float(last["rsi"]), 1),
                        "delta": round(current_delta, 0),
                        "vol_ratio": round(vol_ratio, 2),
                    },
                )
            )

        return signals
