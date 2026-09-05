"""
Volume Delta Divergence Strategy — Institutional Footprint Detector.

Detects institutional accumulation / distribution by identifying divergence
between price direction and cumulative volume delta (buying minus selling
pressure), confirmed by at least one high-volume candle in the pattern.

Bullish Divergence
  Price makes lower lows over a lookback window, but the rolling cumulative
  delta is rising — institutions are absorbing the down move (accumulation).

Bearish Divergence
  Price makes higher highs, but cumulative delta is falling — institutions
  are distributing into the rally.

Entry Criteria (BUY):
  • Bullish delta divergence confirmed over 10-bar lookback.
  • At least one candle in the window has volume ≥ 1.8 × 20-period average.
  • Current (confirming) candle is bullish (close > open).
  • Market regime is NOT 'volatile' (ADX must be ≥ 18).
  • Stop-loss: 0.5 × ATR below the swing low in the window.
  • Target: 2.2 × risk (risk = entry − SL).
  • Confidence: 82–92 % (scales with institutional volume ratio).
"""

from typing import Any, Dict, List

import pandas as pd

from .base import BaseStrategy
from .utils import (
    compute_atr,
    compute_cumulative_delta,
    compute_regime,
)


class VolumeDeltaDivergenceStrategy(BaseStrategy):
    def get_name(self) -> str:
        return "Volume Delta Divergence"

    def get_description(self) -> str:
        return (
            "Detects institutional accumulation / distribution by identifying divergence "
            "between price direction and cumulative volume delta. "
            "Bullish: price lows declining while buying pressure rises. "
            "Bearish: price highs rising while selling pressure rises."
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_divergence(
        self, df: pd.DataFrame, lookback: int = 10
    ) -> tuple[str, float, float, float]:
        """
        Scan the last ``lookback`` bars for price–delta divergence.

        Returns
        -------
        (direction, swing_high, swing_low, max_vol_ratio)
        direction is 'BUY', 'SELL', or 'none'.
        """
        if len(df) < lookback + 15:
            return ("none", 0.0, 0.0, 1.0)

        # Cumulative delta series (rolling 20-bar)
        cum_delta = compute_cumulative_delta(df, window=20)

        # Slice the window (exclude last bar — that is the confirming candle)
        window_df = df.iloc[-(lookback + 1) : -1]
        window_delta = cum_delta.iloc[-(lookback + 1) : -1]

        if len(window_df) < 4:
            return ("none", 0.0, 0.0, 1.0)

        half = len(window_df) // 2
        lows = window_df["low"].values
        highs = window_df["high"].values
        delta_vals = window_delta.values

        price_low_first = float(min(lows[:half]))
        price_low_second = float(min(lows[half:]))
        price_high_first = float(max(highs[:half]))
        price_high_second = float(max(highs[half:]))

        delta_first = (
            float(delta_vals[half - 1]) if not pd.isna(delta_vals[half - 1]) else 0.0
        )
        delta_last = float(delta_vals[-1]) if not pd.isna(delta_vals[-1]) else 0.0

        swing_low = float(min(lows))
        swing_high = float(max(highs))

        # Highest relative volume in the window (institutional candle check)
        vol_avg = df["volume"].rolling(window=20).mean().iloc[-1]
        max_vol_in_window = float(window_df["volume"].max())
        vol_ratio = max_vol_in_window / vol_avg if vol_avg > 0 else 1.0

        # ── Bullish Divergence ──────────────────────────────────────────
        # Lower low in price but higher (or rising) cumulative delta
        if (
            price_low_second < price_low_first * 0.9985  # meaningful lower low (>0.15%)
            and delta_last > delta_first * 1.04  # rising delta (≥4% more net buying)
            and vol_ratio >= 1.8  # at least one institutional-sized candle
        ):
            return ("BUY", swing_high, swing_low, vol_ratio)

        # ── Bearish Divergence ──────────────────────────────────────────
        # Higher high in price but lower (falling) cumulative delta
        if (
            price_high_second > price_high_first * 1.0015  # meaningful higher high
            and delta_last < delta_first * 0.96  # falling delta (≥4% more net selling)
            and vol_ratio >= 1.8
        ):
            return ("SELL", swing_high, swing_low, vol_ratio)

        return ("none", swing_high, swing_low, vol_ratio)

    # ------------------------------------------------------------------
    # Main signal calculation
    # ------------------------------------------------------------------

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < 40:
            return []

        df = df.copy()

        # ── Regime filter ──────────────────────────────────────────────
        regime = compute_regime(df)
        if regime == "volatile":
            return []

        # ── Divergence scan ────────────────────────────────────────────
        direction, swing_high, swing_low, vol_ratio = self._find_divergence(
            df, lookback=10
        )
        if direction == "none":
            return []

        last = df.iloc[-1]
        entry = float(last["close"])
        atr = compute_atr(df)

        signals: List[Dict[str, Any]] = []

        # ── BUY setup ─────────────────────────────────────────────────
        if direction == "BUY":
            # Confirming candle must be bullish
            if last["close"] <= last["open"]:
                return []
            # Also require confirming candle close above its own midpoint
            candle_mid = (last["high"] + last["low"]) / 2.0
            if last["close"] < candle_mid:
                return []

            # SL: 0.5 × ATR below swing low; floor at -3 % of entry
            sl = round(max(swing_low - atr * 0.5, entry * 0.97), 2)
            risk = max(entry - sl, entry * 0.003)
            target = round(entry + risk * 2.2, 2)
            rr = self.calculate_rr(entry, sl, target)

            confidence = min(92, int(82 + (vol_ratio - 1.8) * 5))

            signals.append(
                self.format_signal(
                    tradingsymbol=tradingsymbol,
                    direction="BUY",
                    confidence=confidence,
                    entry=entry,
                    sl=sl,
                    target=target,
                    rr=rr,
                    reasoning=(
                        f"Bullish volume delta divergence: price made lower lows but "
                        f"net buying pressure (cumulative delta) rose. "
                        f"Institutional volume detected at {vol_ratio:.1f}× average "
                        f"within the divergence window. Regime: {regime}."
                    ),
                    indicators={
                        "vol_ratio": round(vol_ratio, 2),
                        "swing_low": round(swing_low, 2),
                        "atr": round(atr, 2),
                        "regime": regime,
                    },
                )
            )

        # ── SELL setup ────────────────────────────────────────────────
        elif direction == "SELL":
            # Confirming candle must be bearish
            if last["close"] >= last["open"]:
                return []
            candle_mid = (last["high"] + last["low"]) / 2.0
            if last["close"] > candle_mid:
                return []

            # SL: 0.5 × ATR above swing high; cap at +3 % of entry
            sl = round(min(swing_high + atr * 0.5, entry * 1.03), 2)
            risk = max(sl - entry, entry * 0.003)
            target = round(entry - risk * 2.2, 2)
            rr = self.calculate_rr(entry, sl, target)

            confidence = min(92, int(82 + (vol_ratio - 1.8) * 5))

            signals.append(
                self.format_signal(
                    tradingsymbol=tradingsymbol,
                    direction="SELL",
                    confidence=confidence,
                    entry=entry,
                    sl=sl,
                    target=target,
                    rr=rr,
                    reasoning=(
                        f"Bearish volume delta divergence: price made higher highs but "
                        f"net selling pressure (cumulative delta) rose. "
                        f"Institutional volume detected at {vol_ratio:.1f}× average "
                        f"within the divergence window. Regime: {regime}."
                    ),
                    indicators={
                        "vol_ratio": round(vol_ratio, 2),
                        "swing_high": round(swing_high, 2),
                        "atr": round(atr, 2),
                        "regime": regime,
                    },
                )
            )

        return signals
