"""
Shared market-condition utilities used across all strategies.

Provides ATR, regime detection, per-candle delta, cumulative delta,
volume profile (POC), VWAP bands, and relative volume helpers.
"""

from __future__ import annotations

import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange

# ─── ATR ──────────────────────────────────────────────────────────────────────


def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Return the most recent ATR value.  Returns 0.0 if not computable."""
    if len(df) < period + 1:
        return 0.0
    atr_series = AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=period
    ).average_true_range()
    val = atr_series.iloc[-1]
    return float(val) if not pd.isna(val) else 0.0


# ─── Market Regime ─────────────────────────────────────────────────────────────


def compute_regime(df: pd.DataFrame, period: int = 14) -> str:
    """
    Classify the current market regime using ADX(14).

    Returns
    -------
    'trend'    – ADX > 25  (directional, strategies work well)
    'range'    – ADX 18-25 (moderate, some strategies may trade)
    'volatile' – ADX < 18  (choppy, skip new entries)
    """
    if len(df) < period + 5:
        return "range"
    adx_indicator = ADXIndicator(
        high=df["high"], low=df["low"], close=df["close"], window=period
    )
    adx_val = adx_indicator.adx().iloc[-1]
    if pd.isna(adx_val):
        return "range"
    if adx_val > 25:
        return "trend"
    elif adx_val >= 18:
        return "range"
    else:
        return "volatile"


# ─── Volume Delta ──────────────────────────────────────────────────────────────


def compute_delta(df: pd.DataFrame) -> pd.Series:
    """
    Estimate net buying vs. selling pressure per candle.

    delta = buy_vol - sell_vol
          = [(close - low) / (high - low) - (high - close) / (high - low)] × volume
          = [(2 × close - high - low) / (high - low)] × volume

    Positive delta  → net buying pressure (bullish).
    Negative delta  → net selling pressure (bearish).
    Doji candles (high == low) produce delta = 0.
    """
    hl = (df["high"] - df["low"]).replace(0.0, float("nan"))
    delta = ((2 * df["close"] - df["high"] - df["low"]) / hl) * df["volume"]
    return delta.fillna(0.0)


def compute_cumulative_delta(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Rolling sum of per-candle delta over `window` bars."""
    return compute_delta(df).rolling(window=window).sum()


# ─── VWAP Bands ────────────────────────────────────────────────────────────────


def compute_vwap_bands(df: pd.DataFrame) -> dict:
    """
    Compute session VWAP and ±1σ / ±2σ standard-deviation bands.

    Standard deviation is calculated as the volume-weighted deviation of
    the typical price from VWAP (similar to Bollinger Bands around VWAP).

    Returns
    -------
    dict with keys: vwap, upper1, upper2, lower1, lower2
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol = df["volume"].cumsum()
    cum_tp_vol = (tp * df["volume"]).cumsum()

    vwap = cum_tp_vol / cum_vol

    deviation_sq = (tp - vwap) ** 2
    cum_dev_vol = (deviation_sq * df["volume"]).cumsum()
    variance = cum_dev_vol / cum_vol
    std = variance**0.5

    last_vwap = float(vwap.iloc[-1])
    last_std = float(std.iloc[-1]) if not pd.isna(std.iloc[-1]) else 0.0

    return {
        "vwap": last_vwap,
        "upper1": round(last_vwap + last_std, 2),
        "upper2": round(last_vwap + 2 * last_std, 2),
        "lower1": round(last_vwap - last_std, 2),
        "lower2": round(last_vwap - 2 * last_std, 2),
    }


# ─── Volume Profile / POC ──────────────────────────────────────────────────────


def compute_volume_profile(
    df: pd.DataFrame, n_bars: int = 50, n_bins: int = 20
) -> dict:
    """
    Compute a simplified volume profile over the last `n_bars` candles.

    Returns the Point of Control (POC — the price level with the highest
    accumulated volume) and the value area (price band containing ~68% of volume).

    Returns
    -------
    dict with keys: poc, value_area_low, value_area_high
    """
    if len(df) < 5:
        return {
            "poc": float(df["close"].iloc[-1]),
            "value_area_low": float(df["low"].iloc[-1]),
            "value_area_high": float(df["high"].iloc[-1]),
        }

    subset = df.tail(min(n_bars, len(df))).copy()
    price_min = float(subset["low"].min())
    price_max = float(subset["high"].max())

    if price_max <= price_min:
        mid = (price_max + price_min) / 2.0
        return {
            "poc": round(mid, 2),
            "value_area_low": round(price_min, 2),
            "value_area_high": round(price_max, 2),
        }

    bin_size = (price_max - price_min) / n_bins
    vol_profile = [0.0] * n_bins

    for _, row in subset.iterrows():
        tp = (row["high"] + row["low"] + row["close"]) / 3.0
        bin_idx = min(int((tp - price_min) / bin_size), n_bins - 1)
        vol_profile[bin_idx] += float(row["volume"])

    poc_bin = vol_profile.index(max(vol_profile))
    poc = price_min + (poc_bin + 0.5) * bin_size

    # Value area: price bins covering ~68% of total volume
    total_vol = sum(vol_profile)
    target_vol = total_vol * 0.68
    cumulative = 0.0
    va_bins = []
    sorted_bins = sorted(range(n_bins), key=lambda x: vol_profile[x], reverse=True)
    for b in sorted_bins:
        if cumulative >= target_vol:
            break
        va_bins.append(b)
        cumulative += vol_profile[b]

    va_low = price_min + min(va_bins) * bin_size if va_bins else price_min
    va_high = price_min + (max(va_bins) + 1) * bin_size if va_bins else price_max

    return {
        "poc": round(poc, 2),
        "value_area_low": round(va_low, 2),
        "value_area_high": round(va_high, 2),
    }


# ─── Relative Volume ───────────────────────────────────────────────────────────


def compute_relative_volume(df: pd.DataFrame, period: int = 20) -> float:
    """Return current candle volume as a multiple of the rolling average."""
    avg = df["volume"].rolling(window=period).mean().iloc[-1]
    if pd.isna(avg) or avg <= 0:
        return 1.0
    return float(df["volume"].iloc[-1] / avg)
