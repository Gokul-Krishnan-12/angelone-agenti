"""
Real-Time Tick Aggregator & Bar Synthesizer.
Maintains in-memory ring buffers and synthesizes 1m/5m OHLCV bars without REST polling.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, Optional

import pandas as pd
from loguru import logger


@dataclass
class Candle:
    """Standard OHLCV Candle structure."""

    token: str
    tradingsymbol: str
    timestamp: float  # Start of candle bucket in epoch seconds
    open: float
    high: float
    low: float
    close: float
    volume: float  # Incremental volume accumulated during the bar
    is_closed: bool = False

    def to_dict(self) -> Dict[str, float | str | bool]:
        return {
            "token": self.token,
            "tradingsymbol": self.tradingsymbol,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "is_closed": self.is_closed,
        }


class BarAggregator:
    """
    High-Performance In-Memory WebSocket Bar Aggregator.
    Synthesizes live 1-minute and 5-minute OHLCV candles from tick feeds without REST polling.
    Fires asynchronous `on_candle_close` events precisely at 5-minute boundaries (t % 300 == 0).
    """

    def __init__(
        self,
        bar_interval_seconds: int = 300,  # 5-minute bars default for decision engine
        max_history: int = 300,
        on_candle_close: Optional[
            Callable[[str, str, Candle, pd.DataFrame], Coroutine]
        ] = None,
        on_1m_candle_close: Optional[
            Callable[[str, str, Candle, pd.DataFrame], Coroutine]
        ] = None,
    ):
        self.bar_interval = bar_interval_seconds
        self.max_history = max_history
        self.on_candle_close = on_candle_close
        self.on_1m_candle_close = on_1m_candle_close

        # Current incomplete building bars
        self._current_bar_5m: Dict[str, Candle] = {}
        self._current_bar_1m: Dict[str, Candle] = {}

        # Historical completed bars: token -> deque of Candle
        self._history_5m: Dict[str, deque[Candle]] = defaultdict(
            lambda: deque(maxlen=self.max_history)
        )
        self._history_1m: Dict[str, deque[Candle]] = defaultdict(
            lambda: deque(maxlen=self.max_history * 5)
        )

        # Volume state tracking (cumulative day volume delta calculation)
        self._last_day_volume: Dict[str, float] = defaultdict(float)

    @property
    def _current_bar(self) -> Dict[str, Candle]:
        """Backward-compatible accessor for current active 5m building candle."""
        return self._current_bar_5m

    @property
    def _history(self) -> Dict[str, deque[Candle]]:
        """Backward-compatible accessor for historical 5m completed bars."""
        return self._history_5m

    def process_raw_quote(
        self,
        token: str,
        tradingsymbol: str,
        quote_data: Dict[str, Any],
    ):
        """
        Convenience ingestion method for raw Mode 2 QUOTE packets from SmartWebSocketV2.
        Normalizes Paise to INR (divides by 100.0).
        """
        raw_price = quote_data.get("last_traded_price")
        if raw_price is not None:
            ltp = float(raw_price) / 100.0
        else:
            raw_alt = quote_data.get("ltp") or quote_data.get("last_price") or 0.0
            ltp = float(raw_alt)

        if ltp <= 0:
            return

        day_vol = float(
            quote_data.get("volume_trade_for_the_day")
            or quote_data.get("volume")
            or 0.0
        )
        ts = time.time()
        ex_ts = quote_data.get("exchange_timestamp")
        if ex_ts and str(ex_ts).isdigit():
            num_ts = float(ex_ts)
            ts = num_ts / 1000.0 if num_ts > 1e11 else num_ts

        self.process_tick(token, tradingsymbol, ltp, day_vol, ts)

    def process_tick(
        self,
        token: str,
        tradingsymbol: str,
        ltp: float,
        day_volume: float = 0.0,
        tick_time: Optional[float] = None,
    ):
        """
        Ingest normalized tick and synthesize dual 1-minute and 5-minute candles.
        """
        if ltp <= 0:
            return

        now_ts = tick_time if tick_time is not None else time.time()

        # Calculate incremental volume delta since last tick
        prev_day_vol = self._last_day_volume[token]
        vol_delta = (
            max(0.0, day_volume - prev_day_vol)
            if prev_day_vol > 0 and day_volume >= prev_day_vol
            else 0.0
        )
        self._last_day_volume[token] = day_volume

        # ── 1. Update 1-Minute Bar ───────────────────────────────────
        bucket_1m = (int(now_ts) // 60) * 60
        curr_1m = self._current_bar_1m.get(token)

        if curr_1m is None:
            self._current_bar_1m[token] = Candle(
                token=token,
                tradingsymbol=tradingsymbol,
                timestamp=bucket_1m,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
                volume=vol_delta,
                is_closed=False,
            )
        elif bucket_1m > curr_1m.timestamp:
            curr_1m.is_closed = True
            closed_1m = curr_1m
            self._history_1m[token].append(closed_1m)
            self._current_bar_1m[token] = Candle(
                token=token,
                tradingsymbol=tradingsymbol,
                timestamp=bucket_1m,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
                volume=vol_delta,
                is_closed=False,
            )
            if self.on_1m_candle_close:
                self._dispatch_callback(
                    self.on_1m_candle_close,
                    token,
                    tradingsymbol,
                    closed_1m,
                    self.get_history_df(token, interval=1),
                )
        else:
            curr_1m.high = max(curr_1m.high, ltp)
            curr_1m.low = min(curr_1m.low, ltp)
            curr_1m.close = ltp
            curr_1m.volume += vol_delta

        # ── 2. Update 5-Minute Bar (Primary Strategy Evaluation Timeframe) ─
        bucket_5m = (int(now_ts) // self.bar_interval) * self.bar_interval
        curr_5m = self._current_bar_5m.get(token)

        if curr_5m is None:
            self._current_bar_5m[token] = Candle(
                token=token,
                tradingsymbol=tradingsymbol,
                timestamp=bucket_5m,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
                volume=vol_delta,
                is_closed=False,
            )
        elif bucket_5m > curr_5m.timestamp:
            curr_5m.is_closed = True
            closed_5m = curr_5m
            self._history_5m[token].append(closed_5m)
            self._current_bar_5m[token] = Candle(
                token=token,
                tradingsymbol=tradingsymbol,
                timestamp=bucket_5m,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
                volume=vol_delta,
                is_closed=False,
            )

            # Fire sub-20ms asynchronous candle close callback
            if self.on_candle_close:
                history_df = self.get_history_df(token, interval=5)
                self._dispatch_callback(
                    self.on_candle_close, token, tradingsymbol, closed_5m, history_df
                )
        else:
            curr_5m.high = max(curr_5m.high, ltp)
            curr_5m.low = min(curr_5m.low, ltp)
            curr_5m.close = ltp
            curr_5m.volume += vol_delta

    def _dispatch_callback(
        self,
        callback: Callable[[str, str, Candle, pd.DataFrame], Coroutine],
        token: str,
        tradingsymbol: str,
        closed_bar: Candle,
        history_df: pd.DataFrame,
    ):
        """Execute async callback cleanly inside current event loop or sync runner."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(callback(token, tradingsymbol, closed_bar, history_df))
        except RuntimeError:
            asyncio.run(callback(token, tradingsymbol, closed_bar, history_df))

    def seed_history(
        self,
        token: str,
        tradingsymbol: str,
        candles: List[Dict[str, float]],
        interval: int = 5,
    ):
        """Pre-seed the ring buffer with initial historical candles at system startup."""
        target_buf = (
            self._history_5m[token] if interval == 5 else self._history_1m[token]
        )
        target_buf.clear()
        for c in candles:
            target_buf.append(
                Candle(
                    token=token,
                    tradingsymbol=tradingsymbol,
                    timestamp=float(c.get("timestamp", 0)),
                    open=float(c["open"]),
                    high=float(c["high"]),
                    low=float(c["low"]),
                    close=float(c["close"]),
                    volume=float(c.get("volume", 0)),
                    is_closed=True,
                )
            )
        logger.info(
            "Pre-seeded %d historical %dm bars for %s (%s)",
            len(target_buf),
            interval,
            tradingsymbol,
            token,
        )

    def get_history_df(self, token: str, interval: int = 5) -> pd.DataFrame:
        """Return historical completed bars as a pandas DataFrame."""
        source = self._history_5m[token] if interval == 5 else self._history_1m[token]
        records = [c.to_dict() for c in source]
        if not records:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume", "timestamp"]
            )

        df = pd.DataFrame(records)
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df

    def get_bars_count(self, token: str, interval: int = 5) -> int:
        """Return count of closed bars in memory for token."""
        return len(
            self._history_5m[token] if interval == 5 else self._history_1m[token]
        )
