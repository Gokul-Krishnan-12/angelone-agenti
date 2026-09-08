import concurrent.futures
import datetime
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from .config import config_manager

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Dispatches Telegram notifications asynchronously for trading events."""

    def __init__(self):
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="TelegramNotifier"
        )

    def _get_config(self) -> Dict[str, Any]:
        notifications = config_manager.get_notifications_config()
        return notifications.get("telegram", {})

    def send_telegram_message_sync(
        self,
        text: str,
        parse_mode: str = "HTML",
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Synchronously send a Telegram message via the Bot API."""
        cfg = self._get_config()
        token = (
            bot_token if bot_token is not None else cfg.get("botToken", "")
        ).strip()
        cid = (chat_id if chat_id is not None else cfg.get("chatId", "")).strip()

        if not token or not cid:
            return False, "Bot Token and Chat ID are required."

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": cid,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": "true",
        }

        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": "AngelOneTradingAgent/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return True, "Message sent successfully"
                return False, f"Telegram API returned status {resp.status}"
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                err_body = str(e)
            logger.error("Telegram HTTPError: %s (%s)", e.code, err_body)
            return False, f"Telegram Error {e.code}: {err_body}"
        except Exception as e:
            logger.error("Telegram connection error: %s", e)
            return False, f"Network error: {e}"

    def send_telegram_message_async(
        self,
        text: str,
        parse_mode: str = "HTML",
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        """Queue message send in background thread pool to avoid blocking the caller."""
        return self._executor.submit(
            self.send_telegram_message_sync, text, parse_mode, bot_token, chat_id
        )

    def notify_trade_exit(self, trade: Dict[str, Any]):
        """
        Send a trade exit notification (profit or loss booked).

        Parameters
        ----------
        trade : dict with keys:
            tradingsymbol, direction, entryPrice, exitPrice, quantity,
            pnl, pnlPercent, exitReason ('TARGET' | 'STOPLOSS' | 'MANUAL'),
            mode ('Live Trading' | 'Paper Trading')
        """
        cfg = self._get_config()
        if not cfg.get("enabled", False) or not cfg.get("notifyOnTradeExit", True):
            return

        symbol = str(trade.get("tradingsymbol", "UNKNOWN")).replace("-EQ", "")
        direction = str(trade.get("direction", "BUY")).upper()
        entry_price = float(trade.get("entryPrice", 0.0) or 0.0)
        exit_price = float(trade.get("exitPrice", 0.0) or 0.0)
        qty = int(trade.get("quantity", 1) or 1)
        pnl = float(trade.get("pnl", 0.0) or 0.0)
        pnl_pct = float(trade.get("pnlPercent", 0.0) or 0.0)
        reason = str(trade.get("exitReason", "")).upper()
        mode = str(trade.get("mode", "Live Trading"))

        now_str = datetime.datetime.now().strftime("%H:%M:%S")

        is_profit = pnl >= 0
        if "TARGET" in reason or is_profit:
            header = "🎯 <b>TARGET HIT — PROFIT BOOKED</b>"
            trend_icon = "📈"
            pnl_str = f"+₹{pnl:,.2f} (+{abs(pnl_pct):.2f}%)"
        else:
            header = "🛑 <b>STOP LOSS HIT — LOSS BOOKED</b>"
            trend_icon = "📉"
            pnl_str = f"-₹{abs(pnl):,.2f} (-{abs(pnl_pct):.2f}%)"

        message = (
            f"{header}\n\n"
            f"{trend_icon} <b>Stock:</b> {symbol} ({direction})\n"
            f"💵 <b>Entry:</b> ₹{entry_price:,.2f} | <b>Exit:</b> ₹{exit_price:,.2f}\n"
            f"📦 <b>Quantity:</b> {qty}\n"
            f"💰 <b>Net P&L:</b> <code>{pnl_str}</code>\n"
            f"🏷 <b>Execution:</b> {mode}\n"
            f"⏱ <b>Time:</b> {now_str} IST"
        )

        self.send_telegram_message_async(message)

    def notify_session_summary(self, summary: Dict[str, Any]):
        """
        Send the daily session summary (total trades, win rate, net P&L).

        Parameters
        ----------
        summary : dict with keys:
            totalTrades, winningTrades, losingTrades, winRate,
            realisedPnl, totalPnl, mode ('Live' | 'Paper')
        """
        cfg = self._get_config()
        if not cfg.get("enabled", False) or not cfg.get("notifyOnSessionEnd", True):
            return

        date_str = datetime.datetime.now().strftime("%d %b %Y")
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        total_trades = int(summary.get("totalTrades", 0) or 0)
        winning = int(summary.get("winningTrades", 0) or 0)
        losing = int(summary.get("losingTrades", 0) or 0)
        win_rate = float(summary.get("winRate", 0.0) or 0.0)
        realised_pnl = float(
            summary.get("realisedPnl", 0.0) or summary.get("totalPnl", 0.0) or 0.0
        )
        mode = summary.get("mode", "Live & Paper")

        pnl_prefix = "+" if realised_pnl >= 0 else "-"
        pnl_display = f"{pnl_prefix}₹{abs(realised_pnl):,.2f}"
        status_icon = "🟢" if realised_pnl >= 0 else "🔴"

        message = (
            f"📊 <b>DAILY SESSION PERFORMANCE SUMMARY</b>\n\n"
            f"📅 <b>Date:</b> {date_str} ({now_str} IST)\n"
            f"🔢 <b>Total Trades:</b> {total_trades}\n"
            f"✅ <b>Winning:</b> {winning} | ❌ <b>Losing:</b> {losing}\n"
            f"🎯 <b>Win Rate:</b> {win_rate:.1f}%\n"
            f"{status_icon} <b>Net Realised P&L:</b> <code>{pnl_display}</code>\n"
            f"🏷 <b>Session:</b> {mode}\n"
            f"🏁 <b>Status:</b> Market Session Closed"
        )

        self.send_telegram_message_async(message)

    def notify_signal_approval(self, signal: Dict[str, Any]):
        """
        Send a signal approval notification to Telegram when a high-confluence trade is found.

        Parameters
        ----------
        signal : dict with keys:
            tradingsymbol, direction, entryPrice (or price), stopLoss, target,
            confidence, confluenceScore, familiesVoting, allStrategies, riskReward
        """
        cfg = self._get_config()
        if not cfg.get("enabled", False) or not cfg.get("notifyOnSignal", False):
            return

        symbol = str(signal.get("tradingsymbol", "UNKNOWN")).replace("-EQ", "")
        direction = str(signal.get("direction", "BUY")).upper()
        entry_price = float(signal.get("entryPrice") or signal.get("price") or 0.0)
        stop_loss = float(signal.get("stopLoss") or signal.get("sl") or 0.0)
        target = float(signal.get("target") or 0.0)
        confidence = int(signal.get("confidence", 0) or 0)
        confluence_score = int(signal.get("confluenceScore", 0) or 0)
        families = signal.get("familiesVoting", [])
        strategies = signal.get("allStrategies", [signal.get("strategy", "")])
        rr = float(signal.get("riskReward", 0.0) or 0.0)

        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        dir_icon = "🟢" if direction == "BUY" else "🔴"
        families_str = ", ".join(families) if families else "N/A"
        strats_str = ", ".join(filter(None, strategies)) if strategies else "N/A"

        risk_pct = (
            abs(entry_price - stop_loss) / entry_price * 100.0
            if entry_price > 0
            else 0.0
        )
        reward_pct = (
            abs(target - entry_price) / entry_price * 100.0 if entry_price > 0 else 0.0
        )

        message = (
            f"⚡ <b>NEW TRADING SIGNAL — APPROVAL REQUIRED</b>\n\n"
            f"{dir_icon} <b>Stock:</b> <b>{symbol}</b> ({direction})\n"
            f"💵 <b>Entry Price:</b> ₹{entry_price:,.2f}\n"
            f"🛑 <b>Stop Loss:</b> ₹{stop_loss:,.2f} ({risk_pct:.1f}% risk)\n"
            f"🎯 <b>Target:</b> ₹{target:,.2f} ({reward_pct:.1f}% reward)\n"
            f"⚖️ <b>Risk:Reward:</b> 1 : {rr:.2f}\n\n"
            f"🧠 <b>Confidence:</b> <code>{confidence}%</code>\n"
            f"🔗 <b>Confluence Score:</b> {confluence_score} Families (<code>{families_str}</code>)\n"
            f"🛠 <b>Strategies:</b> {strats_str}\n\n"
            f"⏳ <b>Status:</b> Awaiting user confirmation in Desktop App\n"
            f"⏱ <b>Generated At:</b> {now_str} IST"
        )

        self.send_telegram_message_async(message)


notifier = TelegramNotifier()
