"""
CMF Institutional Flow Strategy — persistent flow + price momentum.

Changes from v1
---------------
• CMF threshold raised from 0.12 to 0.15 (stronger institutional flow required).
• CMF must be consistently above 0 for all of the last 5 bars (persistent
  accumulation), not just the most recent candle.
• Price momentum confirmation: for BUY, current high must be above the high
  3 bars ago (momentum not just flow). Vice versa for SELL.
• Volume threshold unchanged at 1.25 × average.
• ATR-calibrated SL instead of flat %.
"""

from typing import Any, Dict, List

import pandas as pd
from ta.trend import EMAIndicator
from ta.volume import ChaikinMoneyFlowIndicator

from .base import BaseStrategy

_CMF_BULL_THRESHOLD = 0.15  # raised from 0.12
_CMF_BEAR_THRESHOLD = -0.15  # raised from -0.12
_CMF_PERSISTENCE = 5  # bars of consistent positive/negative CMF required
_MIN_VOL_RATIO = 1.25  # unchanged


class CMFAccumulationStrategy(BaseStrategy):
    def get_name(self) -> str:
        return "CMF Institutional Flow"

    def get_description(self) -> str:
        return (
            "Tracks persistent institutional accumulation / distribution using Chaikin "
            "Money Flow (CMF ≥ 0.15 for 5+ consecutive bars) with price momentum "
            "and volume-surge confirmation."
        )

    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        if len(df) < 30:
            return []

        signals: List[Dict[str, Any]] = []
        df = df.copy()

        cmf = ChaikinMoneyFlowIndicator(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            volume=df["volume"],
            window=20,
        ).chaikin_money_flow()

        ema20 = EMAIndicator(close=df["close"], window=20).ema_indicator()
        vol_sma = df["volume"].rolling(window=20).mean()

        df["cmf"] = cmf
        df["ema20"] = ema20
        df["vol_sma"] = vol_sma

        last = df.iloc[-1]
        cmf_val = float(last["cmf"])
        avg_vol = float(last["vol_sma"])

        if pd.isna(cmf_val) or pd.isna(avg_vol) or avg_vol <= 0:
            return []

        vol_ratio = float(last["volume"]) / avg_vol

        if vol_ratio < _MIN_VOL_RATIO:
            return []

        # ── Persistence check: CMF must be consistently directional ────
        if len(df) >= _CMF_PERSISTENCE:
            cmf_window = df["cmf"].tail(_CMF_PERSISTENCE)
            cmf_all_positive = bool((cmf_window > 0.0).all())
            cmf_all_negative = bool((cmf_window < 0.0).all())
        else:
            cmf_all_positive = cmf_val > 0
            cmf_all_negative = cmf_val < 0

        # ── Price momentum check ───────────────────────────────────────
        # High must be higher than 3 bars ago (BUY) / Low lower than 3 bars ago (SELL)
        momentum_bars = 3
        if len(df) >= momentum_bars + 1:
            higher_high = float(last["high"]) > float(
                df["high"].iloc[-(momentum_bars + 1)]
            )
            lower_low = float(last["low"]) < float(df["low"].iloc[-(momentum_bars + 1)])
        else:
            higher_high = True
            lower_low = True

        # ── BUY ────────────────────────────────────────────────────────
        if (
            cmf_val >= _CMF_BULL_THRESHOLD
            and vol_ratio >= _MIN_VOL_RATIO
            and float(last["close"]) > float(last["ema20"])
            and last["close"] > last["open"]
            and cmf_all_positive
            and higher_high
        ):
            entry = float(last["close"])
            sl = self.calculate_atr_stop_loss(df, entry, "BUY")
            risk = max(entry - sl, entry * 0.003)
            target = round(entry + risk * 2.0, 2)
            rr = self.calculate_rr(entry, sl, target)

            signals.append(
                self.format_signal(
                    tradingsymbol=tradingsymbol,
                    direction="BUY",
                    confidence=84,
                    entry=entry,
                    sl=sl,
                    target=target,
                    rr=rr,
                    reasoning=(
                        f"Persistent institutional accumulation: CMF +{cmf_val:.2f} "
                        f"(positive for {_CMF_PERSISTENCE}+ bars) with {vol_ratio:.1f}× "
                        f"volume surge above EMA 20. Price making higher highs."
                    ),
                    indicators={
                        "cmf": round(cmf_val, 3),
                        "volume_ratio": round(vol_ratio, 2),
                        "ema20": round(float(last["ema20"]), 2),
                    },
                )
            )

        # ── SELL ───────────────────────────────────────────────────────
        elif (
            cmf_val <= _CMF_BEAR_THRESHOLD
            and vol_ratio >= _MIN_VOL_RATIO
            and float(last["close"]) < float(last["ema20"])
            and last["close"] < last["open"]
            and cmf_all_negative
            and lower_low
        ):
            entry = float(last["close"])
            sl = self.calculate_atr_stop_loss(df, entry, "SELL")
            risk = max(sl - entry, entry * 0.003)
            target = round(entry - risk * 2.0, 2)
            rr = self.calculate_rr(entry, sl, target)

            signals.append(
                self.format_signal(
                    tradingsymbol=tradingsymbol,
                    direction="SELL",
                    confidence=84,
                    entry=entry,
                    sl=sl,
                    target=target,
                    rr=rr,
                    reasoning=(
                        f"Persistent institutional distribution: CMF {cmf_val:.2f} "
                        f"(negative for {_CMF_PERSISTENCE}+ bars) with {vol_ratio:.1f}× "
                        f"volume surge below EMA 20. Price making lower lows."
                    ),
                    indicators={
                        "cmf": round(cmf_val, 3),
                        "volume_ratio": round(vol_ratio, 2),
                        "ema20": round(float(last["ema20"]), 2),
                    },
                )
            )

        return signals
