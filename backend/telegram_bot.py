import datetime
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .config import config_manager
from .notifier import notifier
from .smartapi_client import smart_api_client
from .trading_engine import trading_engine

logger = logging.getLogger(__name__)


class TelegramBotController:
    """Listens for inbound Telegram bot commands and provides 2-way remote control.

    Supported commands:
    - /status: Live trading engine status, open positions, daily P&L, available margin
    - /start [auto|confirm]: Start trading engine in specified mode (default: confirm)
    - /stop: Stop trading engine and pause automated scanning
    - /squareoff: Emergency panic button; squares off all open positions and halts engine
    - /positions: List detailed open positions with live P&L
    - /help: Show command menu
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_update_id = 0
        self._lock = threading.Lock()

    def _get_config(self) -> Dict[str, Any]:
        notifications = config_manager.get_notifications_config()
        return notifications.get("telegram", {})

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """Start the long-polling listener in a background daemon thread."""
        with self._lock:
            if self.is_running():
                return True

            cfg = self._get_config()
            if not cfg.get("enabled", False):
                logger.info(
                    "Telegram bot not starting: notifications.telegram.enabled is false"
                )
                return False

            token = cfg.get("botToken", "").strip()
            chat_id = cfg.get("chatId", "").strip()
            if not token or not chat_id:
                logger.warning(
                    "Telegram bot not starting: botToken or chatId missing in config"
                )
                return False

            self._running = True
            self._thread = threading.Thread(
                target=self._poll_loop,
                daemon=True,
                name="TelegramBotController",
            )
            self._thread.start()
            logger.info("Telegram 2-way bot controller started")
            return True

    def stop(self):
        """Stop the background polling thread."""
        with self._lock:
            self._running = False

        if self._thread and self._thread.is_alive():
            # Thread will terminate on the next poll cycle or timeout
            self._thread.join(timeout=1.0)
            self._thread = None
        logger.info("Telegram 2-way bot controller stopped")

    def restart(self) -> bool:
        """Restart the controller with updated configuration."""
        self.stop()
        return self.start()

    def _fetch_updates(
        self, bot_token: str, offset: int, timeout: int = 15
    ) -> List[Dict[str, Any]]:
        """Fetch pending updates from the Telegram Bot API using long polling."""
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout={timeout}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AngelOneTradingAgent/1.0",
            },
        )

        # Allow 10 seconds beyond the server long-poll timeout
        http_timeout = timeout + 10
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            if resp.status == 200:
                payload = json.loads(resp.read().decode("utf-8"))
                if payload.get("ok", False):
                    return payload.get("result", [])
        return []

    def _poll_loop(self):
        """Main long-polling loop."""
        logger.info("Telegram bot listener polling loop started")

        while self._running:
            cfg = self._get_config()
            token = cfg.get("botToken", "").strip()
            allowed_chat_id = str(cfg.get("chatId", "")).strip()

            if not token or not allowed_chat_id or not cfg.get("enabled", False):
                time.sleep(3)
                continue

            try:
                updates = self._fetch_updates(token, self._last_update_id, timeout=15)
                for update in updates:
                    update_id = update.get("update_id", 0)
                    if update_id >= self._last_update_id:
                        self._last_update_id = update_id + 1

                    message = update.get("message") or update.get("channel_post")
                    if not message:
                        continue

                    self.process_message(message, allowed_chat_id)

            except (TimeoutError, urllib.error.URLError) as e:
                # Normal socket timeout during long polling or temporary network issue
                if isinstance(e, urllib.error.HTTPError) and e.code in (401, 404):
                    logger.error("Telegram bot authentication failed: HTTP %s", e.code)
                    time.sleep(10)
                else:
                    time.sleep(1)
            except Exception as e:
                logger.error("Error in Telegram bot polling loop: %s", e)
                time.sleep(2)

    def process_message(self, message: Dict[str, Any], allowed_chat_id: str):
        """Parse incoming message, authenticate sender, and dispatch command."""
        from_chat = message.get("chat", {})
        chat_id = str(from_chat.get("id", "")).strip()
        text = str(message.get("text", "")).strip()

        if not text:
            return

        # Security check: strict verification against configured chatId
        if chat_id != allowed_chat_id:
            logger.warning(
                "Rejected Telegram command from unauthorized chat_id: %s (allowed: %s)",
                chat_id,
                allowed_chat_id,
            )
            self._send_reply(
                chat_id,
                "⛔ <b>Access Denied</b>\nThis bot is private and restricted to the authorized account.",
            )
            return

        # Parse command and optional parameters
        parts = text.split()
        raw_cmd = parts[0].lower()
        cmd = raw_cmd.split("@")[
            0
        ]  # Strip bot mention if in group, e.g. /status@my_bot
        args = parts[1:]

        logger.info("Processing Telegram command: %s (args: %s)", cmd, args)

        response = self.dispatch_command(cmd, args)
        if response:
            self._send_reply(chat_id, response)

    def dispatch_command(self, cmd: str, args: List[str]) -> str:
        """Dispatch a validated command to its corresponding handler."""
        if cmd in ("/status", "status"):
            return self._cmd_status()
        elif cmd in ("/start", "start"):
            return self._cmd_start(args)
        elif cmd in ("/stop", "stop"):
            return self._cmd_stop()
        elif cmd in ("/squareoff", "squareoff", "/panic", "panic"):
            return self._cmd_squareoff()
        elif cmd in ("/positions", "positions"):
            return self._cmd_positions()
        elif cmd in ("/help", "help"):
            return self._cmd_help()
        else:
            return (
                f"❓ Unknown command: <code>{cmd}</code>\n\n"
                "Use /help to see all available remote commands."
            )

    def _cmd_status(self) -> str:
        """Handle /status command."""
        engine_status = trading_engine.status()
        is_running = engine_status.get("running", False)
        mode = str(engine_status.get("mode", "confirm")).upper()

        engine_icon = "🟢 RUNNING" if is_running else "🔴 STOPPED"
        now_str = datetime.datetime.now().strftime("%H:%M:%S")

        # Gather live broker metrics
        positions_res = smart_api_client.get_positions(force=True)
        positions = (
            positions_res.get("net", []) if isinstance(positions_res, dict) else []
        )
        open_pos = [p for p in positions if p.get("quantity", 0) != 0]

        total_pnl = sum(p.get("pnl", p.get("m2m", 0)) for p in positions)
        realised_pnl = sum(p.get("realised", 0) for p in positions)
        unrealised_pnl = sum(p.get("unrealised", 0) for p in positions)

        total_trades = len(positions)
        winning = sum(1 for p in positions if p.get("pnl", p.get("m2m", 0)) > 0)
        losing = sum(1 for p in positions if p.get("pnl", p.get("m2m", 0)) < 0)
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0.0

        pnl_prefix = "+" if total_pnl >= 0 else "-"
        pnl_icon = "📈" if total_pnl >= 0 else "📉"

        # Margin info
        try:
            margins = smart_api_client.get_margins(force=True)
            equity_margin = margins.get("equity", {})
            available_margin = float(
                equity_margin.get("available", {}).get("live_balance", 0)
                or equity_margin.get("net", 0)
            )
            margin_str = f"₹{available_margin:,.2f}"
        except Exception:
            margin_str = "Unavailable"

        return (
            f"🤖 <b>ANGEL ONE AGENT STATUS</b>\n\n"
            f"⚡ <b>Engine:</b> {engine_icon} (Mode: <code>{mode}</code>)\n"
            f"📊 <b>Active Positions:</b> {len(open_pos)}\n"
            f"💼 <b>Available Margin:</b> <code>{margin_str}</code>\n\n"
            f"{pnl_icon} <b>Today's Total P&L:</b> <code>{pnl_prefix}₹{abs(total_pnl):,.2f}</code>\n"
            f"  • Realised: <code>₹{realised_pnl:,.2f}</code>\n"
            f"  • Unrealised: <code>₹{unrealised_pnl:,.2f}</code>\n"
            f"🎯 <b>Session Record:</b> {winning}W / {losing}L ({win_rate:.1f}% Win Rate)\n\n"
            f"⏱ <i>{now_str} IST</i>"
        )

    def _cmd_start(self, args: List[str]) -> str:
        """Handle /start [auto|confirm] command."""
        target_mode = "confirm"
        if args and args[0].lower() in ("auto", "confirm"):
            target_mode = args[0].lower()
        else:
            # Check default from config or engine
            target_mode = trading_engine.mode or "confirm"

        trading_engine.start(mode=target_mode)
        mode_upper = target_mode.upper()

        if target_mode == "auto":
            safety_note = "⚠️ <b>Auto Mode Active:</b> Trades will be placed automatically without desktop confirmation."
        else:
            safety_note = (
                "🛡 <b>Confirm Mode Active:</b> Signals will await confirmation."
            )

        return (
            f"🚀 <b>TRADING ENGINE STARTED</b>\n\n"
            f"🏷 <b>Execution Mode:</b> <code>{mode_upper}</code>\n"
            f"🔍 Dynamic watchlist scanner & position monitoring are now active.\n\n"
            f"{safety_note}"
        )

    def _cmd_stop(self) -> str:
        """Handle /stop command."""
        trading_engine.stop()
        return (
            "🛑 <b>TRADING ENGINE STOPPED</b>\n\n"
            "Market scanning and auto-executions have been paused.\n"
            "Existing open positions remain live and will be closed upon hitting targets or RMS square-off.\n\n"
            "Use /squareoff if you wish to exit all open positions immediately."
        )

    def _cmd_squareoff(self) -> str:
        """Handle /squareoff emergency command."""
        positions_res = smart_api_client.get_positions(force=True)
        positions = (
            positions_res.get("net", []) if isinstance(positions_res, dict) else []
        )
        open_pos = [p for p in positions if p.get("quantity", 0) != 0]
        pos_count = len(open_pos)

        # Trigger engine square off and pause
        trading_engine.square_off_all()
        trading_engine.stop()

        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        return (
            f"🚨 <b>EMERGENCY SQUARE-OFF EXECUTED</b>\n\n"
            f"⚡ <b>Closed Positions:</b> {pos_count} position(s) squared off\n"
            f"🛑 <b>Trading Engine:</b> Stopped\n"
            f"⏱ <b>Executed At:</b> {now_str} IST\n\n"
            f"All open intraday positions have been sent exit limit/market orders."
        )

    def _cmd_positions(self) -> str:
        """Handle /positions command."""
        positions_res = smart_api_client.get_positions(force=True)
        positions = (
            positions_res.get("net", []) if isinstance(positions_res, dict) else []
        )
        open_pos = [p for p in positions if p.get("quantity", 0) != 0]

        if not open_pos:
            return (
                "📊 <b>CURRENT OPEN POSITIONS</b>\n\n"
                "ℹ️ No active open positions right now.\n"
                "Use /status to see overall account summary."
            )

        lines = ["📊 <b>CURRENT OPEN POSITIONS</b>\n"]
        for p in open_pos:
            sym = str(p.get("tradingsymbol", "")).replace("-EQ", "")
            qty = p.get("quantity", 0)
            direction = "BUY" if qty > 0 else "SELL"
            dir_icon = "🟢" if qty > 0 else "🔴"
            avg_price = float(p.get("averagePrice", 0) or p.get("buyPrice", 0) or 0)
            ltp = float(p.get("lastPrice", 0) or 0)
            pnl = float(p.get("pnl", p.get("m2m", 0)) or 0)
            pnl_pct = (
                ((ltp - avg_price) / avg_price * 100)
                if avg_price > 0 and direction == "BUY"
                else (((avg_price - ltp) / avg_price * 100) if avg_price > 0 else 0)
            )

            pnl_sign = "+" if pnl >= 0 else "-"
            lines.append(
                f"{dir_icon} <b>{sym}</b> ({direction} × {abs(qty)})\n"
                f"  • Entry: ₹{avg_price:,.2f} | LTP: ₹{ltp:,.2f}\n"
                f"  • P&L: <code>{pnl_sign}₹{abs(pnl):,.2f} ({pnl_pct:+.2f}%)</code>"
            )

        lines.append(f"\nTotal Open: {len(open_pos)}")
        return "\n".join(lines)

    def _cmd_help(self) -> str:
        """Handle /help command."""
        return (
            "📱 <b>ANGEL ONE TELEGRAM REMOTE CONTROL</b>\n\n"
            "You can manage your trading bot remotely using these commands:\n\n"
            "📊 <b>/status</b> — Live engine status, P&L, win rate & margin\n"
            "📈 <b>/positions</b> — View all active open positions\n"
            "🚀 <b>/start</b> — Start engine in default mode\n"
            "🤖 <b>/start auto</b> — Start engine in full automated execution mode\n"
            "🛡 <b>/start confirm</b> — Start engine in confirmation mode\n"
            "🛑 <b>/stop</b> — Stop scanning and pause trading\n"
            "🚨 <b>/squareoff</b> — <b>Panic Button:</b> Exit all positions immediately\n"
            "ℹ️ <b>/help</b> — Show this command menu"
        )

    def _send_reply(self, chat_id: str, text: str):
        """Send a formatted reply back to Telegram."""
        try:
            notifier.send_telegram_message_sync(text, chat_id=chat_id)
        except Exception as e:
            logger.error("Failed to send Telegram command reply: %s", e)


telegram_bot = TelegramBotController()
