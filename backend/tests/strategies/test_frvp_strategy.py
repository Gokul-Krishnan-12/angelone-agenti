"""Unit tests for High-Conviction Fixed Range Volume Profile (FRVP) Strategy & Auction Market Theory."""

import datetime
import numpy as np
import pandas as pd
import pytest

from backend.strategies.fixed_range_volume_profile import FixedRangeVolumeProfileStrategy
from backend.strategies.utils import (
    compute_volume_profile,
    is_initiative_candle,
    is_lvn_vacuum,
)
from backend.strategy_engine import calculate_pullback_limit_entry
from backend.tests.conftest import assert_valid_signal


def test_compute_volume_profile_basic():
    """Verify that compute_volume_profile correctly calculates POC, Value Area, and bin distribution."""
    n = 60
    closes = np.linspace(95, 105, n)
    highs = closes + 1.0
    lows = closes - 1.0
    opens = closes - 0.2
    # Heavy volume cluster around index 30 (price ~100)
    volumes = np.ones(n) * 1000.0
    volumes[28:33] = 50000.0  # Massive spike at ~100

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    vp = compute_volume_profile(df, n_bars=60, n_bins=30)
    assert "poc" in vp
    assert "value_area_low" in vp
    assert "value_area_high" in vp
    assert "vol_profile" in vp
    assert "poc_volume" in vp

    poc = vp["poc"]
    vah = vp["value_area_high"]
    val = vp["value_area_low"]

    # POC should be centered near 100
    assert 98.0 <= poc <= 102.0
    assert val <= poc <= vah
    assert val < vah


def test_compression_guard_zero_breakout_signals():
    """Verify Module B: Value Area Compression Guard suppresses breakout setups in tight chop."""
    # Build 45 bars of ultra-tight chop around 100.0 where VA width is tiny
    n = 45
    closes = [100.0 + (i % 2) * 0.05 for i in range(n)]
    highs = [c + 0.08 for c in closes]
    lows = [c - 0.08 for c in closes]
    opens = closes.copy()
    volumes = [1000.0] * n

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    strat = FixedRangeVolumeProfileStrategy()
    signals = strat.calculate_signals(df, "TCS")
    # All breakout setups must be suppressed because VA_Width is severely compressed
    breakouts = [s for s in signals if "BREAKOUT" in s.get("indicators", {}).get("setup", "")]
    assert len(breakouts) == 0


def test_frvp_vah_breakout_buy():
    """Verify bullish VAH breakout trigger on 2-bar acceptance, initiative candle, and volume expansion."""
    n = 40
    closes = [90.0 + (i % 6) * 3.0 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = closes.copy()
    volumes = [1000.0] * n

    # Bar t-2: inside value (100.0 <= VAH)
    opens.append(100.5)
    highs.append(101.0)
    lows.append(99.5)
    closes.append(100.0)
    volumes.append(1000.0)

    # Bar t-1: first close above VAH (~105.0)
    opens.append(100.5)
    highs.append(107.5)
    lows.append(100.0)
    closes.append(107.0)
    volumes.append(2500.0)

    # Bar t: 2-bar acceptance close > VAH, initiative bar (close in top 25%, body >= 50%), vol >= 1.25 * prev_vol
    opens.append(107.0)
    highs.append(111.0)
    lows.append(106.8)
    closes.append(110.8)
    volumes.append(3500.0)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    strat = FixedRangeVolumeProfileStrategy()
    # Mock bar_time to morning 10:15 IST (outside midday lull)
    strat._get_bar_time = lambda d, i=-1: datetime.time(10, 15)

    signals = strat.calculate_signals(df, "RELIANCE")

    assert len(signals) >= 1
    sig = signals[0]
    assert_valid_signal(sig)
    assert sig["direction"] == "BUY"
    assert sig["confidence"] >= 85
    assert sig["stopLoss"] < sig["entryPrice"]
    assert sig["target"] > sig["entryPrice"]
    assert sig["riskReward"] >= 1.8
    assert sig["indicators"]["setup"] == "VAH_BREAKOUT"
    assert sig["indicators"]["is_structural_target"] is False


def test_frvp_val_breakdown_sell():
    """Verify bearish VAL breakdown trigger on 2-bar acceptance, initiative candle, and volume expansion."""
    n = 40
    closes = [190.0 + (i % 6) * 3.0 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = closes.copy()
    volumes = [1000.0] * n

    # Bar t-2: inside value (200.0 >= VAL)
    opens.append(199.5)
    highs.append(200.5)
    lows.append(199.0)
    closes.append(200.0)
    volumes.append(1000.0)

    # Bar t-1: close below VAL (< 189.0)
    opens.append(199.5)
    highs.append(200.0)
    lows.append(187.0)
    closes.append(188.0)
    volumes.append(2500.0)

    # Bar t: 2-bar acceptance close < VAL, initiative bar (close in bottom 25%, body >= 50%), vol >= 1.25 * prev_vol
    opens.append(188.0)
    highs.append(188.5)
    lows.append(184.0)
    closes.append(184.5)
    volumes.append(3500.0)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    strat = FixedRangeVolumeProfileStrategy()
    strat._get_bar_time = lambda d, i=-1: datetime.time(10, 15)

    signals = strat.calculate_signals(df, "INFY")

    assert len(signals) >= 1
    sig = signals[0]
    assert_valid_signal(sig)
    assert sig["direction"] == "SELL"
    assert sig["confidence"] >= 85
    assert sig["stopLoss"] > sig["entryPrice"]
    assert sig["target"] < sig["entryPrice"]
    assert sig["riskReward"] >= 1.8
    assert sig["indicators"]["setup"] == "VAL_BREAKDOWN"


def test_frvp_vah_sweep_rejection_setup4():
    """Verify Setup 4 (SELL — VAH Sweep & Rejection) targeting strictly POC with RR >= 1.3."""
    n = 45
    closes = [95.0 + (i % 5) * 2.5 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = closes.copy()
    volumes = [1000.0] * n
    for idx in range(10, 30):
        volumes[idx] = 20000.0

    # Sweep bar: sweeps above VAH (~102.5), high = 105.0, upper wick >= 40%, closes back at 102.4 (< VAH)
    opens.append(103.5)
    highs.append(105.0)
    lows.append(102.0)
    closes.append(102.4)
    volumes.append(1500.0)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    strat = FixedRangeVolumeProfileStrategy()
    strat._get_bar_time = lambda d, i=-1: datetime.time(11, 00)
    signals = strat.calculate_signals(df, "HDFCBANK")

    sweeps = [s for s in signals if s.get("indicators", {}).get("setup") == "VAH_REJECTION"]
    assert len(sweeps) >= 1
    sig = sweeps[0]
    assert sig["direction"] == "SELL"
    assert sig["indicators"]["is_structural_target"] is True
    # Target must be strictly POC
    assert sig["target"] == sig["indicators"]["poc"]
    assert sig["riskReward"] >= 1.3


def test_frvp_val_sweep_rejection_setup3():
    """Verify Setup 3 (BUY — VAL Sweep & Rejection) targeting strictly POC with RR >= 1.3."""
    n = 45
    closes = [196.0 + (i % 5) * 2.5 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = closes.copy()
    volumes = [5000.0] * n
    for idx in range(n):
        if (idx % 5) >= 3:
            volumes[idx] = 10000.0

    # VAL is ~195.7. Sweep bar sweeps beneath VAL: low = 194.5 (<= VAL - 0.2*ATR)
    # open = 195.8, close = 196.2 (> open and > VAL), high = 196.5
    opens.append(195.8)
    highs.append(196.5)
    lows.append(194.5)
    closes.append(196.2)
    volumes.append(1500.0)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    strat = FixedRangeVolumeProfileStrategy()
    strat._get_bar_time = lambda d, i=-1: datetime.time(11, 00)
    signals = strat.calculate_signals(df, "ICICIBANK")

    sweeps = [s for s in signals if s.get("indicators", {}).get("setup") == "VAL_REJECTION"]
    assert len(sweeps) >= 1
    sig = sweeps[0]
    assert sig["direction"] == "BUY"
    assert sig["indicators"]["is_structural_target"] is True
    assert sig["target"] == sig["indicators"]["poc"]
    assert sig["riskReward"] >= 1.3


def test_midday_value_lull_disables_breakouts():
    """Verify that during 11:30 - 13:30 IST, Breakout Setups 1 & 2 are suppressed."""
    n = 40
    closes = [90.0 + (i % 6) * 3.0 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = closes.copy()
    volumes = [1000.0] * n

    opens.append(100.5)
    highs.append(101.0)
    lows.append(99.5)
    closes.append(100.0)
    volumes.append(1000.0)

    opens.append(100.5)
    highs.append(107.5)
    lows.append(100.0)
    closes.append(107.0)
    volumes.append(2500.0)

    opens.append(107.0)
    highs.append(111.0)
    lows.append(106.8)
    closes.append(110.8)
    volumes.append(3500.0)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    strat = FixedRangeVolumeProfileStrategy()
    # Mock midday lull time: 12:15 IST
    strat._get_bar_time = lambda d, i=-1: datetime.time(12, 15)

    signals = strat.calculate_signals(df, "RELIANCE")
    breakouts = [s for s in signals if "BREAKOUT" in s.get("indicators", {}).get("setup", "")]
    assert len(breakouts) == 0, "Breakout setups must be disabled during 11:30-13:30 IST midday lull"


def test_pullback_limit_entry_with_poc():
    """Verify that calculate_pullback_limit_entry anchors to POC/Value Area without chasing."""
    n = 35
    closes = [500.0] * n
    highs = [502.0] * n
    lows = [498.0] * n
    opens = [500.0] * n
    volumes = [10000.0] * n  # Heavy POC at ~500.0

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

    assert entry_price < 515.0
    assert entry_price >= 500.0


def test_frvp_dalton_80_rule_short():
    """Verify Jim Dalton's 80% Rule Bearish Re-entry setup targeting prior POC and VAL."""
    # Build Day 1 (yesterday): Value Area around 100.0 (VAH ~103, VAL ~97, POC ~100)
    day1_times = pd.date_range("2026-09-22 09:15", "2026-09-22 15:30", freq="5min")
    n1 = len(day1_times)
    d1_closes = [100.0 + (i % 5) * 1.0 - 2.0 for i in range(n1)]
    d1_df = pd.DataFrame({
        "datetime": day1_times,
        "open": d1_closes,
        "high": [c + 1.0 for c in d1_closes],
        "low": [c - 1.0 for c in d1_closes],
        "close": d1_closes,
        "volume": [2000.0] * n1,
    })

    # Day 2 (today): Opens above pdVAH (~104.0), then accepts back inside pdVAH with 2 closes
    day2_times = pd.date_range("2026-09-23 09:15", periods=6, freq="5min")
    # bar 0: opens high outside pdVAH (106.0)
    # bar 1: drops to 104.0
    # bar 2: close inside pdVAH (101.5 < pdVAH)
    # bar 3: close inside pdVAH (101.0 < pdVAH, > pdPOC ~100)
    d2_closes = [106.0, 104.5, 101.8, 101.2, 101.0, 100.8]
    d2_df = pd.DataFrame({
        "datetime": day2_times,
        "open": [106.5, 105.0, 103.0, 102.0, 101.5, 101.0],
        "high": [107.0, 105.5, 103.5, 102.5, 101.8, 101.2],
        "low": [105.5, 103.5, 101.5, 101.0, 100.8, 100.5],
        "close": d2_closes,
        "volume": [3000.0] * len(day2_times),
    })

    full_df = pd.concat([d1_df, d2_df], ignore_index=True)
    strat = FixedRangeVolumeProfileStrategy()
    strat._get_bar_time = lambda d, i=-1: datetime.time(10, 0)
    signals = strat.calculate_signals(full_df, "TCS")

    dalton_signals = [s for s in signals if s.get("indicators", {}).get("setup") == "DALTON_80_RULE_SHORT"]
    assert len(dalton_signals) >= 1
    sig = dalton_signals[0]
    assert sig["direction"] == "SELL"
    assert sig["target"] <= sig["entryPrice"]
    assert sig["stopLoss"] > sig["entryPrice"]
    assert sig["indicators"]["is_structural_target"] is True


def test_frvp_dalton_80_rule_long():
    """Verify Jim Dalton's 80% Rule Bullish Re-entry setup targeting prior POC and VAH."""
    day1_times = pd.date_range("2026-09-22 09:15", "2026-09-22 15:30", freq="5min")
    n1 = len(day1_times)
    d1_closes = [200.0 + (i % 5) * 1.5 - 3.0 for i in range(n1)]
    d1_df = pd.DataFrame({
        "datetime": day1_times,
        "open": d1_closes,
        "high": [c + 1.2 for c in d1_closes],
        "low": [c - 1.2 for c in d1_closes],
        "close": d1_closes,
        "volume": [2000.0] * n1,
    })

    # Day 2: Opens below pdVAL (~196.0), then accepts back inside pdVAL with 2 closes
    day2_times = pd.date_range("2026-09-23 09:15", periods=5, freq="5min")
    d2_closes = [193.0, 194.0, 195.0, 197.0, 197.4]
    d2_df = pd.DataFrame({
        "datetime": day2_times,
        "open": [192.5, 193.5, 194.5, 195.5, 197.0],
        "high": [193.5, 194.5, 195.5, 197.2, 197.8],
        "low": [192.0, 193.0, 194.0, 195.0, 196.8],
        "close": d2_closes,
        "volume": [3000.0] * len(day2_times),
    })

    full_df = pd.concat([d1_df, d2_df], ignore_index=True)
    strat = FixedRangeVolumeProfileStrategy()
    strat._get_bar_time = lambda d, i=-1: datetime.time(10, 0)
    signals = strat.calculate_signals(full_df, "INFY")

    dalton_signals = [s for s in signals if s.get("indicators", {}).get("setup") == "DALTON_80_RULE_LONG"]
    assert len(dalton_signals) >= 1
    sig = dalton_signals[0]
    assert sig["direction"] == "BUY"
    assert sig["target"] >= sig["entryPrice"]
    assert sig["stopLoss"] < sig["entryPrice"]
    assert sig["indicators"]["is_structural_target"] is True


def test_frvp_virgin_poc_overhead_resistance_filter():
    """Verify that a VAH breakout running directly into prior day virgin POC is blocked."""
    # Build prior day where POC is at 111.0 (virgin, untested today)
    day1_times = pd.date_range("2026-09-22 09:15", "2026-09-22 15:30", freq="5min")
    n1 = len(day1_times)
    d1_df = pd.DataFrame({
        "datetime": day1_times,
        "open": [108.0] * n1,
        "high": [112.0] * n1,
        "low": [107.0] * n1,
        "close": [111.0] * n1,
        "volume": [50000.0] * n1,  # Heavy volume cluster at 111.0
    })

    # Today: VAH breakout candidate closes at 110.8 (within 0.5% below virgin POC 111.0)
    n = 35
    day2_times = pd.date_range("2026-09-23 09:15", periods=n+3, freq="5min")
    closes = [100.0 + (i % 6) * 1.0 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = closes.copy()
    volumes = [1000.0] * n

    # t-2
    opens.append(104.0); highs.append(105.0); lows.append(103.5); closes.append(104.0); volumes.append(1000.0)
    # t-1
    opens.append(104.5); highs.append(108.5); lows.append(104.0); closes.append(108.0); volumes.append(2500.0)
    # t: breakout candle closes at 110.8, right into virgin POC 111.0
    opens.append(108.0); highs.append(111.0); lows.append(107.8); closes.append(110.8); volumes.append(4000.0)

    d2_df = pd.DataFrame({
        "datetime": day2_times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    full_df = pd.concat([d1_df, d2_df], ignore_index=True)
    strat = FixedRangeVolumeProfileStrategy()
    strat._get_bar_time = lambda d, i=-1: datetime.time(10, 15)

    signals = strat.calculate_signals(full_df, "RELIANCE")
    breakouts = [s for s in signals if s.get("indicators", {}).get("setup") == "VAH_BREAKOUT"]
    # Must be blocked by vPOC overhead resistance filter!
    assert len(breakouts) == 0
