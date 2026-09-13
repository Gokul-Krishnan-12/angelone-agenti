"""
Institutional Volume Absorption Strategy Engine.
Detects heavy institutional order absorption via high-volume rejection wicks at key structural inflection zones.
"""

from __future__ import annotations

import time
from typing import List

import numpy as np
import pandas as pd
from loguru import logger

from .base import BaseStrategy, Signal


class InstitutionalAbsorptionStrategy(BaseStrategy):
    """
    Institutional Absorption:
    Identifies high-volume candle wicks where aggressive market orders are absorbed
    by passive institutional limit orders, triggering sharp mean-reversions.
    """

    def __init__(self, vol_multiplier: float = 1.8, min_wick_ratio: float = 0.50):
        super().__init__(name="InstitutionalAbsorption", family="reversal")
        self.vol_multiplier = vol_multiplier
        self.min_wick_ratio = min_wick_ratio

    def evaluate(self, df: pd.DataFrame, tradingsymbol: str) -> List[Signal]:
        if len(df) < 25:
            return []

        signals: List[Signal] = []
        volumes = df["volume"].values
        highs = df["high"].values
        lows = df["low"].values
        opens = df["open"].values
        closes = df["close"].values

        # 1. Volume Surge Check on the signal candle (last bar)
        vol_sma20 = (
            float(np.mean(volumes[-21:-1]))
            if len(volumes) >= 21
            else float(np.mean(volumes))
        )
        current_vol = float(volumes[-1])
        vol_ratio = current_vol / vol_sma20 if vol_sma20 > 0 else 1.0

        if vol_ratio < self.vol_multiplier:
            return []

        # 2. Candle Wick Analysis
        curr_open = float(opens[-1])
        curr_close = float(closes[-1])
        curr_high = float(highs[-1])
        curr_low = float(lows[-1])
        candle_range = curr_high - curr_low

        atr = self.compute_atr(df, period=14)
        if candle_range <= 0 or atr <= 0:
            return []

        body_top = max(curr_open, curr_close)
        body_bottom = min(curr_open, curr_close)
        upper_wick = curr_high - body_top
        lower_wick = body_bottom - curr_low

        now_ts = (
            float(df["timestamp"].iloc[-1])
            if "timestamp" in df.columns
            else time.time()
        )

        # Bullish Absorption: Giant lower rejection wick (sellers absorbed by smart money bids)
        # Lower wick >= 50% of total candle range and close in upper half
        if (lower_wick / candle_range >= self.min_wick_ratio) and (
            curr_close >= (curr_low + 0.45 * candle_range)
        ):
            sl = round(curr_low - (0.5 * atr), 2)
            risk = max(curr_close - sl, curr_close * 0.005)
            target = round(curr_close + (risk * 2.0), 2)
            rr = round(abs(target - curr_close) / risk, 2)
            confidence = min(95, int(80 + (vol_ratio * 4.0)))

            signals.append(
                Signal(
                    strategy_name=self.name,
                    family=self.family,
                    tradingsymbol=tradingsymbol,
                    direction="BUY",
                    confidence=confidence,
                    entry_price=curr_close,
                    stop_loss=sl,
                    target_price=target,
                    risk_reward=rr,
                    timestamp=now_ts,
                    indicators={
                        "atr": round(atr, 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "wick_ratio": round(lower_wick / candle_range, 2),
                        "candle_low": curr_low,
                    },
                )
            )
            logger.info(
                "InstitutionalAbsorption: Bullish absorption detected on %s",
                tradingsymbol,
            )

        # Bearish Absorption: Giant upper rejection wick (buyers absorbed by smart money asks)
        # Upper wick >= 50% of total candle range and close in lower half
        elif (upper_wick / candle_range >= self.min_wick_ratio) and (
            curr_close <= (curr_high - 0.45 * candle_range)
        ):
            sl = round(curr_high + (0.5 * atr), 2)
            risk = max(sl - curr_close, curr_close * 0.005)
            target = round(curr_close - (risk * 2.0), 2)
            rr = round(abs(curr_close - target) / risk, 2)
            confidence = min(95, int(80 + (vol_ratio * 4.0)))

            signals.append(
                Signal(
                    strategy_name=self.name,
                    family=self.family,
                    tradingsymbol=tradingsymbol,
                    direction="SELL",
                    confidence=confidence,
                    entry_price=curr_close,
                    stop_loss=sl,
                    target_price=target,
                    risk_reward=rr,
                    timestamp=now_ts,
                    indicators={
                        "atr": round(atr, 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "wick_ratio": round(upper_wick / candle_range, 2),
                        "candle_high": curr_high,
                    },
                )
            )
            logger.info(
                "InstitutionalAbsorption: Bearish absorption detected on %s",
                tradingsymbol,
            )

        return signals
