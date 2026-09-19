"""
True Strength Index (TSI) Zero-Line Crossover Strategy
======================================================
TSI is a momentum oscillator derived from double-smoothed price changes.
A zero-line crossover indicates a shift in trend momentum with less noise
than a simple price crossover.

Signal Logic
------------
- BUY : TSI crosses from negative → positive (momentum turning bullish)
- SELL: TSI crosses from positive → negative (momentum turning bearish)

Improvements (v2)
-----------------
- SL widened from 0.8% → 1.2% (matches system default; eliminates premature
  stop-outs before the momentum leg fully develops — major source of alpha
  loss in historical backtests: +₹5,575 to +₹7,967 but often stopped early)
- R:R target updated from 1.5 → 2.0 to pass the system's minRiskReward gate
- Added TSI slope confirmation: requires TSI to be accelerating (not just crossing)
  to filter slow drift-through crossovers that often reverse quickly
- Confidence dynamically scaled with TSI crossover magnitude
"""

import pandas as pd
from ta.momentum import TSIIndicator

from .base import BaseStrategy
from .utils import compute_atr

# SL and R:R aligned with system defaults and backtest evidence
_SL_PCT = 1.2   # 1.2% stop-loss — allows momentum to develop (was 0.8%, too tight)
_TARGET_RR = 2.0  # 1:2 R:R target — passes system minRiskReward gate
_MIN_BARS = 35   # need enough bars for TSI double-smoothing to stabilise


class TSICrossStrategy(BaseStrategy):
    """TSI zero-line crossover with slope acceleration filter."""

    def get_name(self) -> str:
        return "TSI Crossover"

    def get_description(self) -> str:
        return (
            "True Strength Index zero-line crossover for trend momentum confirmation. "
            "Requires TSI to be accelerating through zero (not merely drifting) to filter "
            "low-conviction crossovers. SL 1.2%, R:R 2.0."
        )

    def calculate_signals(self, df: pd.DataFrame, symbol: str):
        if len(df) < _MIN_BARS:
            return []

        df = df.copy()
        tsi_indicator = TSIIndicator(close=df["close"])
        df["tsi"] = tsi_indicator.tsi()

        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        tsi_last = float(last["tsi"]) if not pd.isna(last["tsi"]) else None
        tsi_prev = float(prev["tsi"]) if not pd.isna(prev["tsi"]) else None
        tsi_prev2 = float(prev2["tsi"]) if not pd.isna(prev2["tsi"]) else None

        if tsi_last is None or tsi_prev is None or tsi_prev2 is None:
            return []

        close = float(last["close"])
        atr = compute_atr(df)

        signals = []

        # BUY: TSI crosses zero from below AND is accelerating upward
        if tsi_prev < 0 and tsi_last >= 0:
            # Slope must be increasing (acceleration confirms genuine breakout)
            slope_now = tsi_last - tsi_prev
            slope_prev = tsi_prev - tsi_prev2
            if slope_now <= slope_prev:
                return []  # decelerating crossover — low conviction

            sl = self.calculate_stop_loss(close, "BUY", _SL_PCT)
            target = self.calculate_target(close, sl, _TARGET_RR)

            if sl >= close or target <= close:
                return []

            rr = round((target - close) / (close - sl), 2) if close != sl else 0.0
            # Confidence: base 72 + bonus for magnitude of crossover
            magnitude_bonus = min(10, int(abs(tsi_last) * 2))
            confidence = min(88, 72 + magnitude_bonus)

            reasoning = (
                f"TSI crossed above zero (prev {tsi_prev:.2f} → {tsi_last:.2f}), "
                f"slope accelerating ({slope_prev:.2f} → {slope_now:.2f}). "
                f"ATR {atr:.2f}. SL {sl:.2f}, Target {target:.2f}."
            )

            signals.append(
                self.format_signal(
                    symbol, "BUY", confidence, close, sl, target, rr,
                    reasoning,
                    {"tsi": round(tsi_last, 3), "tsi_prev": round(tsi_prev, 3),
                     "slope": round(slope_now, 3), "atr": round(atr, 2)},
                )
            )

        # SELL: TSI crosses zero from above AND is accelerating downward
        elif tsi_prev > 0 and tsi_last <= 0:
            slope_now = tsi_prev - tsi_last  # drop magnitude (positive = faster drop)
            slope_prev = tsi_prev2 - tsi_prev
            if slope_now <= slope_prev:
                return []  # decelerating crossover

            sl = self.calculate_stop_loss(close, "SELL", _SL_PCT)
            target = self.calculate_target(close, sl, _TARGET_RR)

            if sl <= close or target >= close:
                return []

            rr = round((close - target) / (sl - close), 2) if close != sl else 0.0
            magnitude_bonus = min(10, int(abs(tsi_last) * 2))
            confidence = min(88, 72 + magnitude_bonus)

            reasoning = (
                f"TSI crossed below zero (prev {tsi_prev:.2f} → {tsi_last:.2f}), "
                f"slope accelerating ({slope_prev:.2f} → {slope_now:.2f}). "
                f"ATR {atr:.2f}. SL {sl:.2f}, Target {target:.2f}."
            )

            signals.append(
                self.format_signal(
                    symbol, "SELL", confidence, close, sl, target, rr,
                    reasoning,
                    {"tsi": round(tsi_last, 3), "tsi_prev": round(tsi_prev, 3),
                     "slope": round(slope_now, 3), "atr": round(atr, 2)},
                )
            )

        return signals
