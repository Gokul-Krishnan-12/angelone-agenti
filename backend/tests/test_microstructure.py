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


def test_microstructure_opening_gap_exhaustion_buy():
    """Verify that a stock opening with >= 1.8% gap-up (exhaustion gap) is blocked for BUY breakouts."""
    from backend.microstructure import calculate_opening_gap
    # 2 days of 5m data
    d1 = pd.date_range("2026-09-17 15:00:00", periods=5, freq="5min")
    d2 = pd.date_range("2026-09-18 09:15:00", periods=10, freq="5min")

    df1 = pd.DataFrame({
        "open": [100.0] * 5,
        "high": [100.5] * 5,
        "low": [99.5] * 5,
        "close": [100.0] * 5,  # Prev close = 100.0
        "volume": [1000.0] * 5,
    }, index=d1)

    df2 = pd.DataFrame({
        "open": [102.5] + [102.8] * 9,  # Today open = 102.5 (+2.5% gap)
        "high": [103.5] * 10,
        "low": [102.0] * 10,
        "close": [103.0] * 10,
        "volume": [5000.0] * 10,
    }, index=d2)

    df = pd.concat([df1, df2])
    gap_pct, today_open, prev_close = calculate_opening_gap(df)
    assert gap_pct == 2.5
    assert today_open == 102.5
    assert prev_close == 100.0

    passed, reason, metrics = evaluate_microstructure_quality(
        df,
        direction="BUY",
        max_exhaustion_gap_pct=1.8,
        strategy_family="breakout",
        current_time=datetime.datetime(2026, 9, 18, 10, 0),
    )
    assert passed is False
    assert "Opening exhaustion gap-up" in reason


def test_microstructure_opening_gap_exhaustion_sell():
    """Verify that a stock opening with <= -1.8% gap-down is blocked for SELL breakdowns."""
    d1 = pd.date_range("2026-09-17 15:00:00", periods=5, freq="5min")
    d2 = pd.date_range("2026-09-18 09:15:00", periods=10, freq="5min")

    df1 = pd.DataFrame({
        "open": [200.0] * 5,
        "high": [200.5] * 5,
        "low": [199.5] * 5,
        "close": [200.0] * 5,  # Prev close = 200.0
        "volume": [1000.0] * 5,
    }, index=d1)

    df2 = pd.DataFrame({
        "open": [195.0] + [195.2] * 9,  # Today open = 195.0 (-2.5% gap)
        "high": [196.0] * 10,
        "low": [194.0] * 10,
        "close": [194.5] * 10,
        "volume": [5000.0] * 10,
    }, index=d2)

    df = pd.concat([df1, df2])
    passed, reason, metrics = evaluate_microstructure_quality(
        df,
        direction="SELL",
        max_exhaustion_gap_pct=1.8,
        strategy_family="breakout",
        current_time=datetime.datetime(2026, 9, 18, 10, 0),
    )
    assert passed is False
    assert "Opening exhaustion gap-down" in reason


def test_microstructure_normal_gap_passes():
    """Verify that moderate healthy gaps (< 1.8%) pass the exhaustion filter."""
    d1 = pd.date_range("2026-09-17 15:00:00", periods=5, freq="5min")
    d2 = pd.date_range("2026-09-18 09:15:00", periods=10, freq="5min")

    df1 = pd.DataFrame({
        "open": [100.0] * 5,
        "high": [100.5] * 5,
        "low": [99.5] * 5,
        "close": [100.0] * 5,
        "volume": [1000.0] * 5,
    }, index=d1)

    df2 = pd.DataFrame({
        "open": [100.8] + [101.0] * 8 + [101.0],  # 0.8% healthy gap
        "high": [101.5] * 10,
        "low": [100.5] * 10,
        "close": [101.2] * 9 + [101.4],  # clean close near high on trigger bar
        "volume": [5000.0] * 10,
    }, index=d2)

    df = pd.concat([df1, df2])
    passed, reason, metrics = evaluate_microstructure_quality(
        df,
        direction="BUY",
        max_exhaustion_gap_pct=1.8,
        strategy_family="breakout",
        current_time=datetime.datetime(2026, 9, 18, 10, 0),
    )
    assert passed is True


def test_microstructure_min_body_ratio_rejection():
    """Verify that a doji / climax wick with small body ratio (< 35%) is rejected."""
    # Create candle where body is only 20% of range
    timestamps = pd.date_range("2026-09-18 09:30:00", periods=25, freq="5min")
    data = []
    for _ in range(24):
        data.append({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000.0})
    # Trigger bar with candle range 10.0, body 2.0, upper wick 0.5 (5%), lower wick 7.5 (75%)
    # open 107.5, close 109.5, high 110.0, low 100.0 -> upper wick = 0.5/10 = 5%, body = 2/10 = 20% < 35%
    data.append({"open": 107.5, "high": 110.0, "low": 100.0, "close": 109.5, "volume": 2000.0})
    df = pd.DataFrame(data, index=timestamps)

    passed, reason, metrics = evaluate_microstructure_quality(
        df,
        direction="BUY",
        min_body_ratio=0.35,
        strategy_family="breakout",
        current_time=datetime.datetime(2026, 9, 18, 10, 0),
    )
    assert passed is False
    assert "Weak candle body" in reason
    assert metrics["body_ratio"] < 0.35


def test_microstructure_ema_stretch_guard():
    """Verify that extreme runaway bars stretched > 3.2x ATR from EMA20 are blocked."""
    timestamps = pd.date_range("2026-09-18 09:30:00", periods=25, freq="5min")
    data = []
    # Stable baseline around 100 with ATR ~ 1.0
    for _ in range(24):
        data.append({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000.0})
    # Climax vertical spike to 110 (10 points above EMA20, ATR is ~1.5 -> stretch ~ 6.6x ATR)
    data.append({"open": 100.0, "high": 110.0, "low": 99.5, "close": 110.0, "volume": 3000.0})
    df = pd.DataFrame(data, index=timestamps)

    passed, reason, metrics = evaluate_microstructure_quality(
        df,
        direction="BUY",
        max_ema_stretch_atr=3.2,
        strategy_family="breakout",
        current_time=datetime.datetime(2026, 9, 18, 10, 0),
    )
    assert passed is False
    assert "Breakout over-extended" in reason
    assert metrics["ema_stretch"] > 3.2


def test_microstructure_macro_trend_alignment():
    """Verify that counter-trend trades against the macro 100 EMA are prohibited."""
    timestamps = pd.date_range("2026-09-18 09:30:00", periods=70, freq="5min")
    # Steady downtrend: price drops from 200 down to 150
    prices = np.linspace(200, 150, 70)
    data = []
    for p in prices:
        data.append({"open": p, "high": p + 0.5, "low": p - 0.5, "close": p, "volume": 1000.0})
    # Trigger bar tries to BUY at 151 (far below macro EMA ~175)
    data[-1] = {"open": 150.0, "high": 152.0, "low": 149.5, "close": 151.5, "volume": 2500.0}
    df = pd.DataFrame(data, index=timestamps)

    passed, reason, metrics = evaluate_microstructure_quality(
        df,
        direction="BUY",
        require_macro_trend_aligned=True,
        strategy_family="breakout",
        current_time=datetime.datetime(2026, 9, 18, 10, 0),
    )
    assert passed is False
    assert "Counter-trend BUY prohibited under macro downtrend" in reason


