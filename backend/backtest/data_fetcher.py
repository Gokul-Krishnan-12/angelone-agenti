"""
Backtest data fetcher — downloads NSE historical candles via yfinance.

Uses the .NS suffix for NSE-listed stocks.
Supported intervals: '5m', '15m', '1h', '1d'
Supported periods:   '60d' (5m/15m), '1y', '2y' (1h/1d)
"""

from __future__ import annotations

import time

import pandas as pd
import yfinance as yf


def fetch_candles(
    symbol: str,
    period: str = "60d",
    interval: str = "5m",
    retries: int = 3,
) -> pd.DataFrame:
    """
    Download OHLCV candles for an NSE symbol from Yahoo Finance.

    Parameters
    ----------
    symbol   : NSE symbol without exchange suffix (e.g. "RELIANCE")
    period   : lookback period (e.g. "60d", "6mo", "1y")
    interval : bar size ("5m", "15m", "1h", "1d")

    Returns
    -------
    DataFrame with columns: open, high, low, close, volume
    Empty DataFrame if download fails.
    """
    yf_symbol = f"{symbol}.NS"

    for attempt in range(retries):
        try:
            ticker = yf.Ticker(yf_symbol)
            raw = ticker.history(period=period, interval=interval, auto_adjust=True)
            if raw.empty:
                return pd.DataFrame()

            df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.columns = ["open", "high", "low", "close", "volume"]
            df = df.dropna()
            df = df[df["volume"] > 0]
            df = df.reset_index(drop=True)
            df["close"] = df["close"].astype(float)
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["volume"] = df["volume"].astype(float)
            return df

        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                print(f"[DataFetcher] Failed to fetch {symbol}: {e}")
                return pd.DataFrame()

    return pd.DataFrame()
