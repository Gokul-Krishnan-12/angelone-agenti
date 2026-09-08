"""Unit tests for Central Pivot Range (CPR) & Key Level Confluence Strategy."""

import pandas as pd

from backend.strategies.cpr_breakout_reversal import CPRBreakoutReversalStrategy

SYMBOL = "RELIANCE"


def _make_base_df(
    n: int = 25, price: float = 1000.0, volume: float = 100_000.0
) -> pd.DataFrame:
    """Creates a base DataFrame with stable candles."""
    return pd.DataFrame(
        {
            "open": [price] * n,
            "high": [price + 3.0] * n,
            "low": [price - 3.0] * n,
            "close": [price] * n,
            "volume": [volume] * n,
        }
    )


def test_cpr_math_calculation():
    """Verify standard formula calculations for Pivot, BC, TC, R1, S1."""
    h, l_val, c = 105.0, 95.0, 103.0
    levels = CPRBreakoutReversalStrategy.calculate_cpr_levels(h, l_val, c)

    assert levels["p"] == 101.0  # (105 + 95 + 103) / 3
    assert levels["bc"] == 100.0  # (105 + 95) / 2
    assert levels["tc"] == 102.0  # 2P - BC = 202 - 100
    assert levels["cpr_top"] == 102.0
    assert levels["cpr_bottom"] == 100.0
    assert levels["r1"] == 107.0  # 2P - L = 202 - 95
    assert levels["s1"] == 97.0  # 2P - H = 202 - 105
    assert levels["pdh"] == 105.0
    assert levels["pdl"] == 95.0


def test_insufficient_bars():
    strat = CPRBreakoutReversalStrategy()
    df = _make_base_df(n=10)
    signals = strat.calculate_signals(df, SYMBOL)
    assert signals == []


def test_narrow_cpr_bullish_breakout():
    strat = CPRBreakoutReversalStrategy()
    # 30 bars base at 1000
    df = _make_base_df(n=30, price=1000.0, volume=50_000.0)

    # In df.iloc[:20], reference session: high=1001.0, low=999.0, close=1000.0
    # CPR: P=1000, BC=1000, TC=1000 -> CPR Width = 0.0% (Narrow CPR)
    # Penultimate candle (-2) closes at 1000 (inside CPR)
    df.loc[df.index[-2], "close"] = 1000.0

    # Final candle (-1) breaks out decisively above CPR Top (1000.0) with strong volume
    df.loc[df.index[-1], "open"] = 1000.5
    df.loc[df.index[-1], "high"] = 1015.0
    df.loc[df.index[-1], "low"] = 1000.0
    df.loc[df.index[-1], "close"] = 1014.0
    df.loc[df.index[-1], "volume"] = 150_000.0  # 3x mean volume

    signals = strat.calculate_signals(df, SYMBOL)
    assert len(signals) == 1
    sig = signals[0]
    assert sig["direction"] == "BUY"
    assert sig["confidence"] >= 70
    assert sig["entryPrice"] == 1014.0
    assert sig["stopLoss"] < sig["entryPrice"]
    assert sig["target"] > sig["entryPrice"]
    assert sig["riskReward"] >= 1.5


def test_narrow_cpr_bearish_breakdown():
    strat = CPRBreakoutReversalStrategy()
    df = _make_base_df(n=30, price=1000.0, volume=50_000.0)

    df.loc[df.index[-2], "close"] = 1000.0

    # Final candle breaks down below CPR Bottom (1000.0) with strong volume
    df.loc[df.index[-1], "open"] = 999.5
    df.loc[df.index[-1], "high"] = 1000.0
    df.loc[df.index[-1], "low"] = 985.0
    df.loc[df.index[-1], "close"] = 986.0
    df.loc[df.index[-1], "volume"] = 150_000.0  # 3x volume

    signals = strat.calculate_signals(df, SYMBOL)
    assert len(signals) == 1
    sig = signals[0]
    assert sig["direction"] == "SELL"
    assert sig["confidence"] >= 70
    assert sig["entryPrice"] == 986.0
    assert sig["stopLoss"] > sig["entryPrice"]
    assert sig["target"] < sig["entryPrice"]


def test_low_volume_breakout_rejected():
    strat = CPRBreakoutReversalStrategy()
    df = _make_base_df(n=30, price=1000.0, volume=50_000.0)

    df.loc[df.index[-2], "close"] = 1000.0

    # Breakout price move but with below-average volume
    df.loc[df.index[-1], "open"] = 1000.5
    df.loc[df.index[-1], "high"] = 1015.0
    df.loc[df.index[-1], "low"] = 1000.0
    df.loc[df.index[-1], "close"] = 1014.0
    df.loc[df.index[-1], "volume"] = 20_000.0  # Lower than mean volume

    signals = strat.calculate_signals(df, SYMBOL)
    assert signals == []


def test_wide_cpr_bullish_support_bounce():
    strat = CPRBreakoutReversalStrategy()
    df = _make_base_df(n=30, price=1000.0, volume=50_000.0)

    # Create wide CPR in reference window
    df.loc[df.index[19], "high"] = 1030.0
    df.loc[df.index[19], "low"] = 970.0
    df.loc[df.index[19], "close"] = 1025.0
    # H=1030, L=970, C=1025 -> P = 3025/3 = 1008.33, BC = 2000/2 = 1000.0, TC = 2016.67 - 1000 = 1016.67
    # CPR Top = 1016.67, CPR Bottom = 1000.0, CPR Width % = 1.65% (Wide CPR)

    # Current candle dips near CPR Bottom (1000.0) with long lower wick (pin bar)
    df.loc[df.index[-1], "open"] = 1005.0
    df.loc[df.index[-1], "high"] = 1008.0
    df.loc[df.index[-1], "low"] = 998.0  # dips below 1000
    df.loc[df.index[-1], "close"] = 1007.0  # strong close above
    df.loc[df.index[-1], "volume"] = 80_000.0  # high volume
    # range = 1008 - 998 = 10.0; lower wick = 1005 - 998 = 7.0 (70% wick ratio)

    signals = strat.calculate_signals(df, SYMBOL)
    assert len(signals) == 1
    sig = signals[0]
    assert sig["direction"] == "BUY"
    assert sig["confidence"] >= 70
    assert sig["indicators"]["setup"] == "cpr_support_bounce"
