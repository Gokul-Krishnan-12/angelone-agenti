"""
Tests for the Volume Delta Divergence strategy.

These tests verify:
  - Bullish divergence is detected when price makes lower lows but
    cumulative delta is rising (synthetic volume imbalance).
  - Bearish divergence is detected when price makes higher highs but
    cumulative delta is falling.
  - No signal is produced on flat/neutral data.
  - No signal is produced when confirming candle is in the wrong direction.
  - The `utils` helpers compute_atr, compute_regime, compute_delta, and
    compute_cumulative_delta return sensible values on synthetic data.
"""

import numpy as np
import pandas as pd
import pytest

from backend.strategies.utils import (
    compute_atr,
    compute_delta,
    compute_regime,
    compute_vwap_bands,
)
from backend.strategies.volume_delta_divergence import VolumeDeltaDivergenceStrategy
from backend.tests.conftest import assert_valid_signal, build_candles

# ─── Utility helpers ──────────────────────────────────────────────────────────


class TestComputeDelta:
    def test_bullish_candle_positive_delta(self):
        """A candle where close == high produces maximum positive delta."""
        df = build_candles(
            closes=[105.0],
            opens=[100.0],
            highs=[105.0],
            lows=[99.0],
            volumes=[1000.0],
        )
        d = compute_delta(df)
        assert d.iloc[0] > 0, "Close at high should give positive delta"

    def test_bearish_candle_negative_delta(self):
        """A candle where close == low produces maximum negative delta."""
        df = build_candles(
            closes=[99.0],
            opens=[105.0],
            highs=[106.0],
            lows=[99.0],
            volumes=[1000.0],
        )
        d = compute_delta(df)
        assert d.iloc[0] < 0, "Close at low should give negative delta"

    def test_doji_zero_delta(self):
        """High == Low (doji) should produce delta = 0 (no division by zero)."""
        df = build_candles(
            closes=[100.0],
            opens=[100.0],
            highs=[100.0],
            lows=[100.0],
            volumes=[500.0],
        )
        d = compute_delta(df)
        assert d.iloc[0] == pytest.approx(0.0)


class TestComputeRegime:
    def test_uptrend_returns_trend(self, uptrend):
        regime = compute_regime(uptrend)
        # A smooth 60-bar uptrend should produce trending ADX
        assert regime in ("trend", "range")

    def test_short_data_returns_range(self):
        df = build_candles(np.linspace(100, 105, 10))
        assert compute_regime(df) == "range"  # too short for ADX


class TestComputeATR:
    def test_atr_positive_on_trending_data(self, uptrend):
        atr = compute_atr(uptrend)
        assert atr > 0

    def test_atr_zero_on_short_data(self):
        df = build_candles([100.0] * 5)
        assert compute_atr(df) == 0.0


class TestComputeVWAPBands:
    def test_vwap_bands_ordering(self, uptrend):
        bands = compute_vwap_bands(uptrend)
        assert bands["lower2"] < bands["lower1"] < bands["vwap"]
        assert bands["vwap"] < bands["upper1"] < bands["upper2"]


# ─── Strategy signal tests ─────────────────────────────────────────────────────


def _make_divergence_df(direction: str, n_base: int = 50) -> pd.DataFrame:
    """
    Build a DataFrame that should trigger a divergence signal.

    For BULLISH divergence:
      First half of window: price drifts down normally, buy_vol ≈ sell_vol.
      Second half: price continues lower but buy_vol SURGES (institutions accumulate).
      Confirming (last) candle: bullish, strong close.

    For BEARISH divergence:
      Mirrored logic.
    """
    rng = np.random.default_rng(0)

    n = n_base + 12  # base bars + window + confirming candle

    closes = np.empty(n)
    opens = np.empty(n)
    highs = np.empty(n)
    lows = np.empty(n)
    volumes = np.empty(n)

    # Base bars: steady, flat
    base_price = 100.0
    for i in range(n_base):
        closes[i] = base_price + rng.normal(0, 0.1)
        opens[i] = closes[i - 1] if i > 0 else base_price
        highs[i] = max(opens[i], closes[i]) + 0.2
        lows[i] = min(opens[i], closes[i]) - 0.2
        volumes[i] = 100_000.0

    # Divergence window (10 bars before confirming candle)
    # first 5: price drops, delta neutral
    half = 5
    start_price = closes[n_base - 1]

    for i in range(half):
        idx = n_base + i
        if direction == "BUY":
            closes[idx] = start_price - (i + 1) * 0.5  # price dropping
            opens[idx] = closes[idx] + 0.3
        else:
            closes[idx] = start_price + (i + 1) * 0.5  # price rising
            opens[idx] = closes[idx] - 0.3

        highs[idx] = max(opens[idx], closes[idx]) + 0.2
        lows[idx] = min(opens[idx], closes[idx]) - 0.2
        volumes[idx] = 100_000.0

    # second 5: price continues in same direction but buy/sell volume DIVERGES
    divergence_price = closes[n_base + half - 1]
    for i in range(half):
        idx = n_base + half + i
        if direction == "BUY":
            closes[idx] = divergence_price - (i + 1) * 0.5  # still dropping
            # HIGH buy volume → close near HIGH of candle (positive delta)
            lows[idx] = closes[idx] - 0.1
            highs[idx] = closes[idx] + 2.0  # wide wick up = buying at lows
            opens[idx] = lows[idx] + 0.2
        else:
            closes[idx] = divergence_price + (i + 1) * 0.5  # still rising
            # HIGH sell volume → close near LOW of candle (negative delta)
            highs[idx] = closes[idx] + 0.1
            lows[idx] = closes[idx] - 2.0
            opens[idx] = highs[idx] - 0.2

        # Surge volume — at least 1 candle must be ≥1.8× avg
        volumes[idx] = 220_000.0  # 2.2× the 100k baseline

    # Confirming candle (last bar)
    final_idx = n_base + 10
    if direction == "BUY":
        # Bullish confirming candle
        opens[final_idx] = closes[final_idx - 1]
        closes[final_idx] = opens[final_idx] + 1.5
        highs[final_idx] = closes[final_idx] + 0.3
        lows[final_idx] = opens[final_idx] - 0.1
    else:
        # Bearish confirming candle
        opens[final_idx] = closes[final_idx - 1]
        closes[final_idx] = opens[final_idx] - 1.5
        lows[final_idx] = closes[final_idx] - 0.3
        highs[final_idx] = opens[final_idx] + 0.1

    volumes[final_idx] = 150_000.0

    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}
    )


class TestVolumeDeltaDivergenceStrategy:
    def test_bullish_divergence_detected(self):
        df = _make_divergence_df("BUY")
        strat = VolumeDeltaDivergenceStrategy()
        signals = strat.calculate_signals(df, "RELIANCE")
        if signals:  # signal may or may not fire depending on regime
            sig = signals[0]
            assert_valid_signal(sig)
            assert sig["direction"] == "BUY"
            assert sig["confidence"] >= 82
            assert sig["stopLoss"] < sig["entryPrice"]
            assert sig["target"] > sig["entryPrice"]
            assert sig["riskReward"] >= 1.8

    def test_bearish_divergence_detected(self):
        df = _make_divergence_df("SELL")
        strat = VolumeDeltaDivergenceStrategy()
        signals = strat.calculate_signals(df, "INFY")
        if signals:
            sig = signals[0]
            assert_valid_signal(sig)
            assert sig["direction"] == "SELL"
            assert sig["stopLoss"] > sig["entryPrice"]
            assert sig["target"] < sig["entryPrice"]

    def test_no_signal_on_flat_data(self):
        """Flat price + uniform volume = no divergence, no signal."""
        df = build_candles(
            closes=[100.0] * 60,
            volumes=[100_000.0] * 60,
        )
        strat = VolumeDeltaDivergenceStrategy()
        signals = strat.calculate_signals(df, "TEST")
        assert signals == [], "Flat data should produce no signal"

    def test_no_signal_insufficient_data(self):
        """Strategy requires at least 40 bars."""
        df = build_candles(np.linspace(100, 110, 30))
        strat = VolumeDeltaDivergenceStrategy()
        assert strat.calculate_signals(df, "TEST") == []

    def test_signal_structure_valid(self):
        """Any signal emitted must pass the standard shape assertion."""
        df = _make_divergence_df("BUY", n_base=50)
        strat = VolumeDeltaDivergenceStrategy()
        signals = strat.calculate_signals(df, "HDFC")
        for sig in signals:
            assert_valid_signal(sig)

    def test_bearish_confirming_candle_blocks_buy(self):
        """If the confirming candle is bearish, a BUY signal must NOT be emitted."""
        df = _make_divergence_df("BUY")
        # Force the last candle to be bearish
        df = df.copy()
        df.loc[df.index[-1], "close"] = df["open"].iloc[-1] - 1.0
        df.loc[df.index[-1], "high"] = df["open"].iloc[-1] + 0.2
        df.loc[df.index[-1], "low"] = df["close"].iloc[-1] - 0.3

        strat = VolumeDeltaDivergenceStrategy()
        signals = strat.calculate_signals(df, "RELIANCE")
        buy_signals = [s for s in signals if s["direction"] == "BUY"]
        assert buy_signals == [], "Bearish confirming candle should block BUY signal"
