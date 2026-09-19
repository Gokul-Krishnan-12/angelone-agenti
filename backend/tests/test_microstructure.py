import datetime
import numpy as np
import pandas as pd
import pytest

from backend.microstructure import evaluate_microstructure_quality


def create_synthetic_candle_df(
    n_bars: int = 25,
    base_price: float = 1000.0,
    rvol_multiplier: float = 1.5,
    wick_ratio: float = 0.1,
    direction: str = "BUY",
    ker_trend: bool = True,
) -> pd.DataFrame:
    """Create synthetic candle DataFrame for testing microstructure gates."""
    timestamps = pd.date_range("2026-09-18 09:30:00", periods=n_bars, freq="5min")
    data = []
    curr_p = base_price
    base_vol = 10000.0

    for i in range(n_bars - 1):
        delta = 2.0 if ker_trend else (1.5 if i % 2 == 0 else -1.5)
        o = curr_p
        c = curr_p + delta
        h = max(o, c) + 1.0
        l = min(o, c) - 1.0
        v = base_vol
        data.append({"open": o, "high": h, "low": l, "close": c, "volume": v})
        curr_p = c

    # Trigger bar (last bar)
    last_o = curr_p
    if direction == "BUY":
        last_c = last_o + 5.0
        candle_range = 10.0
        # Rejection wick control
        last_h = last_c + candle_range * wick_ratio
        last_l = last_o - (candle_range * (1 - wick_ratio) - 5.0)
    else:
        last_c = last_o - 5.0
        candle_range = 10.0
        last_h = last_o + (candle_range * (1 - wick_ratio) - 5.0)
        last_l = last_c - candle_range * wick_ratio

    last_v = base_vol * rvol_multiplier
    data.append({
        "open": last_o,
        "high": last_h,
        "low": last_l,
        "close": last_c,
        "volume": last_v
    })

    df = pd.DataFrame(data, index=timestamps)
    return df


def test_microstructure_rvol_rejection():
    # Low volume trigger bar (0.8x RVOL)
    df = create_synthetic_candle_df(rvol_multiplier=0.8)
    passed, reason, metrics = evaluate_microstructure_quality(
        df, "BUY", min_rvol=1.2, current_time=datetime.datetime(2026, 9, 18, 10, 0)
    )
    assert passed is False
    assert "Low RVOL" in reason
    assert metrics["rvol"] < 1.2


def test_microstructure_rvol_pass():
    # Strong volume surge trigger bar (1.8x RVOL)
    df = create_synthetic_candle_df(rvol_multiplier=1.8, wick_ratio=0.1, ker_trend=True)
    passed, reason, metrics = evaluate_microstructure_quality(
        df, "BUY", min_rvol=1.2, current_time=datetime.datetime(2026, 9, 18, 10, 0)
    )
    assert passed is True
    assert metrics["rvol"] >= 1.2


def test_microstructure_upper_wick_rejection_buy():
    # BUY breakout with long upper rejection wick (40% of range)
    df = create_synthetic_candle_df(rvol_multiplier=1.8, wick_ratio=0.40, direction="BUY")
    passed, reason, metrics = evaluate_microstructure_quality(
        df, "BUY", max_wick_ratio=0.25, current_time=datetime.datetime(2026, 9, 18, 10, 0)
    )
    assert passed is False
    assert "High rejection upper wick" in reason
    assert metrics["wick_ratio"] > 0.25


def test_microstructure_lower_wick_rejection_sell():
    # SELL breakdown with long lower rejection wick (35% of range)
    df = create_synthetic_candle_df(rvol_multiplier=1.8, wick_ratio=0.35, direction="SELL")
    passed, reason, metrics = evaluate_microstructure_quality(
        df, "SELL", max_wick_ratio=0.25, current_time=datetime.datetime(2026, 9, 18, 10, 0)
    )
    assert passed is False
    assert "High rejection lower wick" in reason
    assert metrics["wick_ratio"] > 0.25


def test_microstructure_ker_chop_rejection():
    # Sideways oscillating chop (KER ~ 0.15)
    df = create_synthetic_candle_df(rvol_multiplier=2.0, wick_ratio=0.1, ker_trend=False)
    passed, reason, metrics = evaluate_microstructure_quality(
        df, "BUY", min_ker=0.30, current_time=datetime.datetime(2026, 9, 18, 10, 0)
    )
    assert passed is False
    assert "Low local efficiency" in reason
    assert metrics["local_ker"] < 0.30


def test_microstructure_midday_lull_guard():
    # At 12:15 IST (midday lull), RVOL = 1.4x is insufficient (requires 2.2x)
    df = create_synthetic_candle_df(rvol_multiplier=1.4, wick_ratio=0.1, ker_trend=True)
    midday_time = datetime.datetime(2026, 9, 18, 12, 15)
    passed, reason, _ = evaluate_microstructure_quality(
        df, "BUY", min_rvol=1.2, midday_rvol_boost=2.2, current_time=midday_time
    )
    assert passed is False
    assert "midday lull" in reason

    # At 12:15 IST, extraordinary institutional surge (2.5x RVOL) passes
    df_surge = create_synthetic_candle_df(rvol_multiplier=2.5, wick_ratio=0.1, ker_trend=True)
    passed_surge, _, metrics_surge = evaluate_microstructure_quality(
        df_surge, "BUY", min_rvol=1.2, midday_rvol_boost=2.2, current_time=midday_time
    )
    assert passed_surge is True
    assert metrics_surge["is_midday"] is True
