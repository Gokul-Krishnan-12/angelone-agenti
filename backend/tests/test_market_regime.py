"""Tests for Market Regime Engine and Harmonized Trailing Stop-Loss."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.market_regime import (
    MarketRegimeResult,
    calculate_ker,
    classify_market_regime,
    is_trade_allowed_by_regime,
)
from backend.risk_manager import RiskManager


def _generate_synthetic_candles(
    n_bars: int = 60,
    trend: str = "bull",
    base_price: float = 1000.0,
    volatility: float = 5.0,
) -> pd.DataFrame:
    """Generate synthetic OHLCV candles with defined trend structure."""
    np.random.seed(42)
    closes = [base_price]

    for i in range(1, n_bars):
        if trend == "bull":
            drift = 4.0
        elif trend == "bear":
            drift = -4.0
        else:  # chop
            drift = 2.0 if i % 2 == 0 else -2.0

        noise = np.random.normal(0, volatility * 0.3)
        c = closes[-1] + drift + noise
        closes.append(max(c, 10.0))

    closes_arr = np.array(closes)
    highs = closes_arr + np.random.uniform(1.0, volatility, n_bars)
    lows = closes_arr - np.random.uniform(1.0, volatility, n_bars)
    opens = closes_arr - (closes_arr - np.roll(closes_arr, 1)) * 0.5
    opens[0] = base_price
    volumes = np.random.uniform(10_000, 50_000, n_bars)

    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes_arr,
            "volume": volumes,
        }
    )


def test_calculate_ker_trending_vs_choppy():
    """KER should be high (>0.7) for straight trend and low (<0.2) for choppy mean-reverting series."""
    # Monotonic trend
    trend_series = pd.Series([100.0 + i * 2.0 for i in range(25)])
    ker_trend = calculate_ker(trend_series, period=20)
    assert ker_trend >= 0.9, (
        f"Expected high KER for straight line trend, got {ker_trend}"
    )

    # Choppy zig-zag series (alternating +2, -2)
    chop_series = pd.Series([100.0 if i % 2 == 0 else 102.0 for i in range(25)])
    ker_chop = calculate_ker(chop_series, period=20)
    assert ker_chop <= 0.15, f"Expected low KER for choppy series, got {ker_chop}"


def test_classify_market_regime_bull_trend():
    """Sustained upward price movement should trigger TRENDING_BULL."""
    df = _generate_synthetic_candles(n_bars=80, trend="bull", volatility=2.0)
    result = classify_market_regime(df, min_adx=15.0, min_ker=0.20)

    assert result.regime == "TRENDING_BULL"
    assert result.plus_di > result.minus_di
    assert result.adx > 15.0


def test_classify_market_regime_bear_trend():
    """Sustained downward price movement should trigger TRENDING_BEAR."""
    df = _generate_synthetic_candles(n_bars=80, trend="bear", volatility=2.0)
    result = classify_market_regime(df, min_adx=15.0, min_ker=0.20)

    assert result.regime == "TRENDING_BEAR"
    assert result.minus_di > result.plus_di
    assert result.adx > 15.0


def test_classify_market_regime_choppy_range():
    """Sideways consolidation should trigger CHOPPY_RANGE."""
    df = _generate_synthetic_candles(n_bars=80, trend="chop", volatility=1.0)
    result = classify_market_regime(df, min_adx=20.0, min_ker=0.25)

    assert result.regime == "CHOPPY_RANGE"


def test_is_trade_allowed_blocks_choppy_breakouts():
    """In CHOPPY_RANGE regime, breakout strategies must be blocked to eliminate fee churn."""
    choppy_regime = MarketRegimeResult(
        regime="CHOPPY_RANGE",
        adx=14.5,
        plus_di=18.0,
        minus_di=19.0,
        ker=0.18,
        ema20=1000.0,
        ema50=1000.0,
        atr_pct=0.8,
        bb_width_pct=1.2,
        is_squeezed=True,
        summary="Choppy",
    )

    # Breakout strategy must be blocked
    allowed, reason = is_trade_allowed_by_regime(
        choppy_regime,
        direction="BUY",
        strategy_family="breakout",
        block_choppy_breakouts=True,
    )
    assert not allowed
    assert "Blocked by Market Regime" in reason

    # Non-breakout strategy (e.g. structure absorption) allowed if permitted
    allowed_struct, _ = is_trade_allowed_by_regime(
        choppy_regime,
        direction="BUY",
        strategy_family="structure",
        block_choppy_breakouts=True,
    )
    assert allowed_struct


def test_is_trade_allowed_blocks_counter_trend():
    """Strong bull regime must block counter-trend shorts."""
    bull_regime = MarketRegimeResult(
        regime="TRENDING_BULL",
        adx=28.0,
        plus_di=32.0,
        minus_di=11.0,
        ker=0.55,
        ema20=1050.0,
        ema50=1000.0,
        atr_pct=1.5,
        bb_width_pct=3.5,
        is_squeezed=False,
        summary="Bull trend",
    )

    allowed_buy, _ = is_trade_allowed_by_regime(
        bull_regime, direction="BUY", strategy_family="breakout"
    )
    assert allowed_buy

    allowed_sell, reason = is_trade_allowed_by_regime(
        bull_regime, direction="SELL", strategy_family="breakout"
    )
    assert not allowed_sell
    assert "Counter-trend SELL prohibited" in reason


def test_trailing_stop_loss_1r_cushion_and_breakeven():
    """Trailing SL must not activate below +1.0R profit, and must ratchet to at least breakeven once armed."""
    rm = RiskManager()
    trade = {
        "direction": "BUY",
        "entry_price": 100.0,
        "initial_sl": 98.0,  # 1R risk = 2.0 points
        "sl": 98.0,
        "high_water_mark": 100.0,
    }
    atr = 1.0  # distance = 2.0 * 1.0 = 2.0

    # 1. Price at 101.0 (+0.5R profit < 1.0R threshold) -> SL should NOT ratchet yet
    new_sl = rm.update_trailing_sl(
        trade, ltp=101.0, atr=atr, multiplier=2.0, cushion_r=1.0
    )
    assert new_sl is None
    assert trade["sl"] == 98.0

    # 2. Price hits 102.0 (+1.0R profit reached!) -> SL ratchets to at least breakeven (100.0)
    new_sl = rm.update_trailing_sl(
        trade, ltp=102.0, atr=atr, multiplier=2.0, cushion_r=1.0
    )
    assert new_sl is not None
    assert new_sl >= 100.0  # Guaranteed breakeven!
    trade["sl"] = new_sl

    # 3. Price runs to 104.0 (+2.0R full target range) -> SL ratchets to 104.0 - 2.0 = 102.0 (+1.0R locked profit!)
    new_sl = rm.update_trailing_sl(
        trade, ltp=104.0, atr=atr, multiplier=2.0, cushion_r=1.0
    )
    assert new_sl is not None
    assert new_sl == 102.0
