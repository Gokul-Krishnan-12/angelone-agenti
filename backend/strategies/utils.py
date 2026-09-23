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
    df: pd.DataFrame, n_bars: int = 80, n_bins: int = 30, anchor_session: bool = True
) -> dict:
    """
    Compute volume profile and Value Area (POC, VAH, VAL, and bin distributions).

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV candles.
    n_bars : int
        Lookback window if session anchoring is unavailable (default: 80).
    n_bins : int
        Granularity of price bins across the profile (default: 30).
    anchor_session : bool
        If True and session timestamps are detected, anchors profile from
        session open (09:15 IST) of current day.

    Returns
    -------
    dict with keys: poc, value_area_low, value_area_high, vol_profile,
                    bin_size, price_min, price_max, n_bins, poc_bin,
                    poc_volume, vah_bin, val_bin
    """
    if len(df) < 5:
        c = float(df["close"].iloc[-1])
        l = float(df["low"].iloc[-1])
        h = float(df["high"].iloc[-1])
        return {
            "poc": c,
            "value_area_low": l,
            "value_area_high": h,
            "vol_profile": [0.0] * n_bins,
            "bin_size": max(0.01, (h - l) / n_bins),
            "price_min": l,
            "price_max": h,
            "n_bins": n_bins,
            "poc_bin": 0,
            "poc_volume": 0.0,
            "vah_bin": n_bins - 1,
            "val_bin": 0,
        }

    # Module A: Anchored session detection (09:15 IST) vs. rolling fallback
    subset = None
    if anchor_session:
        # Check datetime column or index
        dt_series = None
        if "datetime" in df.columns:
            dt_series = pd.to_datetime(df["datetime"])
        elif "timestamp" in df.columns:
            dt_series = pd.to_datetime(df["timestamp"])
        elif isinstance(df.index, pd.DatetimeIndex):
            dt_series = pd.Series(df.index)

        if dt_series is not None and len(dt_series) > 0:
            last_date = dt_series.iloc[-1].date()
            same_day_mask = dt_series.apply(lambda x: x.date() == last_date)
            session_bars = df.loc[same_day_mask]
            if len(session_bars) >= 5:
                subset = session_bars.copy()

    if subset is None:
        subset = df.tail(min(n_bars, len(df))).copy()

    price_min = float(subset["low"].min())
    price_max = float(subset["high"].max())

    if price_max <= price_min:
        mid = (price_max + price_min) / 2.0
        return {
            "poc": round(mid, 2),
            "value_area_low": round(price_min, 2),
            "value_area_high": round(price_max, 2),
            "vol_profile": [0.0] * n_bins,
            "bin_size": 0.01,
            "price_min": price_min,
            "price_max": price_max,
            "n_bins": n_bins,
            "poc_bin": 0,
            "poc_volume": 0.0,
            "vah_bin": n_bins - 1,
            "val_bin": 0,
        }

    bin_size = (price_max - price_min) / n_bins
    vol_profile = [0.0] * n_bins

    for _, row in subset.iterrows():
        tp = (float(row["high"]) + float(row["low"]) + float(row["close"])) / 3.0
        bin_idx = min(int((tp - price_min) / bin_size), n_bins - 1)
        bin_idx = max(0, bin_idx)
        vol_profile[bin_idx] += float(row.get("volume", 1.0))

    poc_vol = max(vol_profile)
    poc_bin = vol_profile.index(poc_vol) if poc_vol > 0 else 0
    poc = price_min + (poc_bin + 0.5) * bin_size

    # Value area: price bins covering ~68% of total volume
    total_vol = sum(vol_profile)
    target_vol = total_vol * 0.68
    cumulative = 0.0
    va_bins = []
    sorted_bins = sorted(range(n_bins), key=lambda x: vol_profile[x], reverse=True)
    for b in sorted_bins:
        if cumulative >= target_vol and len(va_bins) > 0:
            break
        va_bins.append(b)
        cumulative += vol_profile[b]

    min_va_bin = min(va_bins) if va_bins else 0
    max_va_bin = max(va_bins) if va_bins else n_bins - 1

    va_low = price_min + min_va_bin * bin_size
    va_high = price_min + (max_va_bin + 1) * bin_size

    return {
        "poc": round(poc, 2),
        "value_area_low": round(va_low, 2),
        "value_area_high": round(va_high, 2),
        "vol_profile": vol_profile,
        "bin_size": bin_size,
        "price_min": price_min,
        "price_max": price_max,
        "n_bins": n_bins,
        "poc_bin": poc_bin,
        "poc_volume": poc_vol,
        "vah_bin": max_va_bin,
        "val_bin": min_va_bin,
    }


def is_lvn_vacuum(profile: dict, direction: str) -> bool:
    """
    Check if adjacent price bins beyond the Value Area boundary are Low Volume Nodes (LVNs).

    For VAH breakouts: inspect 2 bins immediately above VAH (vah_bin + 1, vah_bin + 2).
    For VAL breakdowns: inspect 2 bins immediately below VAL (val_bin - 1, val_bin - 2).

    Condition: Volume in adjacent bins must be < 40% of the POC volume.
    Entering directly into an overhead/underlying dense High Volume Node (HVN) is prohibited.
    """
    poc_vol = profile.get("poc_volume", 0.0)
    if poc_vol <= 0:
        return True

    vol_profile = profile.get("vol_profile", [])
    n_bins = profile.get("n_bins", len(vol_profile))
    threshold = 0.40 * poc_vol

    if direction == "BUY":
        vah_bin = profile.get("vah_bin", n_bins - 1)
        # Check up to 2 adjacent bins above VAH
        adjacent_bins = [vah_bin + 1, vah_bin + 2]
        checked = 0
        for b in adjacent_bins:
            if 0 <= b < n_bins:
                checked += 1
                if vol_profile[b] >= threshold:
                    return False  # Dense HVN absorption ahead
        return True
    else:
        val_bin = profile.get("val_bin", 0)
        # Check up to 2 adjacent bins below VAL
        adjacent_bins = [val_bin - 1, val_bin - 2]
        checked = 0
        for b in adjacent_bins:
            if 0 <= b < n_bins:
                checked += 1
                if vol_profile[b] >= threshold:
                    return False  # Dense HVN absorption below
        return True


def is_initiative_candle(candle: pd.Series | dict, direction: str) -> bool:
    """
    Validate initiative bar quality for structural auction breakouts.

    Criteria:
    - Body ratio: |close - open| / range >= 0.50
    - Close location:
        BUY:  (close - low) / range >= 0.75 (closes in upper 25%)
        SELL: (high - close) / range >= 0.75 (closes in lower 25%)
    """
    high = float(candle["high"])
    low = float(candle["low"])
    open_p = float(candle["open"])
    close_p = float(candle["close"])

    candle_range = max(0.001, high - low)
    body_ratio = abs(close_p - open_p) / candle_range

    if body_ratio < 0.50:
        return False

    if direction == "BUY":
        close_loc = (close_p - low) / candle_range
        return close_loc >= 0.75
    else:
        close_loc = (high - close_p) / candle_range
        return close_loc >= 0.75


# ─── Relative Volume ───────────────────────────────────────────────────────────


def compute_relative_volume(df: pd.DataFrame, period: int = 20) -> float:
    """Return current candle volume as a multiple of the rolling average."""
    avg = df["volume"].rolling(window=period).mean().iloc[-1]
    if pd.isna(avg) or avg <= 0:
        return 1.0
    return float(df["volume"].iloc[-1] / avg)
