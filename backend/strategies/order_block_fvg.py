"""
Order Block & Fair Value Gap (FVG) Strategy — upgraded.

Changes from v1
---------------
• Displacement volume threshold raised from 1.2× to 2.0× average volume.
  A 1.2× spike is barely above average; 2.0× is a clear institutional move.
• Stop-loss is now ATR-calibrated (1.0 × ATR beyond the FVG boundary)
  rather than a fixed 0.1 % buffer.
• FVG zone size must be at least 0.15 % of price to filter micro-gaps.

Logic
-----
Scans the last 5 candles for a 3-bar FVG pattern (c1 → displacement → c3):
  Bullish FVG: c3.low > c1.high  (gap above c1, below c3 = institutional bid zone)
  Bearish FVG: c1.low > c3.high  (gap below c1, above c3 = institutional offer zone)

Entry is triggered when the current (latest) candle retests the FVG zone
and closes back above (BUY) / below (SELL) the midpoint of the gap.
"""

from typing import Any, Dict, List

import pandas as pd

from .base import BaseStrategy
from .utils import compute_atr

_MIN_DISP_VOL_RATIO = 2.0  # raised from 1.2
_MIN_FVG_PCT = 0.0015  # FVG must be at least 0.15 % of price


class OrderBlockFVGStrategy(BaseStrategy):
    def get_name(self) -> str:
        return "Order Block FVG"

    def get_description(self) -> str:
        return (
            "Identifies institutional displacement zones (Fair Value Gaps & Order Blocks) "
            "created by high-volume moves (≥ 2× avg) and triggers high-probability entries "
            "when price retests and rejects the imbalance. ATR-calibrated stop-loss."
        )

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < 25:
            return []

        signals: List[Dict[str, Any]] = []
        df = df.copy()

        vol_sma = df["volume"].rolling(window=20).mean()
        last = df.iloc[-1]
        entry = float(last["close"])
        atr = compute_atr(df)

        # Scan the 4 most-recent displacement windows (offsets 2–5 from the end)
        for offset in range(2, 6):
            if len(df) < offset + 2:
                break

            c1 = df.iloc[-offset - 1]  # bar before displacement
            disp = df.iloc[-offset]  # institutional displacement candle
            c3 = df.iloc[-offset + 1]  # candle after displacement

            disp_vol_sma = vol_sma.iloc[-offset]
            if pd.isna(disp_vol_sma) or disp_vol_sma <= 0:
                continue

            disp_vol_ratio = float(disp["volume"]) / float(disp_vol_sma)
            if disp_vol_ratio < _MIN_DISP_VOL_RATIO:
                continue  # not an institutional displacement

            # ── Bullish FVG ──────────────────────────────────────────
            if c3["low"] > c1["high"]:
                fvg_low = float(c1["high"])
                fvg_high = float(c3["low"])
                fvg_size_pct = (fvg_high - fvg_low) / entry

                if fvg_size_pct < _MIN_FVG_PCT:
                    continue  # gap too small to be meaningful

                fvg_mid = (fvg_low + fvg_high) / 2.0

                # Retest + rejection: candle dips into gap but closes above midpoint
                if (
                    last["low"] <= fvg_high
                    and last["close"] >= fvg_mid
                    and last["close"] > last["open"]  # bullish close
                ):
                    # ATR-based SL: 1.0 × ATR below the FVG low
                    sl = round(fvg_low - atr * 1.0, 2)
                    sl = max(sl, entry * 0.97)  # cap at -3 % of entry
                    risk = max(entry - sl, entry * 0.003)
                    target = round(entry + risk * 2.0, 2)
                    rr = self.calculate_rr(entry, sl, target)

                    signals.append(
                        self.format_signal(
                            tradingsymbol=tradingsymbol,
                            direction="BUY",
                            confidence=82,
                            entry=entry,
                            sl=sl,
                            target=target,
                            rr=rr,
                            reasoning=(
                                f"Bullish Order Block retest: FVG zone "
                                f"[{fvg_low:.2f} – {fvg_high:.2f}] "
                                f"created by {disp_vol_ratio:.1f}× institutional displacement. "
                                f"Current bar retested and closed above midpoint {fvg_mid:.2f}."
                            ),
                            indicators={
                                "fvg_low": round(fvg_low, 2),
                                "fvg_high": round(fvg_high, 2),
                                "displacement_vol_ratio": round(disp_vol_ratio, 2),
                                "atr": round(atr, 2),
                            },
                        )
                    )
                    break

            # ── Bearish FVG ──────────────────────────────────────────
            elif c1["low"] > c3["high"]:
                fvg_high = float(c1["low"])
                fvg_low = float(c3["high"])
                fvg_size_pct = (fvg_high - fvg_low) / entry

                if fvg_size_pct < _MIN_FVG_PCT:
                    continue

                fvg_mid = (fvg_low + fvg_high) / 2.0

                if (
                    last["high"] >= fvg_low
                    and last["close"] <= fvg_mid
                    and last["close"] < last["open"]  # bearish close
                ):
                    sl = round(fvg_high + atr * 1.0, 2)
                    sl = min(sl, entry * 1.03)
                    risk = max(sl - entry, entry * 0.003)
                    target = round(entry - risk * 2.0, 2)
                    rr = self.calculate_rr(entry, sl, target)

                    signals.append(
                        self.format_signal(
                            tradingsymbol=tradingsymbol,
                            direction="SELL",
                            confidence=82,
                            entry=entry,
                            sl=sl,
                            target=target,
                            rr=rr,
                            reasoning=(
                                f"Bearish Order Block retest: FVG zone "
                                f"[{fvg_low:.2f} – {fvg_high:.2f}] "
                                f"created by {disp_vol_ratio:.1f}× institutional displacement. "
                                f"Current bar retested and closed below midpoint {fvg_mid:.2f}."
                            ),
                            indicators={
                                "fvg_low": round(fvg_low, 2),
                                "fvg_high": round(fvg_high, 2),
                                "displacement_vol_ratio": round(disp_vol_ratio, 2),
                                "atr": round(atr, 2),
                            },
                        )
                    )
                    break

        return signals
