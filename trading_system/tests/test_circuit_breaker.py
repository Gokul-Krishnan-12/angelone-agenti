"""
Tests for CircuitBreaker and session time gatekeeper.
"""

from trading_system.config.settings import Settings
from trading_system.risk.circuit_breaker import CircuitBreaker


def test_circuit_breaker_max_daily_loss_trip():
    settings = Settings(max_daily_loss=1000.0)
    cb = CircuitBreaker(settings)

    # Initial state
    assert not cb.is_circuit_locked
    can_trade, _ = cb.can_open_new_trade(current_open_positions=0)

    # Record small loss (-400)
    cb.update_pnl(realized_delta=-400.0)
    assert not cb.is_circuit_locked

    # Record large loss breaching 1000 limit (-700 -> total -1100)
    cb.update_pnl(realized_delta=-700.0)
    assert cb.is_circuit_locked
    assert "breached" in cb.lock_reason

    # Further trades should be blocked
    can_trade_now, reason = cb.can_open_new_trade(current_open_positions=0)
    assert not can_trade_now
    assert "Engine Locked" in reason

    # Should trigger mandatory emergency square-off if active positions exist
    must_sq, sq_reason = cb.should_square_off(active_positions_count=2)
    assert must_sq
    assert "Emergency Square-Off" in sq_reason


def test_circuit_breaker_max_daily_trades_limit():
    import datetime

    settings = Settings(max_daily_trades=3)
    cb = CircuitBreaker(settings)
    market_hours = datetime.time(10, 30)

    cb.record_trade_completion(pnl=100.0)
    cb.record_trade_completion(pnl=200.0)
    assert cb.completed_trades_count == 2

    can_trade, _ = cb.can_open_new_trade(
        current_open_positions=0, current_time=market_hours
    )
    assert can_trade

    cb.record_trade_completion(pnl=50.0)
    assert cb.completed_trades_count == 3

    # 4th trade should be rejected
    can_trade, reason = cb.can_open_new_trade(
        current_open_positions=0, current_time=market_hours
    )
    assert not can_trade
    assert "Daily trade limit" in reason
