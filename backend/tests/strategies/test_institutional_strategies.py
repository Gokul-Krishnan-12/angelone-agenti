import numpy as np
import pandas as pd

from backend.strategies.cmf_accumulation import CMFAccumulationStrategy
from backend.strategies.institutional_absorption import (
    InstitutionalAbsorptionStrategy,
)
from backend.strategies.order_block_fvg import OrderBlockFVGStrategy
from backend.tests.conftest import assert_valid_signal, build_candles


def _one(signals):
    assert len(signals) == 1, f"expected exactly 1 signal, got {len(signals)}"
    assert_valid_signal(signals[0])
    return signals[0]


class TestInstitutionalAbsorption:
    def test_bullish_absorption_trigger(self):
        # 30 bars to give ADX > 20 (trending baseline required by the new gate)
        import numpy as np

        n = 32
        closes = list(np.linspace(100.0, 103.0, n))  # gentle uptrend for ADX
        opens = list(closes)
        highs = [c * 1.002 for c in closes]
        lows = [c * 0.998 for c in closes]
        volumes = [1000.0] * n

        # Bar -3 (absorption candle): 3× volume, deep lower wick (hammer)
        idx_abs = -3
        volumes[idx_abs] = 3000.0
        lows[idx_abs] = closes[idx_abs] - 10.0  # deep dip → lower wick ≥ 45%
        opens[idx_abs] = closes[idx_abs] - 0.1
        closes[idx_abs] = closes[idx_abs]  # closes near top of range
        highs[idx_abs] = closes[idx_abs] + 0.5

        # Bar -2 (intermediate): neutral
        # Bar -1 (confirming): bullish, close in top 35% of absorption candle range
        abs_range = highs[idx_abs] - lows[idx_abs]
        top_65pct = lows[idx_abs] + abs_range * 0.65
        closes[-1] = top_65pct + 0.5  # above the 65% mark → in top 35%
        opens[-1] = closes[-1] - 0.3  # close > open = bullish
        highs[-1] = closes[-1] + 0.2
        lows[-1] = opens[-1] - 0.1

        df = pd.DataFrame(
            {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )

        strat = InstitutionalAbsorptionStrategy()
        signals = strat.calculate_signals(df, "RELIANCE")
        sig = _one(signals)
        assert sig["direction"] == "BUY"
        assert sig["confidence"] >= 80
        assert sig["stopLoss"] < sig["entryPrice"]

    def test_bearish_distribution_trigger(self):
        import numpy as np

        n = 32
        closes = list(np.linspace(103.0, 100.0, n))  # gentle downtrend for ADX
        opens = list(closes)
        highs = [c * 1.002 for c in closes]
        lows = [c * 0.998 for c in closes]
        volumes = [1000.0] * n

        # Bar -3 (distribution candle): 3× volume, long upper wick (shooting star)
        idx_abs = -3
        volumes[idx_abs] = 3000.0
        highs[idx_abs] = closes[idx_abs] + 10.0  # high surge rejected
        opens[idx_abs] = closes[idx_abs] + 0.1
        lows[idx_abs] = closes[idx_abs] - 0.5

        # Bar -1 (confirming): bearish, close in bottom 35% of distribution candle range
        abs_range = highs[idx_abs] - lows[idx_abs]
        bottom_35pct = highs[idx_abs] - abs_range * 0.65
        closes[-1] = bottom_35pct - 0.5  # below the 35% boundary
        opens[-1] = closes[-1] + 0.3  # close < open = bearish
        highs[-1] = opens[-1] + 0.1
        lows[-1] = closes[-1] - 0.2

        df = pd.DataFrame(
            {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )

        strat = InstitutionalAbsorptionStrategy()
        signals = strat.calculate_signals(df, "INFY")
        sig = _one(signals)
        assert sig["direction"] == "SELL"
        assert sig["confidence"] >= 80
        assert sig["stopLoss"] > sig["entryPrice"]

    def test_no_signal_on_normal_volume(self):
        df = build_candles([100.0] * 35)
        strat = InstitutionalAbsorptionStrategy()
        assert strat.calculate_signals(df, "TEST") == []


class TestOrderBlockFVG:
    def test_bullish_fvg_retest_and_bounce(self):
        # 25 bars: baseline, displacement leaving gap, followed by retest
        n = 25
        closes = [100.0] * n
        opens = [100.0] * n
        highs = [101.0] * n
        lows = [99.0] * n
        volumes = [1000.0] * n

        # Candle -3 (displacement): huge move up with volume
        highs[-4] = 101.0  # c1 high
        opens[-3] = 101.0
        highs[-3] = 107.0
        lows[-3] = 101.0
        closes[-3] = 106.0
        volumes[-3] = 2500.0  # 2.5x volume

        # Candle -2: low is above c1 high, creating a gap [101.0 to 103.0]
        opens[-2] = 106.0
        lows[-2] = 103.0  # c3 low > c1 high -> gap [101.0, 103.0]
        highs[-2] = 108.0
        closes[-2] = 107.0

        # Candle -1 (latest candle): dips into gap and closes higher
        opens[-1] = 103.0
        lows[-1] = 101.5  # retested gap
        closes[-1] = 104.5  # closed above midpoint of gap
        highs[-1] = 105.0

        df = pd.DataFrame(
            {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )

        strat = OrderBlockFVGStrategy()
        signals = strat.calculate_signals(df, "TCS")
        sig = _one(signals)
        assert sig["direction"] == "BUY"
        assert sig["target"] > sig["entryPrice"]

    def test_bearish_fvg_retest_and_drop(self):
        n = 25
        closes = [100.0] * n
        opens = [100.0] * n
        highs = [101.0] * n
        lows = [99.0] * n
        volumes = [1000.0] * n

        # Candle -3: displacement down with high volume
        lows[-4] = 99.0  # c1 low
        opens[-3] = 99.0
        highs[-3] = 99.0
        lows[-3] = 93.0
        closes[-3] = 94.0
        volumes[-3] = 2500.0

        # Candle -2: high is below c1 low, creating gap [97.0 to 99.0]
        opens[-2] = 94.0
        highs[-2] = 97.0  # c3 high < c1 low -> gap [97.0, 99.0]
        lows[-2] = 92.0
        closes[-2] = 93.0

        # Candle -1 (latest): tests up into gap and closes lower
        opens[-1] = 97.0
        highs[-1] = 98.5  # retested gap
        closes[-1] = 95.5  # closed below midpoint
        lows[-1] = 95.0

        df = pd.DataFrame(
            {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )

        strat = OrderBlockFVGStrategy()
        signals = strat.calculate_signals(df, "HDFCBANK")
        sig = _one(signals)
        assert sig["direction"] == "SELL"
        assert sig["target"] < sig["entryPrice"]


class TestCMFAccumulation:
    def test_bullish_cmf_accumulation(self):
        # Generate series where close is at the top of the candle range (producing high positive CMF)
        n = 30
        closes = np.linspace(100, 115, n)
        highs = closes + 0.05
        lows = closes - 1.0
        opens = closes - 0.8
        volumes = [1000.0] * (n - 1) + [3000.0]  # surge on last

        df = pd.DataFrame(
            {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )

        strat = CMFAccumulationStrategy()
        signals = strat.calculate_signals(df, "SBIN")
        sig = _one(signals)
        assert sig["direction"] == "BUY"
        assert sig["indicators"]["cmf"] > 0
