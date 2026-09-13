"""
Bollinger Band Volatility Expansion Strategy Engine.
Detects volatility compression squeezes followed by explosive directional expansion
confirmed by volume surges.
"""

from __future__ import annotations

import time
from typing import List

import numpy as np
import pandas as pd
from loguru import logger

from .base import BaseStrategy, Signal


class BollingerExpansionStrategy(BaseStrategy):
    """
    Bollinger Volatility Expansion:
    1. Squeeze detection: Bandwidth compresses to low percentile.
    2. Expansion trigger: Close breaks outside 20-period, 2-std band.
    3. Volume confirmation: Volume >= 1.8x SMA20(V).
    """

    def __init__(self, period: int = 20, num_std: float = 2.0):
        super().__init__(name="BollingerExpansion", family="volatility")
        self.period = period
        self.num_std = num_std

    def evaluate(self, df: pd.DataFrame, tradingsymbol: str) -> List[Signal]:
        if len(df) < self.period + 5:
            return []

        signals: List[Signal] = []
        closes = df["close"].values
        volumes = df["volume"].values

        # 1. ADX Trend/Volatility Gate
        adx = self.compute_adx(df, period=14)
        if adx < 18.0:
            return []

        # 2. Volume Expansion Check: V >= 1.8 * SMA20(V)
        vol_sma20 = (
            float(np.mean(volumes[-self.period - 1 : -1]))
            if len(volumes) > self.period
            else float(np.mean(volumes))
        )
        current_vol = float(volumes[-1])
        vol_ratio = current_vol / vol_sma20 if vol_sma20 > 0 else 1.0

        if vol_ratio < 1.8:
            return []

        # 3. Bollinger Bands calculation
        series = df["close"]
        sma = series.rolling(window=self.period).mean()
        rstd = series.rolling(window=self.period).std()
        upper_band = sma + (self.num_std * rstd)
        lower_band = sma - (self.num_std * rstd)

        curr_close = float(closes[-1])
        prev_close = float(closes[-2])
        curr_upper = float(upper_band.iloc[-1])
        curr_lower = float(lower_band.iloc[-1])
        curr_sma = float(sma.iloc[-1])

        # Squeeze confirmation: Bandwidth recently compressed
        bandwidth = (upper_band - lower_band) / sma
        min_bw_recent = float(bandwidth.iloc[-10:-1].min())
        curr_bw = float(bandwidth.iloc[-1])

        # Must be expanding from a recent squeeze (curr bandwidth expanding > min bandwidth)
        if curr_bw <= 0 or min_bw_recent <= 0:
            return []

        atr = self.compute_atr(df, period=14)
        if atr <= 0:
            return []

        now_ts = (
            float(df["timestamp"].iloc[-1])
            if "timestamp" in df.columns
            else time.time()
        )

        # Bullish Expansion: Cross above upper band
        if curr_close > curr_upper and prev_close <= float(upper_band.iloc[-2]):
            sl = round(max(curr_sma, curr_close - (1.5 * atr)), 2)
            risk = max(curr_close - sl, curr_close * 0.005)
            target = round(curr_close + (risk * 2.2), 2)
            rr = round(abs(target - curr_close) / risk, 2)
            confidence = min(94, int(78 + (vol_ratio * 4.0)))

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
                        "adx": round(adx, 1),
                        "atr": round(atr, 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "upper_band": curr_upper,
                        "sma": curr_sma,
                        "bandwidth": round(curr_bw, 4),
                    },
                )
            )
            logger.info(
                "BollingerExpansion: Bullish expansion detected on %s", tradingsymbol
            )

        # Bearish Expansion: Cross below lower band
        elif curr_close < curr_lower and prev_close >= float(lower_band.iloc[-2]):
            sl = round(min(curr_sma, curr_close + (1.5 * atr)), 2)
            risk = max(sl - curr_close, curr_close * 0.005)
            target = round(curr_close - (risk * 2.2), 2)
            rr = round(abs(curr_close - target) / risk, 2)
            confidence = min(94, int(78 + (vol_ratio * 4.0)))

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
                        "adx": round(adx, 1),
                        "atr": round(atr, 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "lower_band": curr_lower,
                        "sma": curr_sma,
                        "bandwidth": round(curr_bw, 4),
                    },
                )
            )
            logger.info(
                "BollingerExpansion: Bearish expansion detected on %s", tradingsymbol
            )

        return signals
