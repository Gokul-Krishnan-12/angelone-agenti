"""
Microstructural Quality Gate for Intraday Cash Equities.

Evaluates critical microstructural dimensions on the trigger candle to prevent false breakouts:
1. RVOL (Relative Volume Surge): Requires trigger bar volume >= 1.2x of its 20-period moving average.
2. Rejection Wick Ratio: Rejects bars where counter-trend rejection wick > 25% of the total candle range.
3. Local Efficiency Ratio (KER): Requires 20-period Kaufman Efficiency Ratio >= 0.30 to block sideways chop traps.
4. Midday Liquidity Guard: Enforces higher RVOL threshold (>= 2.2x) during the 11:30 - 13:15 IST midday lull.
5. Opening Gap Exhaustion Guard: Blocks breakout/trend chasing on stocks that opened with >= 1.8% gap.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np


def calculate_opening_gap(df: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Compute opening gap percentage, today's open price, and previous day close price.

    Returns
    -------
    Tuple[float, float, float]
        (gap_pct, today_open, prev_close)
        gap_pct is positive for gap-up, negative for gap-down.
    """
    if df is None or len(df) < 2:
        return 0.0, 0.0, 0.0

    dates_arr = None
    for col in ["date", "datetime", "timestamp"]:
        if col in df.columns:
            try:
                dates_arr = pd.to_datetime(df[col]).dt.date.values
                break
            except Exception:
                pass
    if dates_arr is None and isinstance(df.index, pd.DatetimeIndex):
        dates_arr = df.index.date

    if dates_arr is not None and len(dates_arr) >= 2:
        unique_dates = np.unique(dates_arr)
        if len(unique_dates) >= 2:
            prev_date = unique_dates[-2]
            curr_date = unique_dates[-1]
            prev_close = float(df[dates_arr == prev_date]["close"].iloc[-1])
            today_open = float(df[dates_arr == curr_date]["open"].iloc[0])
            if prev_close > 0:
                gap_pct = ((today_open - prev_close) / prev_close) * 100.0
                return round(gap_pct, 2), today_open, prev_close

    today_open = float(df["open"].iloc[0])
    return 0.0, today_open, today_open


def evaluate_microstructure_quality(
    df: pd.DataFrame,
    direction: str,
    min_rvol: float = 1.2,
    min_ker: float = 0.30,
    max_wick_ratio: float = 0.25,
    midday_rvol_boost: float = 2.2,
    max_exhaustion_gap_pct: float = 1.8,
    strategy_family: str = "",
    current_time: Optional[datetime.datetime] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Evaluate trigger bar microstructural health and exhaustion risk.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV candles for the symbol.
    direction : str
        'BUY' or 'SELL'.
    min_rvol : float
        Minimum Relative Volume multiplier required (default 1.2x).
    min_ker : float
        Minimum 20-period Kaufman Efficiency Ratio (default 0.30).
    max_wick_ratio : float
        Maximum counter-trend rejection wick ratio (default 0.25).
    midday_rvol_boost : float
        Required RVOL during 11:30 - 13:15 IST midday lull (default 2.2x).
    max_exhaustion_gap_pct : float
        Maximum opening gap percentage beyond which breakout/trend trades are blocked (default 1.8%).
    strategy_family : str
        Signal family name (e.g. 'breakout', 'trend', 'reversal').
    current_time : Optional[datetime.datetime]
        Explicit timestamp to evaluate (useful for backtests).

    Returns
    -------
    Tuple[bool, str, Dict[str, Any]]
        (passed, reason, metrics_dict)
    """
    if df is None or len(df) < 5:
        return True, "Insufficient bars for microstructure evaluation", {}

    # ── 1. Opening Gap Exhaustion Guard ────────────────────────────────────
    gap_pct, today_open, prev_close = calculate_opening_gap(df)
    is_exhaustion_candidate = strategy_family in ("breakout", "trend", "momentum", "")

    if max_exhaustion_gap_pct > 0 and is_exhaustion_candidate:
        if direction == "BUY" and gap_pct >= max_exhaustion_gap_pct:
            return (
                False,
                f"Opening exhaustion gap-up (+{gap_pct:.2f}% >= +{max_exhaustion_gap_pct:.1f}% limit)",
                {"gap_pct": gap_pct, "today_open": today_open, "prev_close": prev_close},
            )
        elif direction == "SELL" and gap_pct <= -max_exhaustion_gap_pct:
            return (
                False,
                f"Opening exhaustion gap-down ({gap_pct:.2f}% <= -{max_exhaustion_gap_pct:.1f}% limit)",
                {"gap_pct": gap_pct, "today_open": today_open, "prev_close": prev_close},
            )

    # ── 2. Relative Volume (RVOL) ──────────────────────────────────────────
    if "volume" in df.columns and len(df) >= 10:
        vol_series = df["volume"].astype(float)
        lookback = min(20, len(vol_series) - 1)
        if lookback >= 5:
            vol_ma = vol_series.iloc[-lookback - 1 : -1].mean()
            curr_vol = vol_series.iloc[-1]
            rvol = float(curr_vol / vol_ma) if vol_ma > 0 else 1.0
        else:
            rvol = 1.0
    else:
        rvol = 1.0

    # ── 3. Time of Day & Midday Liquidity Guard ────────────────────────────
    hour = 10.0  # default morning hour if undetermined
    if current_time is not None:
        hour = current_time.hour + current_time.minute / 60.0
    elif isinstance(df.index, pd.DatetimeIndex) and len(df.index) > 0:
        ts = df.index[-1]
        hour = ts.hour + ts.minute / 60.0
    elif "datetime" in df.columns:
        try:
            ts = pd.to_datetime(df["datetime"].iloc[-1])
            hour = ts.hour + ts.minute / 60.0
        except Exception:
            pass
    elif "date" in df.columns:
        try:
            ts = pd.to_datetime(df["date"].iloc[-1])
            hour = ts.hour + ts.minute / 60.0
        except Exception:
            pass
    else:
        try:
            # Current time in Asia/Kolkata
            now_ist = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            )
            hour = now_ist.hour + now_ist.minute / 60.0
        except Exception:
            pass

    is_midday = 11.5 <= hour <= 13.25  # 11:30 to 13:15 IST
    effective_min_rvol = max(min_rvol, midday_rvol_boost) if is_midday else min_rvol

    if min_rvol > 0 and rvol < effective_min_rvol:
        lull_tag = " [midday lull 11:30-13:15 IST]" if is_midday else ""
        return (
            False,
            f"Low RVOL ({rvol:.2f}x < {effective_min_rvol:.2f}x{lull_tag})",
            {"rvol": round(rvol, 2), "is_midday": is_midday, "gap_pct": gap_pct},
        )

    # ── 4. Rejection Wick Filter ───────────────────────────────────────────
    high = float(df["high"].iloc[-1])
    low = float(df["low"].iloc[-1])
    open_p = float(df["open"].iloc[-1])
    close_p = float(df["close"].iloc[-1])
    candle_range = high - low

    if candle_range > 0:
        if direction == "BUY":
            upper_wick = high - max(open_p, close_p)
            wick_ratio = upper_wick / candle_range
        else:
            lower_wick = min(open_p, close_p) - low
            wick_ratio = lower_wick / candle_range
    else:
        wick_ratio = 0.0

    if max_wick_ratio > 0 and wick_ratio > max_wick_ratio:
        wick_type = "upper" if direction == "BUY" else "lower"
        return (
            False,
            f"High rejection {wick_type} wick ({wick_ratio:.1%} > {max_wick_ratio:.1%})",
            {"rvol": round(rvol, 2), "wick_ratio": round(wick_ratio, 3), "gap_pct": gap_pct},
        )

    # ── 5. Local Kaufman Efficiency Ratio (KER) ────────────────────────────
    if len(df) >= 15:
        lookback_ker = min(20, len(df) - 1)
        direction_dist = abs(float(df["close"].iloc[-1]) - float(df["close"].iloc[-lookback_ker - 1]))
        volatility = float(df["close"].diff().abs().iloc[-lookback_ker:].sum())
        local_ker = (direction_dist / volatility) if volatility > 0 else 0.0
    else:
        local_ker = 0.5

    if min_ker > 0 and local_ker < min_ker:
        return (
            False,
            f"Low local efficiency / sideways chop (KER {local_ker:.2f} < {min_ker:.2f})",
            {
                "rvol": round(rvol, 2),
                "wick_ratio": round(wick_ratio, 3),
                "local_ker": round(local_ker, 3),
                "gap_pct": gap_pct,
            },
        )

    metrics = {
        "rvol": round(rvol, 2),
        "wick_ratio": round(wick_ratio, 3),
        "local_ker": round(local_ker, 3),
        "is_midday": is_midday,
        "gap_pct": gap_pct,
        "today_open": today_open,
        "prev_close": prev_close,
    }
    return True, "Passed microstructural quality gate", metrics
