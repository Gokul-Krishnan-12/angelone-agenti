import time
from unittest.mock import MagicMock

from backend.config import config_manager
from backend.risk_manager import RiskManager
from backend.smartapi_client import SmartApiClient
from backend.trading_engine import TradingEngine


def test_1r_risk_based_position_sizing(monkeypatch):
    """Test that position size scales inversely with stop-loss distance (1R risk budgeting)."""
    rm = RiskManager()
    monkeypatch.setattr(
        config_manager,
        "get_risk_config",
        lambda: {"maxCapitalPerTrade": 8000.0, "riskPerTrade": 500.0, "leverage": 5.0},
    )

    # Tight stop-loss: 1000 entry, 990 SL (distance = 10)
    # 500 risk budget / 10 = 50 shares (cost: 50,000 > 40,000 cap -> capped at 40 shares)
    qty_tight = rm.calculate_position_size(price=1000.0, stop_loss=990.0)
    assert qty_tight == 40  # 40000 / 1000 = 40

    # Normal stop-loss: 500 entry, 480 SL (distance = 20)
    # 500 risk budget / 20 = 25 shares (cost: 12,500 < 40,000 cap -> 25 shares)
    qty_normal = rm.calculate_position_size(price=500.0, stop_loss=480.0)
    assert qty_normal == 25
    assert qty_normal * 20.0 == 500.0  # Exact 1R risk of 500 INR!

    # Wide stop-loss: 500 entry, 450 SL (distance = 50)
    # 500 risk budget / 50 = 10 shares (cost: 5,000 < 40,000 cap -> 10 shares)
    qty_wide = rm.calculate_position_size(price=500.0, stop_loss=450.0)
    assert qty_wide == 10
    assert qty_wide * 50.0 == 500.0  # Exact 1R risk of 500 INR!

    # Zero SL or invalid price fallback
    assert rm.calculate_position_size(price=500.0, stop_loss=500.0) == 80  # 40000 / 500
    assert rm.calculate_position_size(price=0.0, stop_loss=0.0) == 0


def test_strategy_roster_pruning_defaults():
    """Verify that toxic lagging indicators are disabled by default while alpha setups are enabled."""
    strats = config_manager.get_strategy_config()

    # Pruned lagging indicators
    assert strats.get("psar_trend", {}).get("enabled") is False
    assert strats.get("ema_crossover", {}).get("enabled") is False
    assert strats.get("macd_cross", {}).get("enabled") is False
    assert strats.get("supertrend", {}).get("enabled") is False
    assert strats.get("awesome_oscillator", {}).get("enabled") is False
    assert strats.get("williams_r", {}).get("enabled") is False
    assert strats.get("adx_momentum", {}).get("enabled") is False

    # High-expectancy breakout & structural setups
    assert strats.get("donchian_breakout", {}).get("enabled") is True
    assert strats.get("keltner_breakout", {}).get("enabled") is True
    assert strats.get("bollinger_breakout", {}).get("enabled") is True
    assert strats.get("order_block_fvg", {}).get("enabled") is True
    assert strats.get("institutional_absorption", {}).get("enabled") is True
    assert strats.get("volume_delta_divergence", {}).get("enabled") is True
    assert strats.get("cpr_breakout_reversal", {}).get("enabled") is True


def test_active_trades_disk_persistence(tmp_path, monkeypatch):
    """Verify active trades save and reload from disk."""
    monkeypatch.setattr(config_manager, "config_dir", tmp_path)

    test_trades = {
        "RELIANCE": {
            "sl": 2900.0,
            "sl_order_id": "SL12345",
            "target": 3100.0,
            "direction": "BUY",
            "entry_price": 2950.0,
            "entry_time": "2026-09-14T10:00:00",
        }
    }

    config_manager.save_active_trades(test_trades)
    loaded = config_manager.get_active_trades()
    assert loaded == test_trades

    # Test TradingEngine initialization loads persisted trades
    engine = TradingEngine()
    assert "RELIANCE" in engine.active_trades
    assert engine.active_trades["RELIANCE"]["sl_order_id"] == "SL12345"


def test_pending_orders_promotion_on_fill(monkeypatch):
    """Test that entry orders are queued in pending_orders and promoted to active_trades on fill."""
    engine = TradingEngine()
    engine.active_trades = {}
    engine.pending_orders = {}

    mock_client = MagicMock()
    mock_client.place_order.return_value = "ORDER_999"
    monkeypatch.setattr("backend.trading_engine.smart_api_client", mock_client)
    monkeypatch.setattr(
        "backend.trading_engine.risk_manager.can_trade", lambda: (True, "OK")
    )
    monkeypatch.setattr(config_manager, "save_active_trades", lambda t: None)

    signal = {
        "tradingsymbol": "TCS",
        "exchange": "NSE",
        "direction": "BUY",
        "entryPrice": 3800.0,
        "stopLoss": 3750.0,
        "target": 3950.0,
        "strategy": "donchian_breakout",
        "indicators": {"atr": 25.0},
    }

    # Execute signal
    result = engine.execute_signal(signal)
    assert result is True
    # Verify order is in pending_orders, NOT yet in active_trades
    assert "ORDER_999" in engine.pending_orders
    assert "TCS" not in engine.active_trades

    # Simulate get_orders returning COMPLETE for ORDER_999
    mock_client.get_orders.return_value = [
        {
            "orderId": "ORDER_999",
            "status": "COMPLETE",
            "averagePrice": 3805.0,
            "filledQuantity": 10,
        }
    ]
    mock_client.place_order.return_value = "SL_ORDER_001"

    # Run pending order monitor
    engine.monitor_pending_orders()

    # Should be promoted to active_trades with resting exchange SL placed
    assert "ORDER_999" not in engine.pending_orders
    assert "TCS" in engine.active_trades
    trade = engine.active_trades["TCS"]
    assert trade["entry_price"] == 3805.0
    assert trade["sl_order_id"] == "SL_ORDER_001"
    assert trade["sl"] == 3750.0

    # Verify place_order was called with STOPLOSS variety
    mock_client.place_order.assert_called_with(
        variety="STOPLOSS",
        exchange="NSE",
        tradingsymbol="TCS",
        transaction_type="SELL",
        quantity=10,
        product="INTRADAY",
        order_type="STOPLOSS_LIMIT",
        price=3712.5,  # 3750 * 0.99
        trigger_price=3750.0,
    )


def test_pending_orders_timeout_cancellation(monkeypatch):
    """Test that unfilled orders older than 60 seconds are cancelled and purged."""
    engine = TradingEngine()
    engine.pending_orders = {
        "TIMEOUT_ORDER": {
            "order_id": "TIMEOUT_ORDER",
            "tradingsymbol": "INFY",
            "exchange": "NSE",
            "direction": "BUY",
            "quantity": 20,
            "entry_price": 1800.0,
            "stop_loss": 1780.0,
            "target": 1850.0,
            "original_strategy": "keltner_breakout",
            "atr": 15.0,
            "submitted_at": time.time() - 75,  # 75s ago
        }
    }

    mock_client = MagicMock()
    mock_client.get_orders.return_value = [
        {"orderId": "TIMEOUT_ORDER", "status": "PENDING"}
    ]
    monkeypatch.setattr("backend.trading_engine.smart_api_client", mock_client)

    engine.monitor_pending_orders()

    # Must call cancel_order and purge from pending_orders
    mock_client.cancel_order.assert_called_with(
        variety="NORMAL", order_id="TIMEOUT_ORDER"
    )
    assert "TIMEOUT_ORDER" not in engine.pending_orders


def test_exchange_sl_modified_on_trailing_sl(monkeypatch):
    """Test that modifying trailing SL also updates the resting exchange SL order."""
    engine = TradingEngine()
    engine.active_trades = {
        "RELIANCE": {
            "sl": 2900.0,
            "sl_order_id": "SL_EXISTING",
            "target": 3100.0,
            "direction": "BUY",
            "entry_price": 2950.0,
            "atr": 20.0,
            "high_water_mark": 3000.0,
            "low_water_mark": 2950.0,
        }
    }

    mock_client = MagicMock()
    mock_positions = {
        "net": [
            {
                "tradingsymbol": "RELIANCE",
                "quantity": 10,
                "exchange": "NSE",
                "lastPrice": 3050.0,
                "averagePrice": 2950.0,
            }
        ]
    }
    mock_client.get_positions.return_value = mock_positions
    monkeypatch.setattr("backend.trading_engine.smart_api_client", mock_client)
    monkeypatch.setattr(
        "backend.trading_engine.risk_manager.update_trailing_sl",
        lambda t, ltp, atr, mult: 2980.0,  # Ratchet SL up to 2980
    )
    monkeypatch.setattr(config_manager, "save_active_trades", lambda t: None)

    engine.monitor_positions()

    # Check that modify_order was called on the exchange SL order
    assert engine.active_trades["RELIANCE"]["sl"] == 2980.0
    mock_client.modify_order.assert_called_with(
        variety="STOPLOSS",
        order_id="SL_EXISTING",
        tradingsymbol="RELIANCE",
        order_type="STOPLOSS_LIMIT",
        price=2950.2,  # 2980 * 0.99
        trigger_price=2980.0,
    )


def test_smartapi_client_auth_auto_retry(monkeypatch):
    """Test that _execute_with_auth_retry attempts re-authentication on invalid token errors."""
    client = SmartApiClient()
    client.smart_api = MagicMock()

    call_count = {"count": 0}

    def mock_api_call():
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise RuntimeError("Invalid Token (AG8001)")
        return {"status": True, "data": [{"netqty": 5}]}

    # Mock reauthenticate to succeed
    monkeypatch.setattr(client, "reauthenticate", lambda: True)

    res = client._execute_with_auth_retry(mock_api_call)
    assert res == {"status": True, "data": [{"netqty": 5}]}
    assert call_count["count"] == 2  # Called twice (retried after re-auth)
