"""
Donchian & Keltner Channel Volatility Breakout Strategy Engine.
Triggers high-momentum breakouts confirmed by institutional volume surges.
"""

from __future__ import annotations

import time
from typing import List

import numpy as np
import pandas as pd
from loguru import logger

from .base import BaseStrategy, Signal


class BreakoutEngine(BaseStrategy):
    """
    Evaluates 20-period Donchian and Keltner volatility channel breakouts.
    Requires volume expansion (>= 1.8x SMA20) and ADX >= 18 trend confirmation.
    """

    def __init__(self):
        super().__init__(name="ChannelBreakout", family="breakout")

    def evaluate(self, df: pd.DataFrame, tradingsymbol: str) -> List[Signal]:
        if len(df) < 25:
            return []

        signals: List[Signal] = []
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        volumes = df["volume"].values

        # 1. ADX Volatility Regime Gate (Suppress breakouts in choppy markets)
        adx = self.compute_adx(df, period=14)
        if adx < 18.0:
            return []

        # 2. Volume Surge Check: V >= 1.8 * SMA20(V)
        vol_sma20 = (
            float(np.mean(volumes[-21:-1]))
            if len(volumes) >= 21
            else float(np.mean(volumes))
        )
        current_vol = float(volumes[-1])
        vol_ratio = current_vol / vol_sma20 if vol_sma20 > 0 else 1.0

        if vol_ratio < 1.8:
            return []

        # 3. Keltner Channel & Donchian Levels
        atr = self.compute_atr(df, period=14)
        if atr <= 0:
            return []

        # 20 EMA
        ema20 = float(df["close"].ewm(span=20, adjust=False).mean().iloc[-1])
        keltner_upper = round(ema20 + (1.5 * atr), 2)
        keltner_lower = round(ema20 - (1.5 * atr), 2)

        # 20-period Donchian Channel (prior 20 bars excluding current)
        donchian_high = float(np.max(highs[-21:-1]))
        donchian_low = float(np.min(lows[-21:-1]))

        last_close = float(closes[-1])
        now_ts = (
            float(df["timestamp"].iloc[-1])
            if "timestamp" in df.columns
            else time.time()
        )

        # Bullish Breakout: Close above both Donchian High and Keltner Upper Band
        if last_close > donchian_high and last_close >= keltner_upper:
            sl = round(max(ema20, last_close - (1.5 * atr)), 2)
            risk = max(last_close - sl, last_close * 0.005)
            target = round(last_close + (risk * 2.0), 2)
            rr = round(abs(target - last_close) / risk, 2)
            confidence = min(92, int(75 + (vol_ratio * 4.0)))

            signals.append(
                Signal(
                    strategy_name=self.name,
                    family=self.family,
                    tradingsymbol=tradingsymbol,
                    direction="BUY",
                    confidence=confidence,
                    entry_price=last_close,
                    stop_loss=sl,
                    target_price=target,
                    risk_reward=rr,
                    timestamp=now_ts,
                    indicators={
                        "adx": round(adx, 1),
                        "atr": round(atr, 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "keltner_upper": keltner_upper,
                        "donchian_high": donchian_high,
                    },
                )
            )
            logger.info(
                "BreakoutEngine: Bullish channel breakout detected on %s", tradingsymbol
            )

        # Bearish Breakout: Close below both Donchian Low and Keltner Lower Band
        elif last_close < donchian_low and last_close <= keltner_lower:
            sl = round(min(ema20, last_close + (1.5 * atr)), 2)
            risk = max(sl - last_close, last_close * 0.005)
            target = round(last_close - (risk * 2.0), 2)
            rr = round(abs(last_close - target) / risk, 2)
            confidence = min(92, int(75 + (vol_ratio * 4.0)))

            signals.append(
                Signal(
                    strategy_name=self.name,
                    family=self.family,
                    tradingsymbol=tradingsymbol,
                    direction="SELL",
                    confidence=confidence,
                    entry_price=last_close,
                    stop_loss=sl,
                    target_price=target,
                    risk_reward=rr,
                    timestamp=now_ts,
                    indicators={
                        "adx": round(adx, 1),
                        "atr": round(atr, 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "keltner_lower": keltner_lower,
                        "donchian_low": donchian_low,
                    },
                )
            )
            logger.info(
                "BreakoutEngine: Bearish channel breakout detected on %s", tradingsymbol
            )

        return signals
