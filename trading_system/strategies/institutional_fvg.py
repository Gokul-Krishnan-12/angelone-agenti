"""
3-Bar Fair Value Gap (FVG) & Order Block Retest Strategy Engine.
Detects institutional imbalances and enters on retracements to high-volume displacement zones.
"""

from __future__ import annotations

import time
from typing import List

import pandas as pd
from loguru import logger

from .base import BaseStrategy, Signal


class InstitutionalFVGStrategy(BaseStrategy):
    """
    Identifies 3-bar displacement zones where the displacement candle body exceeds
    1.5x ATR, and triggers an order on retracement and rejection of the imbalance midpoint.
    """

    def __init__(self):
        super().__init__(name="InstitutionalFVG", family="structure")

    def evaluate(self, df: pd.DataFrame, tradingsymbol: str) -> List[Signal]:
        if len(df) < 15:
            return []

        signals: List[Signal] = []
        atr = self.compute_atr(df, period=14)
        if atr <= 0:
            return []

        now_ts = (
            float(df["timestamp"].iloc[-1])
            if "timestamp" in df.columns
            else time.time()
        )
        last_bar = df.iloc[-1]
        entry = float(last_bar["close"])

        # Scan the last 4 completed 3-bar windows (c1, c2, c3)
        # With current candle being df.iloc[-1] (testing the gap)
        for offset in range(2, 6):
            if len(df) < offset + 2:
                break

            c1 = df.iloc[-offset - 1]
            disp = df.iloc[-offset]
            c3 = df.iloc[-offset + 1]

            disp_body = abs(float(disp["close"]) - float(disp["open"]))
            # Institutional displacement requirement: body >= 1.5 * ATR
            if disp_body < (1.5 * atr):
                continue

            # ── Bullish FVG: Low(c3) > High(c1) ──────────────────────
            if float(c3["low"]) > float(c1["high"]):
                fvg_low = float(c1["high"])
                fvg_high = float(c3["low"])
                fvg_mid = (fvg_low + fvg_high) / 2.0

                # Retracement trigger: Current candle dips into gap but closes back above midpoint
                if (
                    float(last_bar["low"]) <= fvg_high
                    and float(last_bar["close"]) >= fvg_mid
                    and float(last_bar["close"])
                    > float(last_bar["open"])  # Bullish close
                ):
                    sl = round(fvg_low - (1.0 * atr), 2)
                    risk = max(entry - sl, entry * 0.005)
                    target = round(entry + (risk * 2.2), 2)
                    rr = round(abs(target - entry) / risk, 2)

                    signals.append(
                        Signal(
                            strategy_name=self.name,
                            family=self.family,
                            tradingsymbol=tradingsymbol,
                            direction="BUY",
                            confidence=86,
                            entry_price=entry,
                            stop_loss=sl,
                            target_price=target,
                            risk_reward=rr,
                            timestamp=now_ts,
                            indicators={
                                "atr": round(atr, 2),
                                "fvg_low": fvg_low,
                                "fvg_high": fvg_high,
                                "fvg_mid": round(fvg_mid, 2),
                                "disp_body": round(disp_body, 2),
                            },
                        )
                    )
                    logger.info(
                        "InstitutionalFVG: Bullish FVG retest confirmed on %s",
                        tradingsymbol,
                    )
                    break

            # ── Bearish FVG: High(c3) < Low(c1) ──────────────────────
            elif float(c3["high"]) < float(c1["low"]):
                fvg_high = float(c1["low"])
                fvg_low = float(c3["high"])
                fvg_mid = (fvg_low + fvg_high) / 2.0

                # Retracement trigger: Current candle rises into gap but closes back below midpoint
                if (
                    float(last_bar["high"]) >= fvg_low
                    and float(last_bar["close"]) <= fvg_mid
                    and float(last_bar["close"])
                    < float(last_bar["open"])  # Bearish close
                ):
                    sl = round(fvg_high + (1.0 * atr), 2)
                    risk = max(sl - entry, entry * 0.005)
                    target = round(entry - (risk * 2.2), 2)
                    rr = round(abs(entry - target) / risk, 2)

                    signals.append(
                        Signal(
                            strategy_name=self.name,
                            family=self.family,
                            tradingsymbol=tradingsymbol,
                            direction="SELL",
                            confidence=86,
                            entry_price=entry,
                            stop_loss=sl,
                            target_price=target,
                            risk_reward=rr,
                            timestamp=now_ts,
                            indicators={
                                "atr": round(atr, 2),
                                "fvg_low": fvg_low,
                                "fvg_high": fvg_high,
                                "fvg_mid": round(fvg_mid, 2),
                                "disp_body": round(disp_body, 2),
                            },
                        )
                    )
                    logger.info(
                        "InstitutionalFVG: Bearish FVG retest confirmed on %s",
                        tradingsymbol,
                    )
                    break

        return signals
