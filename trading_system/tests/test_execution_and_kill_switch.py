"""
Tests for Two-Legged Native Order Execution, Trailing Ratchet Manager, and Emergency Kill Switch.
"""

from trading_system.config.settings import Settings
from trading_system.execution.order_router import OrderRouter
from trading_system.execution.ratchet_manager import RatchetManager
from trading_system.risk.circuit_breaker import CircuitBreaker
from trading_system.strategies.base import Signal


def test_two_legged_order_execution():
    settings = Settings(mode="paper")
    router = OrderRouter(settings=settings)

    sig = Signal(
        strategy_name="Breakout",
        family="breakout",
        tradingsymbol="PAYTM",
        direction="BUY",
        confidence=85,
        entry_price=1000.0,
        stop_loss=980.0,
        target_price=1050.0,
        risk_reward=2.5,
        timestamp=1700000000,
        indicators={"atr": 10.0},
    )

    trade = router.execute_two_legged_trade(signal=sig, token="12345", quantity=20)
    assert trade is not None
    assert trade.tradingsymbol == "PAYTM"
    assert trade.quantity == 20
    assert trade.direction == "BUY"
    assert trade.status == "OPEN"
    # Exchange SL order ID should be populated immediately
    assert trade.sl_order_id.startswith("SIM_SL_")
    assert trade.current_sl == 980.0


def test_ratchet_manager_trailing_gate_and_widened_atr():
    settings = Settings(
        mode="paper",
        breakeven_trigger_r=1.0,
        trailing_sl_atr_multiplier=2.2,
    )
    router = OrderRouter(settings=settings)

    sig = Signal(
        strategy_name="Breakout",
        family="breakout",
        tradingsymbol="PAYTM",
        direction="BUY",
        confidence=85,
        entry_price=1000.0,
        stop_loss=980.0,  # 1R = ₹20
        target_price=1080.0,
        risk_reward=4.0,
        timestamp=1700000000,
        indicators={"atr": 10.0},  # ATR = ₹10 -> 2.2x ATR = ₹22
    )

    trade = router.execute_two_legged_trade(signal=sig, token="12345", quantity=20)
    assert trade is not None
    ratchet = RatchetManager(order_router=router, settings=settings)

    # 1. Price advances to ₹1010 (+0.5R) -> Below 1.0R -> Trailing MUST NOT activate
    ratchet.update_with_tick(token="12345", symbol="PAYTM", ltp=1010.0)
    assert trade.current_sl == 980.0

    # 2. Price advances to ₹1030 (+1.5R) -> >= 1.0R -> Trailing activates!
    # HWM = 1030.0. Trailing distance = 2.2 * 10 = 22.0.
    # Candidate SL = max(1000, 1030 - 22) = 1008.0
    ratchet.update_with_tick(token="12345", symbol="PAYTM", ltp=1030.0)
    assert trade.current_sl == 1008.0
    assert trade.current_sl > trade.initial_sl

    # 3. Price advances to ₹1050 (+2.5R) -> HWM = 1050.0
    # Candidate SL = max(1000, 1050 - 22) = 1028.0
    ratchet.update_with_tick(token="12345", symbol="PAYTM", ltp=1050.0)
    assert trade.current_sl == 1028.0


def test_emergency_kill_switch_protocol():
    settings = Settings(mode="paper", max_daily_loss=600.0, max_open_positions=1)
    cb = CircuitBreaker(settings)
    router = OrderRouter(settings=settings)

    sig = Signal(
        strategy_name="Breakout",
        family="breakout",
        tradingsymbol="PAYTM",
        direction="BUY",
        confidence=85,
        entry_price=1000.0,
        stop_loss=980.0,
        target_price=1050.0,
        risk_reward=2.5,
        timestamp=1700000000,
        indicators={"atr": 10.0},
    )
    trade = router.execute_two_legged_trade(signal=sig, token="12345", quantity=10)
    assert trade is not None
    assert len(router.active_trades) == 1

    # Daily loss threshold breached (-₹650)
    cb.update_pnl(realized_delta=-650.0)
    assert cb.is_circuit_locked

    # Trigger emergency kill switch
    liquidated_count = cb.execute_emergency_kill_switch(router)
    assert liquidated_count == 1
    assert len(router.active_trades) == 0
    assert cb.is_circuit_locked

    # New trades blocked
    can_trade, reason = cb.can_open_new_trade(current_open_positions=0)
    assert not can_trade
    assert "Engine Locked" in reason
