"""
Strategy Engine: Structural Stop-Loss Volatility Buffers & Pullback Limit Entry.

Prevents:
1. Structural stop-loss clustering & stop runs by adding 0.5x ATR breathing room
   below swing lows (BUY) or above swing highs (SELL).
2. Breakout chasing on expansion candle closes by calculating pullback limit orders
   at value support/resistance (nearest of VWAP, 20 EMA, or breakout level).
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from .strategies.utils import compute_atr, compute_volume_profile, compute_vwap_bands

logger = logging.getLogger("strategy_engine")


def calculate_volatility_buffered_sl(
    df: pd.DataFrame,
    direction: str,
    raw_sl: Optional[float] = None,
    lookback: int = 10,
    atr_multiplier: float = 0.5,
) -> float:
    """
    Calculate an ATR-buffered structural stop loss.

    For BUY orders:
        StopLoss = round(structural_low - (0.5 * atr_14), 2)
    For SELL orders:
        StopLoss = round(structural_high + (0.5 * atr_14), 2)

    Parameters
    ----------
    df : pd.DataFrame
        Candle history with ['open', 'high', 'low', 'close', 'volume'].
    direction : str
        "BUY" or "SELL".
    raw_sl : float, optional
        Baseline or unbuffered strategy SL level.
    lookback : int
        Number of recent candles to establish structural swing boundaries (default: 10).
    atr_multiplier : float
        ATR multiplier for breathing room (default: 0.5).

    Returns
    -------
    float
        Buffered stop loss price.
    """
    if df is None or len(df) < 5:
        return float(raw_sl or 0.0)

    direction = direction.upper()
    atr = compute_atr(df, period=14)
    curr_close = float(df["close"].iloc[-1])

    # Fallback to 0.8% of price if ATR cannot be computed
    if atr <= 0 or pd.isna(atr):
        atr = curr_close * 0.008

    recent_bars = df.iloc[-min(len(df), max(3, lookback)) :]

    if direction == "BUY":
        structural_low = float(recent_bars["low"].min())
        if raw_sl is not None and raw_sl > 0:
            structural_low = min(structural_low, float(raw_sl))
        buffered_sl = structural_low - (atr_multiplier * atr)
        return round(max(0.05, buffered_sl), 2)
    else:
        structural_high = float(recent_bars["high"].max())
        if raw_sl is not None and raw_sl > 0:
            structural_high = max(structural_high, float(raw_sl))
        buffered_sl = structural_high + (atr_multiplier * atr)
        return round(buffered_sl, 2)


def calculate_pullback_limit_entry(
    df: pd.DataFrame,
    direction: str,
    breakout_level: Optional[float] = None,
) -> float:
    """
    Calculate a limit entry price at the nearest value pullback level.

    Shifts execution away from buying/selling the exhaustion close of a 5m expansion candle.
    For BUY:
        entry_price = round(max(vwap_price, ema_20, breakout_level), 2)
        (bounded by current close to ensure a genuine pullback entry)
    For SELL:
        entry_price = round(min(vwap_price, ema_20, breakout_level), 2)
        (bounded by current close to ensure a genuine pullback entry)

    Parameters
    ----------
    df : pd.DataFrame
        Candle history with ['open', 'high', 'low', 'close', 'volume'].
    direction : str
        "BUY" or "SELL".
    breakout_level : float, optional
        The level broken out of (e.g. Donchian upper/lower, Keltner band, pivot level).

    Returns
    -------
    float
        Pullback limit entry price.
    """
    if df is None or len(df) < 3:
        return 0.0

    direction = direction.upper()
    closes = df["close"].astype(float)
    curr_close = float(closes.iloc[-1])

    # 1. Session VWAP
    try:
        vwap_data = compute_vwap_bands(df)
        vwap_price = float(vwap_data.get("vwap", curr_close))
    except Exception:
        vwap_price = curr_close

    # 2. 20-period EMA
    if len(closes) >= 20:
        ema_20 = float(closes.ewm(span=20, adjust=False).mean().iloc[-1])
    else:
        ema_20 = float(closes.mean())

    # 3. Breakout reference level if not provided
    if breakout_level is None or breakout_level <= 0:
        ref_bars = df.iloc[-min(len(df), 21) : -1]
        if len(ref_bars) > 0:
            if direction == "BUY":
                breakout_level = float(ref_bars["high"].max())
            else:
                breakout_level = float(ref_bars["low"].min())
        else:
            breakout_level = curr_close

    # 4. Volume Profile (POC & Value Area bounds)
    poc_candidates = []
    try:
        vp = compute_volume_profile(df, n_bars=min(len(df), 40), n_bins=20)
        poc = float(vp.get("poc", 0.0))
        vah = float(vp.get("value_area_high", 0.0))
        val = float(vp.get("value_area_low", 0.0))
        if poc > 0:
            poc_candidates.append(poc)
        if direction == "BUY" and vah > 0:
            poc_candidates.append(vah)
        elif direction == "SELL" and val > 0:
            poc_candidates.append(val)
    except Exception:
        pass

    candidates = [
        v for v in (vwap_price, ema_20, float(breakout_level) if breakout_level else 0, *poc_candidates) if v and v > 0
    ]
    if not candidates:
        return round(curr_close, 2)

    if direction == "BUY":
        # Nearest support strictly below the breakout close (0.3% - 1.5% pullback)
        valid_supports = [c for c in candidates if c < curr_close]
        if valid_supports:
            pullback_val = max(valid_supports)
            # Bound pullback between 0.3% and 1.5% below close
            pullback_val = max(pullback_val, curr_close * 0.985)
            entry_price = min(curr_close * 0.997, pullback_val)
        else:
            entry_price = round(curr_close * 0.996, 2)
    else:
        # Nearest resistance strictly above the breakdown close (0.3% - 1.5% pullback)
        valid_resistances = [c for c in candidates if c > curr_close]
        if valid_resistances:
            pullback_val = min(valid_resistances)
            # Bound pullback between 0.3% and 1.5% above close
            pullback_val = min(pullback_val, curr_close * 1.015)
            entry_price = max(curr_close * 1.003, pullback_val)
        else:
            entry_price = round(curr_close * 1.004, 2)

    return round(entry_price, 2)

