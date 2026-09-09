"""Tests for JSON-RPC bridge methods handled in backend/main.py."""

from unittest.mock import patch

from backend.main import handle_request


def test_agent_status_rpc():
    res = handle_request({"jsonrpc": "2.0", "method": "agent_status", "id": 1})
    assert res["id"] == 1
    assert "result" in res
    assert "running" in res["result"]
    assert "mode" in res["result"]


def test_settings_rpc():
    # get_settings
    res = handle_request({"jsonrpc": "2.0", "method": "get_settings", "id": 2})
    assert res["id"] == 2
    assert "result" in res
    assert "risk" in res["result"]

    # save_settings
    res = handle_request(
        {
            "jsonrpc": "2.0",
            "method": "save_settings",
            "params": {"testKey": "testValue"},
            "id": 3,
        }
    )
    assert res["id"] == 3
    assert res["result"]["status"] == "saved"

    # settings_reset
    res = handle_request({"jsonrpc": "2.0", "method": "settings_reset", "id": 4})
    assert res["id"] == 4
    assert "result" in res
    assert "risk" in res["result"]


def test_watchlist_rpc():
    # watchlist_get
    res = handle_request({"jsonrpc": "2.0", "method": "watchlist_get", "id": 5})
    assert res["id"] == 5
    assert isinstance(res["result"], list)

    # watchlist_add
    res = handle_request(
        {
            "jsonrpc": "2.0",
            "method": "watchlist_add",
            "params": {"symbol": "TESTSTOCK"},
            "id": 6,
        }
    )
    assert res["id"] == 6
    assert "TESTSTOCK" in res["result"]

    # watchlist_remove
    res = handle_request(
        {
            "jsonrpc": "2.0",
            "method": "watchlist_remove",
            "params": {"symbol": "TESTSTOCK"},
            "id": 7,
        }
    )
    assert res["id"] == 7
    assert "TESTSTOCK" not in res["result"]


def test_ticker_rpc():
    res = handle_request(
        {
            "jsonrpc": "2.0",
            "method": "ticker_subscribe",
            "params": {"tokens": [12345, "SBIN"]},
            "id": 8,
        }
    )
    assert res["id"] == 8
    assert res["result"]["status"] == "subscribed"

    res = handle_request(
        {
            "jsonrpc": "2.0",
            "method": "ticker_unsubscribe",
            "params": {"tokens": [12345, "SBIN"]},
            "id": 9,
        }
    )
    assert res["id"] == 9
    assert res["result"]["status"] == "unsubscribed"

    res = handle_request({"jsonrpc": "2.0", "method": "ticker_status", "id": 10})
    assert res["id"] == 10
    assert "running" in res["result"]
    assert "tokens" in res["result"]


def test_log_and_signal_rpc():
    res = handle_request({"jsonrpc": "2.0", "method": "log_get_all", "id": 11})
    assert res["id"] == 11
    assert res["result"] == []

    res = handle_request({"jsonrpc": "2.0", "method": "log_clear", "id": 12})
    assert res["id"] == 12
    assert res["result"]["status"] == "cleared"

    res = handle_request(
        {
            "jsonrpc": "2.0",
            "method": "agent_dismiss_signal",
            "params": {"signalId": "sig-123"},
            "id": 13,
        }
    )
    assert res["id"] == 13
    assert res["result"]["dismissed"] == "sig-123"


def test_scan_now_rpc_aliases():
    with patch("backend.scanner.scanner.scan_watchlist", return_value=[]):
        with patch(
            "backend.screener.screener_engine.generate_daily_watchlist",
            return_value=["SBIN"],
        ):
            res1 = handle_request({"jsonrpc": "2.0", "method": "scan_now", "id": 14})
            assert res1["id"] == 14
            assert res1["result"] == []

            res2 = handle_request(
                {"jsonrpc": "2.0", "method": "agent_scan_now", "id": 15}
            )
            assert res2["id"] == 15
            assert res2["result"] == []


def test_get_trades_and_ohlc_rpc():
    with patch("backend.smartapi_client.smart_api_client.get_trades", return_value=[]):
        res = handle_request({"jsonrpc": "2.0", "method": "get_trades", "id": 16})
        assert res["id"] == 16
        assert res["result"] == []

    with patch(
        "backend.smartapi_client.smart_api_client.get_ohlc",
        return_value={"NSE:RELIANCE": {"last_price": 2500.0, "ohlc": {}}},
    ):
        res = handle_request(
            {
                "jsonrpc": "2.0",
                "method": "get_ohlc",
                "params": {"instruments": ["NSE:RELIANCE"]},
                "id": 17,
            }
        )
        assert res["id"] == 17
        assert "NSE:RELIANCE" in res["result"]


def test_execute_signal_safe_handling():
    # Calling execute_signal with empty signal dict should safely return executed: False without crash
    res = handle_request(
        {"jsonrpc": "2.0", "method": "execute_signal", "params": {}, "id": 18}
    )
    assert res["id"] == 18
    assert res["result"]["executed"] is False


def test_get_historical_validation():
    # Missing parameters should return error -32602
    res = handle_request(
        {"jsonrpc": "2.0", "method": "get_historical", "params": {}, "id": 19}
    )
    assert res["id"] == 19
    assert "error" in res
    assert res["error"]["code"] == -32602


def test_estimate_charges_rpc():
    mock_charges = {
        "summary": {
            "total_charges": 182.5,
            "breakup": [{"name": "Angel One Brokerage", "amount": 160.0}],
        }
    }
    with patch(
        "backend.smartapi_client.smart_api_client.estimate_charges",
        return_value=mock_charges,
    ):
        res = handle_request(
            {
                "jsonrpc": "2.0",
                "method": "estimate_charges",
                "params": {"orders": [{"tradingsymbol": "SBIN-EQ"}]},
                "id": 20,
            }
        )
        assert res["id"] == 20
        assert res["result"] == mock_charges
