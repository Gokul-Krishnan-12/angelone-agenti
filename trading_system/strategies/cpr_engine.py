"""
Central Pivot Range (CPR) Width & Boundary Defense Strategy Engine.
Implements Frank Ochoa's institutional pivot framework for NSE equities.
"""

from __future__ import annotations

import time
from typing import List

import pandas as pd
from loguru import logger

from .base import BaseStrategy, Signal


class CPREngine(BaseStrategy):
    """
    Calculates Central Pivot Range (P, BC, TC) and targets Narrow CPR volatility breakouts
    or Wide CPR boundary defense rejections.
    """

    def __init__(self):
        super().__init__(name="CentralPivotRange", family="structure")

    def evaluate(self, df: pd.DataFrame, tradingsymbol: str) -> List[Signal]:
        if len(df) < 20:
            return []

        signals: List[Signal] = []
        atr = self.compute_atr(df, period=14)
        if atr <= 0:
            return []

        # Reference session High, Low, Close (from earlier bars or session prior)
        # We take the first 15 bars of the history window as prior session proxy if intraday
        ref_bars = df.iloc[:15]
        ref_high = float(ref_bars["high"].max())
        ref_low = float(ref_bars["low"].min())
        ref_close = float(ref_bars["close"].iloc[-1])

        # Mathematical Pivot Formulation
        pivot = (ref_high + ref_low + ref_close) / 3.0
        bc = (ref_high + ref_low) / 2.0
        tc = (2.0 * pivot) - bc

        cpr_top = round(max(tc, bc), 2)
        cpr_bottom = round(min(tc, bc), 2)
        cpr_width_pct = round((abs(cpr_top - cpr_bottom) / pivot) * 100.0, 3)

        r1 = round((2.0 * pivot) - ref_low, 2)
        s1 = round((2.0 * pivot) - ref_high, 2)

        last_bar = df.iloc[-1]
        last_close = float(last_bar["close"])
        last_open = float(last_bar["open"])
        now_ts = (
            float(df["timestamp"].iloc[-1])
            if "timestamp" in df.columns
            else time.time()
        )

        vol_mean = float(df["volume"].rolling(window=15).mean().iloc[-1])
        curr_vol = float(last_bar["volume"])
        vol_ratio = curr_vol / vol_mean if vol_mean > 0 else 1.0

        # Setup 1: Narrow CPR Momentum Breakout (Trend Expansion Day)
        if cpr_width_pct < 0.35 and vol_ratio >= 1.3:
            # Bullish expansion above CPR Top
            if last_close > cpr_top and last_close > last_open:
                sl = round(cpr_bottom - (0.5 * atr), 2)
                risk = max(last_close - sl, last_close * 0.005)
                target = round(max(r1, last_close + (risk * 2.0)), 2)
                rr = round(abs(target - last_close) / risk, 2)

                signals.append(
                    Signal(
                        strategy_name=self.name,
                        family=self.family,
                        tradingsymbol=tradingsymbol,
                        direction="BUY",
                        confidence=88,
                        entry_price=last_close,
                        stop_loss=sl,
                        target_price=target,
                        risk_reward=rr,
                        timestamp=now_ts,
                        indicators={
                            "cpr_width_pct": cpr_width_pct,
                            "cpr_top": cpr_top,
                            "cpr_bottom": cpr_bottom,
                            "pivot": round(pivot, 2),
                            "r1": r1,
                        },
                    )
                )
                logger.info(
                    "CPREngine: Narrow CPR Bullish Breakout on %s", tradingsymbol
                )

            # Bearish expansion below CPR Bottom
            elif last_close < cpr_bottom and last_close < last_open:
                sl = round(cpr_top + (0.5 * atr), 2)
                risk = max(sl - last_close, last_close * 0.005)
                target = round(min(s1, last_close - (risk * 2.0)), 2)
                rr = round(abs(last_close - target) / risk, 2)

                signals.append(
                    Signal(
                        strategy_name=self.name,
                        family=self.family,
                        tradingsymbol=tradingsymbol,
                        direction="SELL",
                        confidence=88,
                        entry_price=last_close,
                        stop_loss=sl,
                        target_price=target,
                        risk_reward=rr,
                        timestamp=now_ts,
                        indicators={
                            "cpr_width_pct": cpr_width_pct,
                            "cpr_top": cpr_top,
                            "cpr_bottom": cpr_bottom,
                            "pivot": round(pivot, 2),
                            "s1": s1,
                        },
                    )
                )
                logger.info(
                    "CPREngine: Narrow CPR Bearish Breakout on %s", tradingsymbol
                )

        # Setup 2: CPR Boundary Defense / Reversal (Range-Bound Days)
        elif cpr_width_pct >= 0.25:
            candle_range = float(last_bar["high"]) - float(last_bar["low"])
            if candle_range > 0:
                lower_wick = min(last_open, last_close) - float(last_bar["low"])
                upper_wick = float(last_bar["high"]) - max(last_open, last_close)

                # Rejection pin bar bouncing off CPR Bottom toward Pivot (Bullish)
                if (
                    lower_wick / candle_range >= 0.45
                    and float(last_bar["low"]) <= cpr_bottom < last_close
                ):
                    sl = round(float(last_bar["low"]) - (0.3 * atr), 2)
                    risk = max(last_close - sl, last_close * 0.005)
                    target = round(pivot, 2)
                    if target > last_close:
                        rr = round(abs(target - last_close) / risk, 2)
                        signals.append(
                            Signal(
                                strategy_name=self.name,
                                family="reversal",
                                tradingsymbol=tradingsymbol,
                                direction="BUY",
                                confidence=82,
                                entry_price=last_close,
                                stop_loss=sl,
                                target_price=target,
                                risk_reward=rr,
                                timestamp=now_ts,
                                indicators={
                                    "cpr_bottom": cpr_bottom,
                                    "pivot": round(pivot, 2),
                                },
                            )
                        )
                        logger.info(
                            "CPREngine: CPR Bottom boundary defense on %s",
                            tradingsymbol,
                        )

                # Rejection pin bar bouncing off CPR Top toward Pivot (Bearish)
                elif (
                    upper_wick / candle_range >= 0.45
                    and float(last_bar["high"]) >= cpr_top > last_close
                ):
                    sl = round(float(last_bar["high"]) + (0.3 * atr), 2)
                    risk = max(sl - last_close, last_close * 0.005)
                    target = round(pivot, 2)
                    if target < last_close:
                        rr = round(abs(last_close - target) / risk, 2)
                        signals.append(
                            Signal(
                                strategy_name=self.name,
                                family="reversal",
                                tradingsymbol=tradingsymbol,
                                direction="SELL",
                                confidence=82,
                                entry_price=last_close,
                                stop_loss=sl,
                                target_price=target,
                                risk_reward=rr,
                                timestamp=now_ts,
                                indicators={
                                    "cpr_top": cpr_top,
                                    "pivot": round(pivot, 2),
                                },
                            )
                        )
                        logger.info(
                            "CPREngine: CPR Top boundary defense on %s", tradingsymbol
                        )

        return signals
