"""Unit tests for Fixed Range Volume Profile (FRVP) Strategy & Auction Market Theory levels."""

import numpy as np
import pandas as pd
import pytest

from backend.strategies.fixed_range_volume_profile import FixedRangeVolumeProfileStrategy
from backend.strategies.utils import compute_volume_profile
from backend.strategy_engine import calculate_pullback_limit_entry
from backend.tests.conftest import assert_valid_signal, build_candles


def test_compute_volume_profile_basic():
    """Verify that compute_volume_profile correctly calculates POC and Value Area."""
    # Build a DataFrame with heavy volume at price 100
    n = 40
    closes = np.linspace(95, 105, n)
    highs = closes + 1.0
    lows = closes - 1.0
    opens = closes - 0.2
    # Heavy volume cluster around index 20 (price ~100)
    volumes = np.ones(n) * 1000.0
    volumes[18:22] = 50000.0  # Massive spike at ~100

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    vp = compute_volume_profile(df, n_bars=40, n_bins=20)
    assert "poc" in vp
    assert "value_area_low" in vp
    assert "value_area_high" in vp

    poc = vp["poc"]
    vah = vp["value_area_high"]
    val = vp["value_area_low"]

    # POC should be centered near 100
    assert 98.0 <= poc <= 102.0
    assert val <= poc <= vah
    assert val < vah


def test_frvp_vah_breakout_buy():
    """Verify bullish VAH breakout trigger on volume surge."""
    # Build baseline consolidating around 100
    n = 35
    closes = [100.0 + (i % 3 - 1) * 0.5 for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    opens = closes.copy()
    volumes = [1000.0] * n

    # Current bar breaks above recent high / VAH with 3x volume surge
    opens.append(100.5)
    closes.append(104.0)  # Breakout
    highs.append(104.5)
    lows.append(100.2)
    volumes.append(4000.0)  # Volume surge

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    strat = FixedRangeVolumeProfileStrategy()
    signals = strat.calculate_signals(df, "RELIANCE")

    assert len(signals) >= 1
    sig = signals[0]
    assert_valid_signal(sig)
    assert sig["direction"] == "BUY"
    assert sig["confidence"] >= 80
    assert sig["stopLoss"] < sig["entryPrice"]
    assert sig["target"] > sig["entryPrice"]
    assert sig["riskReward"] >= 2.0
    assert "VAH" in sig["reasoning"] or "breakout" in sig["reasoning"].lower()


def test_frvp_val_breakdown_sell():
    """Verify bearish VAL breakdown trigger on volume surge."""
    # Build baseline consolidating around 200
    n = 35
    closes = [200.0 + (i % 3 - 1) * 0.5 for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    opens = closes.copy()
    volumes = [1000.0] * n

    # Current bar breaks down below recent low / VAL with volume surge
    opens.append(199.5)
    closes.append(195.0)  # Breakdown
    highs.append(199.8)
    lows.append(194.5)
    volumes.append(4500.0)  # Volume surge

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    strat = FixedRangeVolumeProfileStrategy()
    signals = strat.calculate_signals(df, "INFY")

    assert len(signals) >= 1
    sig = signals[0]
    assert_valid_signal(sig)
    assert sig["direction"] == "SELL"
    assert sig["stopLoss"] > sig["entryPrice"]
    assert sig["target"] < sig["entryPrice"]
    assert sig["riskReward"] >= 2.0
    assert "VAL" in sig["reasoning"] or "breakdown" in sig["reasoning"].lower()


def test_pullback_limit_entry_with_poc():
    """Verify that calculate_pullback_limit_entry anchors to POC/Value Area without chasing."""
    n = 35
    closes = [500.0] * n
    highs = [502.0] * n
    lows = [498.0] * n
    opens = [500.0] * n
    volumes = [10000.0] * n  # Heavy POC at ~500.0

    # Breakout bar to 515.0
    opens.append(501.0)
    highs.append(516.0)
    lows.append(500.5)
    closes.append(515.0)
    volumes.append(5000.0)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    entry_price = calculate_pullback_limit_entry(
        df=df, direction="BUY", breakout_level=502.0
    )

    # Entry price should pull back below the 515 close toward the breakout / POC support level
    assert entry_price < 515.0
    assert entry_price >= 500.0
