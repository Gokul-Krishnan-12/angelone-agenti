"""
Backtest data fetcher — downloads NSE historical candles via yfinance.

Uses the .NS suffix for NSE-listed stocks.
Supported intervals: '5m', '15m', '1h', '1d'
Supported periods:   '60d' (5m/15m), '1y', '2y' (1h/1d)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache" / "candles"


def fetch_candles(
    symbol: str,
    period: str = "60d",
    interval: str = "5m",
    retries: int = 3,
) -> pd.DataFrame:
    """Download OHLCV candles for an NSE symbol from Yahoo Finance (with disk cache).

    Parameters
    ----------
    symbol   : NSE symbol without exchange suffix (e.g. "RELIANCE")
    period   : lookback period (e.g. "60d", "6mo", "1y")
    interval : bar size ("5m", "15m", "1h", "1d")

    Returns
    -------
    DataFrame with columns: open, high, low, close, volume, datetime
    Empty DataFrame if download fails.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{symbol}_{period}_{interval}.pkl"

    # Check cache freshness (valid for 12 hours)
    if cache_file.exists():
        age = time.time() - os.path.getmtime(cache_file)
        if age < 12 * 3600:
            try:
                cached_df = pd.read_pickle(cache_file)
                if not cached_df.empty:
                    return cached_df
            except Exception:
                pass

    yf_symbol = f"{symbol}.NS"

    for attempt in range(retries):
        try:
            ticker = yf.Ticker(yf_symbol)
            raw = ticker.history(period=period, interval=interval, auto_adjust=True)
            if raw.empty:
                return pd.DataFrame()

            df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.columns = ["open", "high", "low", "close", "volume"]
            df["datetime"] = raw.index
            df = df.dropna()
            df = df[df["volume"] > 0]
            df = df.reset_index(drop=True)
            df["close"] = df["close"].astype(float)
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["volume"] = df["volume"].astype(float)

            # Save to cache
            try:
                df.to_pickle(cache_file)
            except Exception:
                pass

            return df

        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                print(f"[DataFetcher] Failed to fetch {symbol}: {e}")
                return pd.DataFrame()

    return pd.DataFrame()
