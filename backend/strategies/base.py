import datetime
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import pandas as pd


class BaseStrategy(ABC):
    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

    @abstractmethod
    def calculate_signals(
        self, df: pd.DataFrame, tradingsymbol: str
    ) -> List[Dict[str, Any]]:
        pass

    def calculate_stop_loss(
        self, entry: float, direction: str, percentage: float = None
    ) -> float:
        if percentage is None:
            from ..config import config_manager

            percentage = config_manager.get_risk_config().get(
                "defaultStopLossPercent", 1.5
            )

        if direction == "BUY":
            return round(entry * (1 - percentage / 100), 2)
        else:
            return round(entry * (1 + percentage / 100), 2)

    def calculate_atr_stop_loss(
        self,
        df: "pd.DataFrame",
        entry: float,
        direction: str,
        multiplier: float = 1.5,
    ) -> float:
        """
        ATR-calibrated stop loss.

        Places the SL at ``entry ± (multiplier × ATR(14))``, with a minimum
        distance floor of 0.3 % of the entry price to avoid noise-level SLs.
        Falls back to the percentage-based SL if ATR cannot be computed.
        """
        try:
            from ta.volatility import AverageTrueRange

            atr_series = AverageTrueRange(
                high=df["high"], low=df["low"], close=df["close"], window=14
            ).average_true_range()
            atr = float(atr_series.iloc[-1])
            if pd.isna(atr) or atr <= 0:
                return self.calculate_stop_loss(entry, direction)
            min_distance = entry * 0.003  # 0.3 % floor
            distance = max(atr * multiplier, min_distance)
            if direction == "BUY":
                return round(entry - distance, 2)
            else:
                return round(entry + distance, 2)
        except Exception:
            return self.calculate_stop_loss(entry, direction)

    def calculate_rr(self, entry: float, sl: float, target: float) -> float:
        """Return the risk-reward ratio for a trade, rounded to 2 dp."""
        risk = abs(entry - sl)
        reward = abs(target - entry)
        if risk <= 0:
            return 0.0
        return round(reward / risk, 2)

    def calculate_target(
        self, entry: float, sl: float, percentage: float = None
    ) -> float:
        if percentage is None:
            from ..config import config_manager

            percentage = config_manager.get_risk_config().get(
                "defaultTargetPercent", 3.0
            )

        if entry > sl:  # BUY
            return round(entry * (1 + percentage / 100), 2)
        else:  # SELL
            return round(entry * (1 - percentage / 100), 2)

    def generate_signal_id(self) -> str:
        return str(uuid.uuid4())

    def format_signal(
        self,
        tradingsymbol: str,
        direction: str,
        confidence: int,
        entry: float,
        sl: float,
        target: float,
        rr: float,
        reasoning: str,
        indicators: dict,
    ) -> Dict[str, Any]:
        return {
            "id": self.generate_signal_id(),
            "tradingsymbol": tradingsymbol,
            "exchange": "NSE",
            "strategy": self.get_name(),
            "direction": direction,
            "confidence": confidence,
            "entryPrice": entry,
            "stopLoss": sl,
            "target": target,
            "riskReward": rr,
            "reasoning": reasoning,
            "timestamp": datetime.datetime.now().isoformat(),
            "indicators": indicators,
        }
