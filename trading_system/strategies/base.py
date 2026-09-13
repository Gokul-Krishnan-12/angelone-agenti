"""
Abstract Strategy Protocol, Signal Models, and Confluence Validator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..config.settings import Settings, get_settings


@dataclass(frozen=True)
class Signal:
    """Standardized trading signal emitted by strategy engines."""

    strategy_name: str
    family: str  # e.g. 'breakout', 'structure', 'reversal', 'trend'
    tradingsymbol: str
    direction: str  # 'BUY' or 'SELL'
    confidence: int  # 0 to 100
    entry_price: float
    stop_loss: float
    target_price: float
    risk_reward: float
    timestamp: float
    indicators: Dict[str, Any] = field(default_factory=dict)

    @property
    def risk_amount(self) -> float:
        return round(abs(self.entry_price - self.stop_loss), 2)

    @property
    def reward_amount(self) -> float:
        return round(abs(self.target_price - self.entry_price), 2)


class BaseStrategy(ABC):
    """Abstract base class for all trading strategy engines."""

    def __init__(self, name: str, family: str):
        self.name = name
        self.family = family

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, tradingsymbol: str) -> List[Signal]:
        """
        Evaluate closed candles and generate trading signals.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing closed OHLCV bars with columns:
            ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        tradingsymbol : str
            Instrument symbol without suffix (e.g. 'RELIANCE').
        """
        pass

    @staticmethod
    def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
        """Vectorized Average True Range (ATR) calculation."""
        if len(df) < period + 1:
            return 0.0
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        if len(tr) < period:
            return float(np.mean(tr)) if len(tr) > 0 else 0.0

        # Wilder's smoothing or simple mean of recent TR
        return float(np.mean(tr[-period:]))

    @staticmethod
    def compute_adx(df: pd.DataFrame, period: int = 14) -> float:
        """Vectorized Directional Movement Index (ADX) calculation."""
        if len(df) < period * 2:
            return 25.0  # Default neutral reading if insufficient data

        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        # Up/Down move
        up_move = high[1:] - high[:-1]
        down_move = low[:-1] - low[1:]

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        tr_sum = np.sum(tr[-period:])
        if tr_sum <= 0:
            return 0.0

        plus_di = 100.0 * (np.sum(plus_dm[-period:]) / tr_sum)
        minus_di = 100.0 * (np.sum(minus_dm[-period:]) / tr_sum)

        di_sum = plus_di + minus_di
        if di_sum <= 0:
            return 0.0

        dx = 100.0 * (abs(plus_di - minus_di) / di_sum)
        return float(dx)

    @staticmethod
    def compute_ema(series: pd.Series, span: int) -> float:
        """Compute latest value of Exponential Moving Average."""
        if len(series) < span:
            return float(series.mean()) if len(series) > 0 else 0.0
        return float(series.ewm(span=span, adjust=False).mean().iloc[-1])


class ConfluenceGate:
    """
    Validates that candidate signals satisfy multi-family confluence,
    trend alignment (50 EMA), ADX regime filtering, and minimum R:R rules.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def validate_signals(
        self,
        signals: List[Signal],
        df: pd.DataFrame,
    ) -> Optional[Signal]:
        """
        Filter and select the highest-conviction signal from multiple strategy outputs.
        """
        if not signals:
            return None

        # Group by direction
        buys = [s for s in signals if s.direction == "BUY"]
        sells = [s for s in signals if s.direction == "SELL"]

        selected_group = buys if len(buys) >= len(sells) else sells
        if not selected_group:
            return None

        direction = selected_group[0].direction

        # 1. Macro Trend Alignment Gate (50 EMA)
        if len(df) >= 50:
            closes = df["close"]
            ema50 = float(closes.ewm(span=50, adjust=False).mean().iloc[-1])
            curr_close = float(closes.iloc[-1])

            if direction == "BUY" and curr_close < ema50:
                logger.debug("ConfluenceGate: Rejected counter-trend BUY below 50 EMA")
                return None
            if direction == "SELL" and curr_close > ema50:
                logger.debug("ConfluenceGate: Rejected counter-trend SELL above 50 EMA")
                return None

        # 2. ADX Volatility / Trend Strength Regime Gate
        if len(df) >= 28:
            adx = BaseStrategy.compute_adx(df, period=14)
            if adx < 18.0:
                logger.debug(
                    "ConfluenceGate: Rejected signal in low-trend regime (ADX %.1f < 18.0)",
                    adx,
                )
                return None

        # 2. Independent Family Confluence Gate
        families_voting = {s.family for s in selected_group}
        if len(families_voting) < self.settings.min_confluence:
            logger.debug(
                "ConfluenceGate: Signal has %d families (%s), requires >= %d",
                len(families_voting),
                families_voting,
                self.settings.min_confluence,
            )
            return None

        # 3. Select highest confidence candidate
        best_signal = max(selected_group, key=lambda s: s.confidence)

        # 4. Minimum Risk-to-Reward Gate
        if best_signal.risk_reward < self.settings.min_risk_reward:
            logger.debug(
                "ConfluenceGate: R:R %.2f below required %.2f",
                best_signal.risk_reward,
                self.settings.min_risk_reward,
            )
            return None

        # 5. Noise Protection: Minimum SL buffer floor
        entry = best_signal.entry_price
        sl = best_signal.stop_loss
        min_sl_dist = entry * (self.settings.min_stop_loss_percent / 100.0)
        curr_sl_dist = abs(entry - sl)

        if curr_sl_dist < min_sl_dist:
            # Widen stop-loss to minimum noise buffer and recalculate target
            adjusted_sl = round(
                entry - min_sl_dist if direction == "BUY" else entry + min_sl_dist, 2
            )
            adjusted_target = round(
                entry
                + (
                    min_sl_dist
                    * max(best_signal.risk_reward, self.settings.min_risk_reward)
                )
                if direction == "BUY"
                else entry
                - (
                    min_sl_dist
                    * max(best_signal.risk_reward, self.settings.min_risk_reward)
                ),
                2,
            )
            best_signal = Signal(
                strategy_name=best_signal.strategy_name,
                family=best_signal.family,
                tradingsymbol=best_signal.tradingsymbol,
                direction=best_signal.direction,
                confidence=best_signal.confidence,
                entry_price=best_signal.entry_price,
                stop_loss=adjusted_sl,
                target_price=adjusted_target,
                risk_reward=round(
                    abs(adjusted_target - entry) / abs(entry - adjusted_sl), 2
                ),
                timestamp=best_signal.timestamp,
                indicators={
                    **best_signal.indicators,
                    "families_voting": list(families_voting),
                },
            )
        else:
            best_signal = Signal(
                strategy_name=best_signal.strategy_name,
                family=best_signal.family,
                tradingsymbol=best_signal.tradingsymbol,
                direction=best_signal.direction,
                confidence=best_signal.confidence,
                entry_price=best_signal.entry_price,
                stop_loss=best_signal.stop_loss,
                target_price=best_signal.target_price,
                risk_reward=best_signal.risk_reward,
                timestamp=best_signal.timestamp,
                indicators={
                    **best_signal.indicators,
                    "families_voting": list(families_voting),
                },
            )

        logger.success(
            "ConfluenceGate APPROVED: %s %s on %s (Confluence: %d families %s, R:R %.2f)",
            best_signal.direction,
            best_signal.strategy_name,
            best_signal.tradingsymbol,
            len(families_voting),
            families_voting,
            best_signal.risk_reward,
        )
        return best_signal
