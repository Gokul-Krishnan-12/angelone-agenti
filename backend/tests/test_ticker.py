import json
from unittest.mock import patch

from backend.ticker import TickerManager


def test_ticker_on_data_paise_conversion():
    """Verify SmartWebSocketV2 ticks in paise are accurately converted to rupees."""
    manager = TickerManager()

    # Emulate incoming WebSocket tick with price in paise
    # 150660 paise = ₹1,506.60 (TECHM)
    raw_tick = {
        "token": "13538",
        "tradingsymbol": "TECHM",
        "last_traded_price": 150660,
        "open_price_of_the_day": 150000,
        "high_price_of_the_day": 152000,
        "low_price_of_the_day": 149500,
        "closed_price": 150500,
        "volume_trade_for_the_day": 500000,
        "total_buy_quantity": 25000,
        "total_sell_quantity": 30000,
    }

    captured_events = []

    def mock_print(val, **kwargs):
        try:
            captured_events.append(json.loads(val))
        except Exception:
            pass

    with patch("builtins.print", side_effect=mock_print):
        manager._on_data(None, raw_tick)

    assert len(captured_events) == 1
    event = captured_events[0]
    assert event["event"] == "ticker:tick"
    data = event["data"]

    # Price must be in rupees (1506.60), NOT 150660.00
    assert data["lastPrice"] == 1506.60
    assert data["last_price"] == 1506.60
    assert data["ltp"] == 1506.60

    # OHLC must also be in rupees
    assert data["ohlc"]["open"] == 1500.00
    assert data["ohlc"]["high"] == 1520.00
    assert data["ohlc"]["low"] == 1495.00
    assert data["ohlc"]["close"] == 1505.00


def test_ticker_on_data_cgpower_paise_conversion():
    """Verify CGPOWER tick: 93040 paise -> ₹930.40."""
    manager = TickerManager()
    raw_tick = {
        "token": "1234",
        "tradingsymbol": "CGPOWER",
        "last_traded_price": 93040,
    }

    captured_events = []

    def mock_print(val, **kwargs):
        try:
            captured_events.append(json.loads(val))
        except Exception:
            pass

    with patch("builtins.print", side_effect=mock_print):
        manager._on_data(None, raw_tick)

    assert len(captured_events) == 1
    data = captured_events[0]["data"]
    assert data["lastPrice"] == 930.40
