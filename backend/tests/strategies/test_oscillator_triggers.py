"""Behavioral (trigger) tests for the momentum / oscillator / trend strategies.

Oscillator crossovers (MACD, TSI, Stochastic, StochRSI, RSI, Awesome, ADX,
Supertrend, PSAR, Keltner, MFI) don't fire on simple linear ramps because the
smoothed lines move in lockstep. A sine wave produces genuine crossovers, so
these series are a sine slice cut so the signal lands on the final bar. Each
`_seed` was found against the real indicator math and is asserted here so a
regression in a strategy's condition breaks the test.
"""

import numpy as np

from backend.scanner import scanner
from backend.tests.conftest import assert_valid_signal, build_candles

STRAT = scanner.strategies


def _t(n):
    return np.arange(n)


def _sine(period, n, base=100.0, amp=8.0):
    """A sine-wave close series of length n."""
    return list(base + amp * np.sin(2 * np.pi * _t(n) / period))


def _one(strategy_id, df, direction):
    sigs = STRAT[strategy_id].calculate_signals(df.copy(), "T")
    assert len(sigs) == 1, f"{strategy_id}: expected 1 signal, got {sigs}"
    sig = sigs[0]
    assert_valid_signal(sig)
    assert sig["direction"] == direction
    return sig


class TestMACDCross:
    def test_buy_on_bullish_cross(self):
        _one("macd_cross", build_candles(_sine(20, 42)), "BUY")

    def test_sell_on_bearish_cross(self):
        _one("macd_cross", build_candles(_sine(30, 45)), "SELL")


class TestTSICross:
    def test_buy_on_zero_line_cross_up(self):
        _one("tsi_cross", build_candles(_sine(20, 41)), "BUY")

    def test_sell_on_zero_line_cross_down(self):
        _one("tsi_cross", build_candles(_sine(30, 50)), "SELL")


class TestStochasticReversal:
    def test_buy_on_oversold_cross(self):
        _one("stochastic_reversal", build_candles(_sine(30, 24)), "BUY")

    def test_sell_on_overbought_cross(self):
        _one("stochastic_reversal", build_candles(_sine(20, 27)), "SELL")


class TestStochRSI:
    def test_buy_on_cross_above_lower_band(self):
        _one("stoc_rsi", build_candles(_sine(20, 40)), "BUY")

    def test_sell_on_cross_below_upper_band(self):
        _one("stoc_rsi", build_candles(_sine(30, 42)), "SELL")


class TestRSIReversal:
    def test_buy_on_recovery_above_30_with_price_over_vwap(self):
        _one("rsi_reversal", build_candles(_sine(40, 36)), "BUY")


class TestAwesomeOscillator:
    def test_buy_on_zero_cross_up(self):
        # Deep decline then a long recovery pushes AO from below to above zero.
        closes = list(np.linspace(120, 100, 30)) + list(np.linspace(100, 110, 10))
        _one("awesome_oscillator", build_candles(closes), "BUY")


class TestADXMomentum:
    def test_buy_on_di_cross_in_strong_trend(self):
        # V-bottom: sharp reversal with a strong (ADX > 25) directional move.
        closes = list(np.linspace(120, 100, 30)) + list(np.linspace(100, 110, 2))
        _one("adx_momentum", build_candles(closes), "BUY")


class TestSupertrend:
    def test_buy_on_bullish_flip_with_adx(self):
        # Down-then-up shape gives ADX > 25 and a Supertrend flip.
        # The flip (last) bar must have volume ≥ 1.5× avg and close in top 40% of range.
        closes = list(np.linspace(120, 100, 30)) + list(np.linspace(100, 110, 2))
        # Last bar: volume surge (2× baseline 100 k), ensure strong close position
        volumes = [100_000] * 31 + [200_000]
        highs = list(
            np.maximum(np.array(closes[:-1]), np.array(closes[1:])) * 1.002
        ) + [closes[-1] * 1.002]
        lows = list(np.minimum(np.array(closes[:-1]), np.array(closes[1:])) * 0.998) + [
            closes[-2] * 0.998
        ]
        # Final bar: open low, close high to guarantee top-40% close
        opens = list(closes)
        opens[-1] = closes[-1] * 0.994  # bearish-then-strong-close
        highs[-1] = closes[-1] * 1.004
        lows[-1] = closes[-1] * 0.994
        _one(
            "supertrend",
            build_candles(closes, opens=opens, highs=highs, lows=lows, volumes=volumes),
            "BUY",
        )


class TestParabolicSAR:
    def test_buy_on_flip_below_price(self):
        closes = list(np.linspace(120, 100, 30)) + list(np.linspace(100, 110, 2))
        _one("psar_trend", build_candles(closes), "BUY")


class TestKeltnerBreakout:
    def test_buy_on_break_above_upper_band(self):
        closes = list(np.linspace(120, 100, 30)) + list(np.linspace(100, 110, 2))
        _one("keltner_breakout", build_candles(closes), "BUY")


class TestMFIExhaustion:
    def test_buy_on_bounce_from_oversold(self):
        closes = list(np.linspace(120, 100, 30)) + list(np.linspace(100, 102, 4))
        _one("mfi_exhaustion", build_candles(closes), "BUY")


class TestVWAPBounce:
    def test_buy_on_bounce_off_vwap_in_uptrend(self):
        # Build a base DataFrame, compute its VWAP, then construct the final two
        # bars to land precisely within 0.15% of that VWAP so the proximity gate
        # passes.  Both bars are bullish (close > open) for positive delta.
        import numpy as np
        import pandas as pd
        from ta.volume import VolumeWeightedAveragePrice

        # 50-bar base: 40 flat + 10 gentle rise → EMA 9 > EMA 21, RSI > 40
        base_closes = [100.0] * 40 + list(np.linspace(100.0, 101.5, 10))
        base_opens = [100.0] * 40 + list(np.linspace(99.8, 101.3, 10))
        base_highs = [max(o, c) * 1.001 for o, c in zip(base_opens, base_closes)]
        base_lows = [min(o, c) * 0.999 for o, c in zip(base_opens, base_closes)]
        base_vols = [100_000.0] * 50
        base_df = pd.DataFrame(
            {
                "open": base_opens,
                "high": base_highs,
                "low": base_lows,
                "close": base_closes,
                "volume": base_vols,
            }
        )

        # Compute actual VWAP from the base
        actual_vwap = float(
            VolumeWeightedAveragePrice(
                high=base_df["high"],
                low=base_df["low"],
                close=base_df["close"],
                volume=base_df["volume"],
            )
            .volume_weighted_average_price()
            .iloc[-1]
        )

        # Construct the final 2 bars right at VWAP (within 0.05%)
        vwap_price = actual_vwap * 1.0004  # 0.04 % above → well within 0.15 %
        p1_open = vwap_price - 0.05
        p1_close = vwap_price
        p2_open = vwap_price
        p2_close = vwap_price + 0.05  # green candle → positive delta

        closes = base_closes + [p1_close, p2_close]
        opens = base_opens + [p1_open, p2_open]
        highs = base_highs + [
            max(p1_open, p1_close) * 1.001,
            max(p2_open, p2_close) * 1.001,
        ]
        lows = base_lows + [
            min(p1_open, p1_close) * 0.999,
            min(p2_open, p2_close) * 0.999,
        ]
        volumes = base_vols + [100_000, 130_000]  # last bar 1.3×

        _one(
            "vwap_bounce",
            build_candles(closes, opens=opens, highs=highs, lows=lows, volumes=volumes),
            "BUY",
        )
