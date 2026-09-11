"""Unit tests for Telegram 2-way bot remote control controller and commands."""

from unittest.mock import MagicMock, patch

from backend.main import handle_request
from backend.telegram_bot import TelegramBotController


def test_unauthorized_message_rejected():
    bot = TelegramBotController()
    bot._get_config = MagicMock(
        return_value={
            "enabled": True,
            "botToken": "fake_token",
            "chatId": "999888777",
        }
    )

    with patch.object(bot, "_send_reply") as mock_reply:
        # Message from an unknown/attacker chat ID
        message = {
            "chat": {"id": "111222333"},
            "text": "/stop",
        }
        bot.process_message(message, allowed_chat_id="999888777")
        assert mock_reply.called
        sent_text = mock_reply.call_args[0][1]
        assert "Access Denied" in sent_text


def test_command_status():
    bot = TelegramBotController()

    with patch(
        "backend.telegram_bot.trading_engine.status",
        return_value={"running": True, "mode": "auto"},
    ):
        with patch(
            "backend.telegram_bot.smart_api_client.get_positions",
            return_value={
                "net": [
                    {
                        "tradingsymbol": "SBIN-EQ",
                        "quantity": 10,
                        "averagePrice": 750.0,
                        "lastPrice": 760.0,
                        "pnl": 100.0,
                    }
                ]
            },
        ):
            with patch(
                "backend.telegram_bot.smart_api_client.get_margins",
                return_value={"equity": {"available": {"live_balance": 50000.0}}},
            ):
                resp = bot.dispatch_command("/status", [])
                assert "AGENT STATUS" in resp
                assert "RUNNING" in resp
                assert "AUTO" in resp
                assert "Active Positions:</b> 1" in resp
                assert "₹50,000.00" in resp
                assert "+₹100.00" in resp


def test_command_start_default_and_auto():
    bot = TelegramBotController()

    with patch("backend.telegram_bot.trading_engine.start") as mock_start:
        resp_confirm = bot.dispatch_command("/start", [])
        assert "TRADING ENGINE STARTED" in resp_confirm
        assert "CONFIRM" in resp_confirm
        mock_start.assert_called_with(mode="confirm")

        resp_auto = bot.dispatch_command("/start", ["auto"])
        assert "TRADING ENGINE STARTED" in resp_auto
        assert "AUTO" in resp_auto
        mock_start.assert_called_with(mode="auto")


def test_command_stop():
    bot = TelegramBotController()

    with patch("backend.telegram_bot.trading_engine.stop") as mock_stop:
        resp = bot.dispatch_command("/stop", [])
        assert "TRADING ENGINE STOPPED" in resp
        assert mock_stop.called


def test_command_squareoff():
    bot = TelegramBotController()

    with (
        patch("backend.telegram_bot.trading_engine.square_off_all") as mock_sq,
        patch("backend.telegram_bot.trading_engine.stop") as mock_stop,
        patch(
            "backend.telegram_bot.smart_api_client.get_positions",
            return_value={"net": [{"tradingsymbol": "TCS-EQ", "quantity": 5}]},
        ),
    ):
        resp = bot.dispatch_command("/squareoff", [])
        assert "EMERGENCY SQUARE-OFF EXECUTED" in resp
        assert "1 position(s) squared off" in resp
        assert mock_sq.called
        assert mock_stop.called


def test_command_positions():
    bot = TelegramBotController()

    # When no positions are open
    with patch(
        "backend.telegram_bot.smart_api_client.get_positions", return_value={"net": []}
    ):
        resp_empty = bot.dispatch_command("/positions", [])
        assert "No active open positions" in resp_empty

    # When positions are open
    with patch(
        "backend.telegram_bot.smart_api_client.get_positions",
        return_value={
            "net": [
                {
                    "tradingsymbol": "RELIANCE-EQ",
                    "quantity": 10,
                    "averagePrice": 2900.0,
                    "lastPrice": 2950.0,
                    "pnl": 500.0,
                }
            ]
        },
    ):
        resp_pos = bot.dispatch_command("/positions", [])
        assert "RELIANCE" in resp_pos
        assert "BUY × 10" in resp_pos
        assert "Entry: ₹2,900.00" in resp_pos
        assert "+₹500.00" in resp_pos


def test_command_help():
    bot = TelegramBotController()
    resp = bot.dispatch_command("/help", [])
    assert "/status" in resp
    assert "/start" in resp
    assert "/stop" in resp
    assert "/squareoff" in resp
    assert "/positions" in resp


def test_command_unknown():
    bot = TelegramBotController()
    resp = bot.dispatch_command("/random_cmd", [])
    assert "Unknown command" in resp
    assert "/help" in resp


def test_lifecycle_and_disabled():
    bot = TelegramBotController()
    # When disabled
    bot._get_config = MagicMock(return_value={"enabled": False})
    assert bot.start() is False
    assert bot.is_running() is False

    # When missing credentials
    bot._get_config = MagicMock(
        return_value={"enabled": True, "botToken": "", "chatId": ""}
    )
    assert bot.start() is False
    assert bot.is_running() is False


def test_telegram_bot_rpc_handlers():
    res = handle_request({"method": "telegram_bot_status", "id": 1})
    assert res["result"]["running"] is not None

    with patch("backend.main.telegram_bot.start", return_value=True):
        res_start = handle_request({"method": "telegram_bot_start", "id": 2})
        assert "started" in res_start["result"]

    with patch("backend.main.telegram_bot.stop"):
        res_stop = handle_request({"method": "telegram_bot_stop", "id": 3})
        assert res_stop["result"]["stopped"] is True
