"""
Real-Time Tick Aggregator & Bar Synthesizer.
Maintains in-memory ring buffers and synthesizes 1m/5m OHLCV bars without REST polling.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, Coroutine, Dict, List, Optional

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
    Ingests live tick streams, builds rolling 1m and 5m OHLCV bars in-memory,
    and fires asynchronous `on_candle_close` events precisely at bucket boundaries.
    """

    def __init__(
        self,
        bar_interval_seconds: int = 300,  # 5-minute bars default
        max_history: int = 300,
        on_candle_close: Optional[
            Callable[[str, str, Candle, pd.DataFrame], Coroutine]
        ] = None,
    ):
        self.bar_interval = bar_interval_seconds
        self.max_history = max_history
        self.on_candle_close = on_candle_close

        # Current incomplete building bars: token -> Candle
        self._current_bar: Dict[str, Candle] = {}

        # Historical completed bars: token -> deque of Candle
        self._history: Dict[str, deque[Candle]] = defaultdict(
            lambda: deque(maxlen=self.max_history)
        )

        # Volume state tracking (cumulative day volume delta calculation)
        self._last_day_volume: Dict[str, float] = defaultdict(float)

    def process_tick(
        self,
        token: str,
        tradingsymbol: str,
        ltp: float,
        day_volume: float = 0.0,
        tick_time: Optional[float] = None,
    ):
        """
        Ingest normalized tick and update live candlestick synthesis.

        Parameters
        ----------
        token : str
            Instrument scrip token.
        tradingsymbol : str
            Trading symbol name (e.g. 'RELIANCE').
        ltp : float
            Normalized Last Traded Price in INR.
        day_volume : float, default=0.0
            Exchange cumulative traded volume for the day.
        tick_time : float, optional
            Timestamp in epoch seconds (defaults to time.time()).
        """
        if ltp <= 0:
            return

        now_ts = tick_time if tick_time is not None else time.time()
        bucket_ts = (int(now_ts) // self.bar_interval) * self.bar_interval

        # Calculate incremental volume delta since last tick
        prev_day_vol = self._last_day_volume[token]
        vol_delta = (
            max(0.0, day_volume - prev_day_vol)
            if prev_day_vol > 0 and day_volume >= prev_day_vol
            else 0.0
        )
        self._last_day_volume[token] = day_volume

        curr = self._current_bar.get(token)

        # Check if tick belongs to a new time bucket
        if curr is None:
            # First tick for this token
            self._current_bar[token] = Candle(
                token=token,
                tradingsymbol=tradingsymbol,
                timestamp=bucket_ts,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
                volume=vol_delta,
                is_closed=False,
            )
            return

        if bucket_ts > curr.timestamp:
            # Current bar has officially closed!
            curr.is_closed = True
            closed_bar = curr

            # Append to rolling ring buffer
            self._history[token].append(closed_bar)

            # Start fresh building bar for the new bucket
            self._current_bar[token] = Candle(
                token=token,
                tradingsymbol=tradingsymbol,
                timestamp=bucket_ts,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
                volume=vol_delta,
                is_closed=False,
            )

            # Dispatch asynchronous candle closure event to alpha engine
            if self.on_candle_close:
                history_df = self.get_history_df(token)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        self.on_candle_close(
                            token, tradingsymbol, closed_bar, history_df
                        )
                    )
                except RuntimeError:
                    # If running outside an active event loop (e.g. unit tests)
                    asyncio.run(
                        self.on_candle_close(
                            token, tradingsymbol, closed_bar, history_df
                        )
                    )

        else:
            # Update current active candle in-place
            curr.high = max(curr.high, ltp)
            curr.low = min(curr.low, ltp)
            curr.close = ltp
            curr.volume += vol_delta

    def seed_history(
        self, token: str, tradingsymbol: str, candles: List[Dict[str, float]]
    ):
        """
        Pre-seed the ring buffer with initial historical candles (e.g. at startup).
        """
        buf = self._history[token]
        buf.clear()
        for c in candles:
            buf.append(
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
            "Pre-seeded %d historical bars for %s (%s)", len(buf), tradingsymbol, token
        )

    def get_history_df(self, token: str) -> pd.DataFrame:
        """Return historical completed bars as a pandas DataFrame."""
        records = [c.to_dict() for c in self._history[token]]
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

    def get_bars_count(self, token: str) -> int:
        """Return count of closed bars in memory for token."""
        return len(self._history[token])
