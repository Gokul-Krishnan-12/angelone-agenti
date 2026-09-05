"""
Institutional Absorption Strategy — upgraded to multi-candle confirmation.

Logic Change (v2)
-----------------
The original strategy fired on the *current* candle alone, which meant any
single-candle spike — including stop-hunt wicks — triggered a signal.

The upgraded version scans the last 3 completed bars (excluding the current
bar) for an absorption candle (high volume + significant rejection wick),
then requires the current bar to *confirm* the absorption by closing in the
direction the institutions absorbed into.

Additional gates:
  • ADX(14) > 20 — only trade during directional regimes, not choppy ranges.
  • Absorption candle volume ≥ 2.5 × 20-period average (raised from 2.0).
  • Rejection wick ≥ 45 % of the absorption candle's range (unchanged).
  • Confirming candle must close in the top (BUY) / bottom (SELL) 35 % of
    the absorption candle's range.
  • ATR-calibrated SL instead of a fixed 0.1 % offset.
  • Confidence scales with vol ratio; cap raised to 92.
"""

from typing import Any, Dict, List

import pandas as pd
from ta.trend import ADXIndicator

from .base import BaseStrategy
from .utils import compute_atr


class InstitutionalAbsorptionStrategy(BaseStrategy):
    def get_name(self) -> str:
        return "Institutional Absorption"

    def get_description(self) -> str:
        return (
            "Detects multi-candle institutional absorption where ultra-high volume "
            "prints a strong rejection wick, confirmed by a subsequent candle closing "
            "in the direction of institutional interest."
        )

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < 30:
            return []

        df = df.copy()

        # ── Regime gate (ADX > 20) ─────────────────────────────────────
        adx_val = (
            ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
            .adx()
            .iloc[-1]
        )
        if pd.isna(adx_val) or adx_val < 20:
            return []

        # ── Volume average ─────────────────────────────────────────────
        vol_sma = df["volume"].rolling(window=20).mean()
        avg_vol = vol_sma.iloc[-1]
        if pd.isna(avg_vol) or avg_vol <= 0:
            return []

        last = df.iloc[-1]
        atr = compute_atr(df)

        # ── Scan last 3 completed bars for an absorption candle ────────
        # Indices relative to end: -2 = bar before last, -3 = 2 bars ago, -4 = 3 bars ago
        absorption_candle = None
        absorption_direction: str = ""
        abs_vol_ratio = 0.0

        for offset in range(1, 4):  # offsets 1, 2, 3 → df.iloc[-2], [-3], [-4]
            idx = -(offset + 1)
            if abs(idx) > len(df):
                break

            candle = df.iloc[idx]
            candle_vol_avg = vol_sma.iloc[idx]
            if pd.isna(candle_vol_avg) or candle_vol_avg <= 0:
                continue

            vol_ratio = float(candle["volume"]) / float(candle_vol_avg)
            if vol_ratio < 2.5:  # raised threshold
                continue

            candle_range = float(candle["high"]) - float(candle["low"])
            if candle_range <= 0:
                continue

            lower_wick = float(min(candle["open"], candle["close"])) - float(
                candle["low"]
            )
            upper_wick = float(candle["high"]) - float(
                max(candle["open"], candle["close"])
            )

            if lower_wick / candle_range >= 0.45:
                absorption_candle = candle
                absorption_direction = "BUY"
                abs_vol_ratio = vol_ratio
                break

            if upper_wick / candle_range >= 0.45:
                absorption_candle = candle
                absorption_direction = "SELL"
                abs_vol_ratio = vol_ratio
                break

        if absorption_candle is None:
            return []

        # ── Confirming candle validation ───────────────────────────────
        abs_range = float(absorption_candle["high"]) - float(absorption_candle["low"])
        entry = float(last["close"])
        signals: List[Dict[str, Any]] = []

        if absorption_direction == "BUY":
            # Confirming candle: bullish close in top 35 % of absorption range
            top_35pct = float(absorption_candle["low"]) + abs_range * 0.65
            if last["close"] <= last["open"]:
                return []
            if entry < top_35pct:
                return []

            # ATR-calibrated SL below the absorption candle's low
            sl = round(float(absorption_candle["low"]) - atr * 0.3, 2)
            risk = max(entry - sl, entry * 0.003)
            target = round(entry + risk * 2.0, 2)
            rr = self.calculate_rr(entry, sl, target)
            confidence = min(92, int(80 + (abs_vol_ratio - 2.0) * 4))

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
                        f"Multi-candle institutional buying absorption confirmed: "
                        f"Absorption candle had {abs_vol_ratio:.1f}× avg volume with "
                        f"a {(lower_wick := float(min(absorption_candle['open'], absorption_candle['close'])) - float(absorption_candle['low'])) and round(lower_wick / abs_range * 100, 0):.0f}% "
                        f"lower rejection wick. Current bar confirms bullish follow-through. ADX: {adx_val:.1f}."
                    ),
                    indicators={
                        "vol_ratio": round(abs_vol_ratio, 2),
                        "adx": round(adx_val, 1),
                        "atr": round(atr, 2),
                        "absorption_low": round(float(absorption_candle["low"]), 2),
                    },
                )
            )

        elif absorption_direction == "SELL":
            # Confirming candle: bearish close in bottom 35 % of absorption range
            bottom_35pct = float(absorption_candle["high"]) - abs_range * 0.65
            if last["close"] >= last["open"]:
                return []
            if entry > bottom_35pct:
                return []

            sl = round(float(absorption_candle["high"]) + atr * 0.3, 2)
            risk = max(sl - entry, entry * 0.003)
            target = round(entry - risk * 2.0, 2)
            rr = self.calculate_rr(entry, sl, target)
            confidence = min(92, int(80 + (abs_vol_ratio - 2.0) * 4))

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
                        f"Multi-candle institutional selling distribution confirmed: "
                        f"Distribution candle had {abs_vol_ratio:.1f}× avg volume with "
                        f"a strong upper rejection wick. "
                        f"Current bar confirms bearish follow-through. ADX: {adx_val:.1f}."
                    ),
                    indicators={
                        "vol_ratio": round(abs_vol_ratio, 2),
                        "adx": round(adx_val, 1),
                        "atr": round(atr, 2),
                        "absorption_high": round(float(absorption_candle["high"]), 2),
                    },
                )
            )

        return signals
