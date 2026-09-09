"""Unit tests for Telegram notification service and RPC methods."""

from unittest.mock import MagicMock, patch

from backend.main import handle_request
from backend.notifier import TelegramNotifier


def test_telegram_send_without_credentials():
    notifier = TelegramNotifier()
    ok, msg = notifier.send_telegram_message_sync(
        "Test message", bot_token="", chat_id=""
    )
    assert ok is False
    assert "Bot Token and Chat ID are required" in msg


def test_telegram_send_success():
    notifier = TelegramNotifier()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, msg = notifier.send_telegram_message_sync(
            "Test message", bot_token="123456:ABC-DEF", chat_id="987654321"
        )
        assert ok is True
        assert "successfully" in msg


def test_notify_trade_exit_target():
    notifier = TelegramNotifier()
    notifier._get_config = MagicMock(
        return_value={
            "enabled": True,
            "notifyOnTradeExit": True,
            "botToken": "tok",
            "chatId": "123",
        }
    )

    with patch.object(notifier, "send_telegram_message_async") as mock_send:
        notifier.notify_trade_exit(
            {
                "tradingsymbol": "RELIANCE",
                "direction": "BUY",
                "entryPrice": 2850.0,
                "exitPrice": 2935.5,
                "quantity": 10,
                "pnl": 855.0,
                "pnlPercent": 3.0,
                "exitReason": "TARGET",
                "mode": "Live Trading",
            }
        )
        assert mock_send.called
        sent_msg = mock_send.call_args[0][0]
        assert "TARGET HIT" in sent_msg
        assert "RELIANCE" in sent_msg
        assert "+₹855.00" in sent_msg


def test_notify_trade_exit_stoploss():
    notifier = TelegramNotifier()
    notifier._get_config = MagicMock(
        return_value={
            "enabled": True,
            "notifyOnTradeExit": True,
            "botToken": "tok",
            "chatId": "123",
        }
    )

    with patch.object(notifier, "send_telegram_message_async") as mock_send:
        notifier.notify_trade_exit(
            {
                "tradingsymbol": "INFY",
                "direction": "SELL",
                "entryPrice": 1800.0,
                "exitPrice": 1827.0,
                "quantity": 15,
                "pnl": -405.0,
                "pnlPercent": -1.5,
                "exitReason": "STOPLOSS",
                "mode": "Paper Trading",
            }
        )
        assert mock_send.called
        sent_msg = mock_send.call_args[0][0]
        assert "STOP LOSS HIT" in sent_msg
        assert "INFY" in sent_msg
        assert "-₹405.00" in sent_msg


def test_notify_session_summary():
    notifier = TelegramNotifier()
    notifier._get_config = MagicMock(
        return_value={
            "enabled": True,
            "notifyOnSessionEnd": True,
            "botToken": "tok",
            "chatId": "123",
        }
    )

    with patch.object(notifier, "send_telegram_message_async") as mock_send:
        notifier.notify_session_summary(
            {
                "totalTrades": 4,
                "executedOrders": 8,
                "winningTrades": 3,
                "losingTrades": 1,
                "winRate": 75.0,
                "grossPnl": 1845.50,
                "brokerage": 160.00,
                "netPnl": 1685.50,
                "mode": "Live Trading",
            }
        )
        assert mock_send.called
        sent_msg = mock_send.call_args[0][0]
        assert "DAILY SESSION PERFORMANCE SUMMARY" in sent_msg
        assert "Total Trades:</b> 4 (8 Executed Orders)" in sent_msg
        assert "Gross Realised P&L:</b> <code>+₹1,845.50</code>" in sent_msg
        assert "Brokerage Collected:</b> <code>-₹160.00</code>" in sent_msg
        assert "Net Realised P&L:</b> <code>+₹1,685.50</code>" in sent_msg


def test_notify_session_summary_with_live_api_charges():
    notifier = TelegramNotifier()
    notifier._get_config = MagicMock(
        return_value={
            "enabled": True,
            "notifyOnSessionEnd": True,
            "botToken": "tok",
            "chatId": "123",
        }
    )

    with patch.object(notifier, "send_telegram_message_async") as mock_send:
        notifier.notify_session_summary(
            {
                "totalTrades": 4,
                "executedOrders": 8,
                "winningTrades": 3,
                "losingTrades": 1,
                "winRate": 75.0,
                "grossPnl": 2000.00,
                "brokerage": 160.00,
                "totalCharges": 182.50,
                "taxesAndCharges": 22.50,
                "netPnl": 1817.50,
                "mode": "Live Trading",
            }
        )
        assert mock_send.called
        sent_msg = mock_send.call_args[0][0]
        assert "DAILY SESSION PERFORMANCE SUMMARY" in sent_msg
        assert "Brokerage & Taxes:</b> <code>-₹182.50</code>" in sent_msg
        assert "Brokerage: ₹160.00 + Taxes/STT: ₹22.50" in sent_msg
        assert "Net Realised P&L:</b> <code>+₹1,817.50</code>" in sent_msg


def test_notify_paper_session_summary():
    notifier = TelegramNotifier()
    notifier._get_config = MagicMock(
        return_value={
            "enabled": True,
            "notifyOnSessionEnd": True,
            "botToken": "tok",
            "chatId": "123",
        }
    )

    with patch.object(notifier, "send_telegram_message_async") as mock_send:
        notifier.notify_session_summary(
            {
                "totalTrades": 2,
                "executedOrders": 4,
                "winningTrades": 2,
                "losingTrades": 0,
                "winRate": 100.0,
                "grossPnl": 2400.00,
                "brokerage": 80.00,
                "netPnl": 2320.00,
                "endingBalance": 102320.00,
                "mode": "Paper Trading",
            }
        )
        assert mock_send.called
        sent_msg = mock_send.call_args[0][0]
        assert "DAILY PAPER SESSION PERFORMANCE REPORT" in sent_msg
        assert "Paper Trading Sandbox" in sent_msg
        assert "Total Paper Trades:</b> 2 (4 Simulated Orders)" in sent_msg
        assert "Est. Brokerage Saved:</b> <code>₹80.00</code>" in sent_msg
        assert "Net Virtual P&L:</b> <code>+₹2,320.00</code>" in sent_msg
        assert "Ending Virtual Balance:</b> ₹102,320.00" in sent_msg
        assert "Zero Financial Risk" in sent_msg


def test_telegram_rpc_handlers():
    # Test telegram_test RPC
    with patch(
        "backend.notifier.notifier.send_telegram_message_sync",
        return_value=(True, "Success"),
    ):
        res = handle_request(
            {
                "jsonrpc": "2.0",
                "method": "telegram_test",
                "params": {"botToken": "dummy", "chatId": "123"},
                "id": 99,
            }
        )
        assert res["id"] == 99
        assert res["result"]["success"] is True

    # Test telegram_send_exit RPC
    with patch("backend.notifier.notifier.notify_trade_exit") as mock_exit:
        res = handle_request(
            {
                "jsonrpc": "2.0",
                "method": "telegram_send_exit",
                "params": {"trade": {"tradingsymbol": "SBIN", "pnl": 100}},
                "id": 100,
            }
        )
        assert res["id"] == 100
        assert res["result"]["status"] == "queued"
        assert mock_exit.called

    # Test telegram_send_summary RPC
    with patch("backend.notifier.notifier.notify_session_summary") as mock_summary:
        res = handle_request(
            {
                "jsonrpc": "2.0",
                "method": "telegram_send_summary",
                "params": {"summary": {"totalTrades": 2}},
                "id": 101,
            }
        )
        assert res["id"] == 101
        assert res["result"]["status"] == "queued"
        assert mock_summary.called


def test_notify_signal_approval():
    notifier = TelegramNotifier()
    # By default without notifyOnSignal, approval notification should not be sent
    notifier._get_config = MagicMock(return_value={"enabled": True})
    with patch.object(notifier, "send_telegram_message_async") as mock_send:
        notifier.notify_signal_approval({"tradingsymbol": "TATASTEEL"})
        assert not mock_send.called

    # If explicitly enabled, it formats and sends
    notifier._get_config = MagicMock(
        return_value={"enabled": True, "notifyOnSignal": True}
    )
    with patch.object(notifier, "send_telegram_message_async") as mock_send:
        notifier.notify_signal_approval(
            {
                "tradingsymbol": "TATASTEEL",
                "direction": "BUY",
                "entryPrice": 152.40,
                "stopLoss": 150.10,
                "target": 156.60,
                "confidence": 88,
                "confluenceScore": 3,
                "familiesVoting": ["trend", "momentum", "breakout"],
                "allStrategies": ["keltner_breakout", "macd_cross", "psar_trend"],
                "riskReward": 1.83,
            }
        )
        assert mock_send.called
        sent_msg = mock_send.call_args[0][0]
        assert "NEW TRADING SIGNAL — APPROVAL REQUIRED" in sent_msg
        assert "TATASTEEL" in sent_msg
        assert "152.40" in sent_msg
        assert "150.10" in sent_msg
        assert "156.60" in sent_msg
        assert "88%" in sent_msg
        assert "trend, momentum, breakout" in sent_msg
