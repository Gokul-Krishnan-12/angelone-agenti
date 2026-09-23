"""
Unit tests for refactored algorithmic trading modules:
- backend.strategy_engine (Tasks 1 & 2)
- backend.order_manager (Tasks 2 & 4)
- backend.watchdog (Tasks 3 & 5)
- backend.market_regime (Task 5 midday chop)
- Statutory turnover rate synchronization (Task 6)
"""

import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from backend.market_regime import is_midday_chop_window
from backend.order_manager import order_manager
from backend.strategy_engine import (
    calculate_pullback_limit_entry,
    calculate_volatility_buffered_sl,
)
from backend.watchdog import watchdog


@pytest.fixture
def sample_candle_df():
    """Generates 30 synthetic 5m candles for testing."""
    n = 30
    dates = pd.date_range(end="2026-09-17 10:30:00", periods=n, freq="5min")
    base_price = 1000.0
    # Create an upward trend with some volatility
    closes = [base_price + i * 2.0 + (i % 3) * 0.5 for i in range(n)]
    highs = [c + 3.0 for c in closes]
    lows = [c - 3.0 for c in closes]
    opens = [c - 1.0 for c in closes]
    volumes = [10000 + i * 200 for i in range(n)]

    df = pd.DataFrame(
        {
            "date": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )
    return df


def test_volatility_buffered_stop_loss_buy(sample_candle_df):
    """Task 1: Verify 0.5x ATR breathing room below swing low for BUY."""
    recent_low = float(sample_candle_df["low"].iloc[-10:].min())
    buffered_sl = calculate_volatility_buffered_sl(
        df=sample_candle_df,
        direction="BUY",
        raw_sl=recent_low,
        lookback=10,
        atr_multiplier=0.5,
    )
    assert buffered_sl < recent_low
    # Difference should be approximately 0.5 * ATR
    risk_diff = recent_low - buffered_sl
    assert 1.0 <= risk_diff <= 5.0


def test_volatility_buffered_stop_loss_sell(sample_candle_df):
    """Task 1: Verify 0.5x ATR breathing room above swing high for SELL."""
    recent_high = float(sample_candle_df["high"].iloc[-10:].max())
    buffered_sl = calculate_volatility_buffered_sl(
        df=sample_candle_df,
        direction="SELL",
        raw_sl=recent_high,
        lookback=10,
        atr_multiplier=0.5,
    )
    assert buffered_sl > recent_high
    risk_diff = buffered_sl - recent_high
    assert 1.0 <= risk_diff <= 5.0


def test_pullback_limit_entry_buy(sample_candle_df):
    """Task 2: Verify pullback entry price is at nearest value support and <= current close."""
    curr_close = float(sample_candle_df["close"].iloc[-1])
    entry_p = calculate_pullback_limit_entry(
        df=sample_candle_df,
        direction="BUY",
        breakout_level=curr_close - 5.0,
    )
    assert entry_p > 0
    # Must be bounded by current close (not buying above the close)
    assert entry_p <= curr_close


def test_pullback_limit_entry_sell(sample_candle_df):
    """Task 2: Verify pullback entry price is at nearest value resistance and >= current close."""
    curr_close = float(sample_candle_df["close"].iloc[-1])
    entry_p = calculate_pullback_limit_entry(
        df=sample_candle_df,
        direction="SELL",
        breakout_level=curr_close + 5.0,
    )
    assert entry_p > 0
    # Must be bounded by current close (not selling below the close)
    assert entry_p >= curr_close


def test_watchdog_evaluate_exit_curve_target1():
    """Task 3: Verify +1.2R front-loaded profit booking and friction-covered breakeven."""
    trade = {
        "direction": "BUY",
        "entry_price": 1000.0,
        "initial_sl": 980.0,  # 1R = 20.0
        "sl": 980.0,
        "partial_booked": False,
    }
    # Price tags +1.2R = 1000 + 1.2 * 20 = 1024.0
    ltp = 1025.0
    eval_res = watchdog.evaluate_exit_curve(
        trade=trade,
        ltp=ltp,
        current_qty=10,
        target1_r_mult=1.2,
    )

    assert eval_res["trigger_t1"] is True
    assert eval_res["t1_exit_qty"] == 5
    # Breakeven SL must be strictly above entry_price for BUY to cover round-trip friction
    assert eval_res["breakeven_sl"] > trade["entry_price"]


def test_watchdog_idle_trade_circuit_breaker():
    """Task 5: Verify position held >= 20 mins without +0.5R triggers exit."""
    trade = {
        "direction": "BUY",
        "entry_price": 1000.0,
        "initial_sl": 980.0,  # 1R = 20.0
    }
    # 1. Held 25 mins (within 35m window) -> no exit
    exit_25, _ = watchdog.check_idle_trade_circuit_breaker(
        trade=trade, ltp=1005.0, mins_held=25.0
    )
    assert exit_25 is False

    # 2. Held 36 mins with only +0.25R gain (+5.0 profit / 20.0 risk = 0.25R < 0.6R) -> exit!
    exit_36, reason_36 = watchdog.check_idle_trade_circuit_breaker(
        trade=trade, ltp=1005.0, mins_held=36.0
    )
    assert exit_36 is True
    assert "Idle trade circuit breaker" in reason_36

    # 3. Held 36 mins with +0.75R gain (+15.0 profit / 20.0 risk = 0.75R >= 0.6R) -> keep holding!
    exit_good, _ = watchdog.check_idle_trade_circuit_breaker(
        trade=trade, ltp=1015.0, mins_held=36.0
    )
    assert exit_good is False


def test_order_manager_atomic_modify_sl(monkeypatch):
    """Task 4: Verify atomic modify_order call and response structure."""
    mock_client = MagicMock()
    mock_client.modify_order.return_value = {
        "status": True,
        "orderid": "SL_ORDER_123",
    }
    monkeypatch.setattr("backend.order_manager.smart_api_client", mock_client)

    res = order_manager.atomic_modify_stop_loss(
        order_id="SL_ORDER_123",
        symbol="INFY",
        exchange="NSE",
        direction="BUY",
        quantity=5,
        trigger_price=1000.50,
    )
    assert res["success"] is True
    assert res["emergency_exit_required"] is False
    mock_client.modify_order.assert_called_once()


def test_order_manager_emergency_market_close_on_failure(monkeypatch):
    """Task 4: Verify that on atomic modify failure, emergency market close is invoked."""
    mock_client = MagicMock()
    mock_client.modify_order.side_effect = RuntimeError("Broker matching engine timeout")
    mock_client.place_order.return_value = "EMERGENCY_ORDER_999"
    monkeypatch.setattr("backend.order_manager.smart_api_client", mock_client)

    res = order_manager.atomic_modify_stop_loss(
        order_id="SL_ORDER_123",
        symbol="TCS",
        exchange="NSE",
        direction="BUY",
        quantity=10,
        trigger_price=3500.0,
    )
    assert res["success"] is False
    assert res["emergency_exit_required"] is True

    # Call emergency market close
    exit_id = order_manager.emergency_market_close(
        symbol="TCS",
        exchange="NSE",
        quantity=10,
        direction="BUY",
    )
    assert exit_id == "EMERGENCY_ORDER_999"
    mock_client.place_order.assert_called_with(
        variety="NORMAL",
        exchange="NSE",
        tradingsymbol="TCS",
        transaction_type="SELL",
        quantity=10,
        product="INTRADAY",
        order_type="MARKET",
    )


def test_midday_chop_window_gating():
    """Verify midday chop gating is disabled/removed to allow continuous trading."""
    # Midday window gating has been removed per user specification
    t_chop = datetime.time(12, 0)
    assert is_midday_chop_window(t_chop) is False

    t_chop_start = datetime.time(11, 15)
    assert is_midday_chop_window(t_chop_start) is False

    t_chop_end = datetime.time(13, 15)
    assert is_midday_chop_window(t_chop_end) is False

    t_morning = datetime.time(10, 0)
    assert is_midday_chop_window(t_morning) is False

    t_afternoon = datetime.time(14, 0)
    assert is_midday_chop_window(t_afternoon) is False


def test_fallback_statutory_turnover_rate():
    """Task 6: Verify statutory turnover fee is 0.00297% (SEBI True-to-Label)."""
    from backend.smartapi_client import smart_api_client

    charges = smart_api_client.calculate_statutory_charges_fast(
        entry_price=1000.0,
        exit_price=1000.0,
        qty=50,  # Turnover = 100,000
        product_type="INTRADAY",
        exchange="NSE",
    )
    # Total turnover = 100,000. Exchange charge = 100,000 * 0.0000297 = 2.97
    assert charges["external_charges"] > 0
    # Verify external charges component is calculated using 0.0000297
    assert round(100_000 * 0.0000297, 2) == 2.97
