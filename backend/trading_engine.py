import datetime
import json
import logging
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from .config import config_manager
from .notifier import notifier
from .risk_manager import risk_manager
from .scanner import scanner
from .smartapi_client import smart_api_client
from .ticker import ticker_manager
from .utils import DateTimeEncoder

logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(self):
        self.running = False
        self.thread = None
        self.mode = "confirm"  # auto or confirm
        self.interval = 60  # seconds
        self.pending_orders = {}  # order_id -> pending order info awaiting fill
        saved_trades = config_manager.get_active_trades()
        self.active_trades = (
            dict(saved_trades) if isinstance(saved_trades, dict) else {}
        )
        self._instrument_map = {}  # cached symbol -> instrument_token map
        self._last_eod_summary_date = None
        self.dynamic_watchlist = []
        self.screener_interval = 1800  # 30 min periodic dynamic re-screening
        self._last_screener_time = 0.0
        self._last_screener_date = None
        self._screener_slots_completed = set()
        self._screener_retry_due_at = 0.0
        self._screener_failed_slot = None
        self._screener_lock = threading.Lock()
        self._recent_logs: List[Dict[str, Any]] = []

        # Autonomous screener daemon: runs every 30 mins during market hours even if live trade agent is idle
        self._screener_thread = threading.Thread(
            target=self._run_screener_scheduler, daemon=True
        )
        self._screener_thread.start()

    def _run_screener_scheduler(self):
        """Autonomous background scheduler that checks if dynamic screener is due, running between 09:30 and 14:30 IST."""
        time.sleep(5)
        while True:
            try:
                self.run_clock_screener()
            except Exception as e:
                logger.error("Error in screener background scheduler: %s", e)
            time.sleep(15)




    def start(self, mode: str = "confirm"):
        if self.running:
            return

        self.mode = mode
        self.running = True
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.daemon = True
        self.thread.start()
        self._push_state_update()
        self._push_log(f"Trading engine started in {mode} mode")

    def stop(self):
        self.running = False
        self._push_state_update()
        self._push_log("Trading engine stopped")

    def status(self) -> dict:
        return {"running": self.running, "mode": self.mode}

    def _push_state_update(self):
        event = {
            "event": "agent:state-update",
            "data": {
                "running": self.running,
                "mode": self.mode,
                "status": "scanning" if self.running else "idle",
            },
        }
        print(json.dumps(event, cls=DateTimeEncoder))
        sys.stdout.flush()

    def _push_log(self, message: str, level: str = "info"):
        log_fn = getattr(logger, level.lower(), logger.info)
        log_fn(message)
        log_entry = {
            "id": str(uuid.uuid4()),
            "level": level,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        if not hasattr(self, "_recent_logs"):
            self._recent_logs = []
        self._recent_logs.insert(0, log_entry)
        if len(self._recent_logs) > 300:
            self._recent_logs = self._recent_logs[:300]

        event = {
            "event": "log:entry",
            "data": log_entry,
        }
        print(json.dumps(event, cls=DateTimeEncoder))
        sys.stdout.flush()

    def get_recent_logs(self) -> List[Dict[str, Any]]:
        return list(getattr(self, "_recent_logs", []))

    def clear_recent_logs(self):
        self._recent_logs = []

    def _push_signal(self, signal: dict):
        event = {"event": "agent:signal", "data": signal}
        print(json.dumps(event, cls=DateTimeEncoder))
        sys.stdout.flush()

    def _run_loop(self):
        last_scan_time = 0
        scan_interval = 60  # Check for new signals every 60 seconds
        monitor_interval = 5  # Check open positions every 5 seconds for rapid exits

        while self.running:
            try:
                # 1. Check pending entry orders (promotes to active_trades on fill, cancels on timeout)
                self.monitor_pending_orders()

                # 2. Fast polling: Monitor live positions for Stop-Loss / Target
                self.monitor_positions()

                # 2. Check End of Day square off
                if risk_manager.should_square_off():
                    self.square_off_all()
                    self.stop()
                    break

                # Check EOD session summary (triggered around squareOffTime)
                now_dt = datetime.datetime.now()
                today_str = now_dt.strftime("%Y-%m-%d")
                if getattr(self, "_last_day", None) != today_str:
                    risk_manager.reset_daily_trades()
                    self._last_day = today_str

                risk_cfg = config_manager.get_risk_config()
                sq_time_str = risk_cfg.get("squareOffTime", "15:15")
                try:
                    sq_t = datetime.datetime.strptime(sq_time_str, "%H:%M").time()
                except ValueError:
                    sq_t = datetime.time(15, 15)

                if now_dt.time() >= sq_t and self._last_eod_summary_date != today_str:
                    self._send_eod_summary()
                    self._last_eod_summary_date = today_str

                # 3. Slow polling: Scan for new entry signals
                current_time = time.time()
                if current_time - last_scan_time >= scan_interval:
                    self.scan_and_trade()
                    last_scan_time = current_time

            except Exception as e:
                self._push_log(f"Error in trading loop: {e}")

            # Sleep for the shorter interval (5 seconds)
            for _ in range(monitor_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _ensure_instrument_map(self):
        """Cache the NSE instrument map for reuse across scan and re-evaluation."""
        if not self._instrument_map:
            instruments = smart_api_client.get_instruments("NSE")
            self._instrument_map = {}
            for i in instruments:
                sym = i.get("tradingsymbol", "")
                tok = i.get("instrument_token", "")
                self._instrument_map[sym] = tok
                self._instrument_map[sym.replace("-EQ", "")] = tok
        return self._instrument_map

    def run_clock_screener(self, force: bool = False, slot_label_override: Optional[str] = None) -> List[str]:
        """Runs clock-aligned dynamic screener across F&O universe (09:30–14:30 IST)."""
        screener_lock = getattr(self, "_screener_lock", None)
        if screener_lock is not None and not screener_lock.acquire(blocking=False):
            logger.info("Dynamic screener already running in another thread; returning current watchlist.")
            return getattr(self, "dynamic_watchlist", [])

        try:
            now_dt = datetime.datetime.now()
            today_date = now_dt.date()
            now_time_str = now_dt.strftime("%H:%M")
            now_ts = time.time()

            from .market_hours import is_trading_day

            # Requirement: Dynamic screening ONLY happens from 09:30 to 14:30 IST on trading days
            if not force:
                if not is_trading_day(today_date) or not ("09:30" <= now_time_str <= "14:30"):
                    return getattr(self, "dynamic_watchlist", [])

            SCREENER_SLOTS = [
                "09:30", "10:00", "10:30", "11:00", "11:30",
                "12:00", "12:30", "13:00", "13:30", "14:00", "14:30"
            ]
            screener_due = force
            slot_label = slot_label_override or ""
            current_due_slot = None

            if getattr(self, "_last_screener_date", None) != today_date:
                self._screener_slots_completed = set()
                self._last_screener_date = today_date
                self._screener_retry_due_at = 0.0
                self._screener_failed_slot = None
                # Mark past slots so engine doesn't sequentially replay missed morning slots
                for s in SCREENER_SLOTS:
                    if now_time_str > s:
                        self._screener_slots_completed.add(s)

            if not screener_due:
                if not getattr(self, "dynamic_watchlist", None):
                    screener_due = True
                    passed = [s for s in SCREENER_SLOTS if now_time_str >= s]
                    if passed:
                        current_due_slot = passed[-1]
                        slot_label = f"{current_due_slot} IST"
                        for s in passed:
                            self._screener_slots_completed.add(s)
                    else:
                        current_due_slot = "09:30"
                        slot_label = "09:30 IST"
                else:
                    for s in SCREENER_SLOTS:
                        if now_time_str >= s and s not in self._screener_slots_completed:
                            screener_due = True
                            current_due_slot = s
                            slot_label = f"{s} IST"
                            break

                    # Fallback for 30-min elapsed interval (or simulated test clocks)
                    if not screener_due and (now_ts - getattr(self, "_last_screener_time", 0.0)) >= getattr(self, "screener_interval", 1800):
                        screener_due = True
                        passed = [s for s in SCREENER_SLOTS if now_time_str >= s]
                        current_due_slot = passed[-1] if passed else "09:30"
                        slot_label = f"{current_due_slot} IST"

                    if not screener_due and getattr(self, "_screener_retry_due_at", 0.0) > 0:
                        if now_ts >= self._screener_retry_due_at:
                            screener_due = True
                            current_due_slot = getattr(self, "_screener_failed_slot", "09:30")
                            slot_label = f"{current_due_slot} IST"


            if screener_due:
                from .fno_universe import get_fno_universe
                from .screener import screener_engine

                custom_watchlist = config_manager.get_watchlist()
                full_universe = list(set(get_fno_universe() + custom_watchlist))

                try:
                    screened_stocks = screener_engine.generate_daily_watchlist(
                        universe=full_universe, limit=35
                    )
                except Exception as e:
                    logger.error("Dynamic screener invocation failed: %s", e)
                    screened_stocks = []

                screener_ok = bool(screened_stocks) and getattr(screener_engine, "last_run_successful", True)
                if screened_stocks:
                    screener_ok = True
                candidate_list = (
                    list(screened_stocks) if screened_stocks else list(full_universe[:35])
                )
                combined_watchlist = list(candidate_list)
                for sym in self.active_trades:
                    if sym not in combined_watchlist:
                        combined_watchlist.append(sym)

                if screener_ok and screened_stocks:
                    self.dynamic_watchlist = combined_watchlist
                    self._last_screener_time = now_ts
                    self._screener_retry_due_at = 0.0
                    self._screener_failed_slot = None
                    if current_due_slot:
                        self._screener_slots_completed.add(current_due_slot)

                    next_slot = self.get_next_screener_slot()
                    effective_label = slot_label or f"{current_due_slot or now_time_str} IST"
                    self._push_log(
                        f"⏱️ 30-Min Scan [{effective_label}] complete. Next autonomous scan scheduled at: {next_slot}.",
                        level="info",
                    )
                    try:
                        ticker_manager.subscribe(self.dynamic_watchlist)
                    except Exception:
                        pass
                else:
                    if not getattr(self, "dynamic_watchlist", None):
                        self.dynamic_watchlist = combined_watchlist
                    self._screener_retry_due_at = now_ts + 300
                    self._screener_failed_slot = current_due_slot
        finally:
            if screener_lock is not None:
                try:
                    screener_lock.release()
                except RuntimeError:
                    pass

        return getattr(self, "dynamic_watchlist", [])

    def get_next_screener_slot(self) -> str:
        """Return the next upcoming 30-minute scan time between 09:30 and 14:30 IST."""
        now_dt = datetime.datetime.now()
        now_time_str = now_dt.strftime("%H:%M")
        SCREENER_SLOTS = [
            "09:30", "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30", "14:00", "14:30"
        ]
        upcoming = [s for s in SCREENER_SLOTS if s > now_time_str]
        if upcoming:
            return f"{upcoming[0]} IST"
        return "Tomorrow 09:30 IST"

    def scan_and_trade(self):
        can_trade, reason = risk_manager.can_trade()
        if not can_trade:
            if not getattr(self, "_notified_cannot_trade", False):
                self._push_log(
                    f"Agent is running in offline mode ({reason}). It will scan for opportunities but will NOT execute trades.",
                    level="warning",
                )
                self._notified_cannot_trade = True
        else:
            self._notified_cannot_trade = False

        # Clock-aligned Dynamic Screener
        self.run_clock_screener()

        def handle_new_signal(signal):
            if signal["confidence"] >= 70:
                self._push_signal(signal)
                confluence_score = signal.get("confluenceScore", 0)

                if self.mode == "confirm":
                    # Signals are pushed to the desktop UI for user approval without Telegram spam
                    pass
                elif self.mode == "auto" and can_trade:
                    # Confluence filter applies to BOTH auto and confirm modes.
                    # Signals from the scanner already passed the gate, but we
                    # double-check here as a safety backstop.
                    if signal["confidence"] >= 85 and confluence_score >= 2:
                        # Prevent buying the same stock if we already have an active trade for it!
                        if signal["tradingsymbol"] not in self.active_trades:
                            families = ", ".join(signal.get("familiesVoting", []))
                            self._push_log(
                                f"Auto-executing {signal['direction']} on "
                                f"{signal['tradingsymbol']} — confluence {confluence_score} "
                                f"({families}), confidence {signal['confidence']}%."
                            )
                            self.execute_signal(signal)
                        else:
                            self._push_log(
                                f"Skipping auto-trade for {signal['tradingsymbol']} as it is already an active position."
                            )

        # Scan stocks in parallel and stream signals to the UI instantly via handle_new_signal callback
        signals = scanner.scan_watchlist(self.dynamic_watchlist, on_signal=handle_new_signal)
        from .market_regime import get_current_market_regime
        regime = get_current_market_regime()
        if signals:
            syms = ", ".join(f"{s['tradingsymbol']} ({s.get('direction', 'BUY')} {s.get('confidence', 0)}%)" for s in signals[:5])
            self._push_log(
                f"🎯 Multi-Strategy Scan Complete: {len(signals)} setup(s) cleared confluence gate ({syms}). Regime: {regime}.",
                level="signal",
            )
        else:
            now_t = time.time()
            if now_t - getattr(self, "_last_scan_summary_time", 0.0) >= 300:
                self._last_scan_summary_time = now_t
                self._push_log(
                    f"ℹ️ Multi-Strategy Scan Status: Evaluated {len(self.dynamic_watchlist)} stocks across 26 technical strategies. "
                    f"0 setups met adaptive confluence gate (Regime: {regime}). Monitoring price action & key levels.",
                    level="info",
                )

        # Re-evaluate open positions for thesis invalidation
        if self.active_trades:
            self._reevaluate_positions()

    def manual_scan(self) -> List[Dict[str, Any]]:
        """Run on-demand dynamic screener and multi-strategy market scan with real-time UI Activity Logs."""
        from .fno_universe import get_fno_universe
        from .screener import screener_engine
        from .ticker import ticker_manager

        custom_watchlist = config_manager.get_watchlist()
        full_universe = list(set(get_fno_universe() + custom_watchlist))

        self._push_log(
            f"Manual Scan requested: Running dynamic momentum, RVOL & institutional flow screener across {len(full_universe)} F&O stocks...",
            level="info",
        )

        try:
            screened_stocks = screener_engine.generate_daily_watchlist(
                universe=full_universe, limit=35
            )
        except Exception as e:
            logger.error("Manual dynamic screener invocation failed: %s", e)
            screened_stocks = []

        screener_ok = getattr(screener_engine, "last_run_successful", True)
        candidate_list = (
            list(screened_stocks) if screened_stocks else list(full_universe[:35])
        )
        combined_watchlist = list(candidate_list)
        for sym in self.active_trades:
            if sym not in combined_watchlist:
                combined_watchlist.append(sym)

        self.dynamic_watchlist = combined_watchlist
        self._last_screener_time = time.time()
        try:
            ticker_manager.subscribe(self.dynamic_watchlist)
        except Exception:
            pass

        top_preview = ", ".join(self.dynamic_watchlist[:10])
        self._push_log(
            f"Dynamic Watchlist updated [Manual Scan]: Top {len(self.dynamic_watchlist)} in-play stocks shortlisted: {top_preview}...",
            level="info",
        )

        funnel = getattr(screener_engine, "last_funnel_stats", {})
        if funnel:
            self._push_log(
                f"📊 Screener Funnel [Manual Scan]: Evaluated {funnel.get('total_universe', len(full_universe))} stocks → "
                f"{funnel.get('passed_ker', 0)} passed KER ≥ 0.35, {funnel.get('passed_rvol', 0)} passed RVOL ≥ 1.8, "
                f"{funnel.get('passed_turnover', 0)} passed Turnover ≥ ₹40Cr.",
                level="info",
            )
        top_items = []
        for sym in self.dynamic_watchlist[:5]:
            st = screener_engine.get_stock_stats(sym)
            if st:
                top_items.append(
                    f"{sym} [KER: {st.get('ker', 0.5):.2f}, RVOL: {st.get('rvol', 1.0):.1f}x, 20D Vol: ₹{st.get('turnover_cr', 0):.0f}Cr, Day: {st.get('change_pct', 0):+.1f}%, Score: {st.get('score', 0):.1f}]"
                )
            else:
                top_items.append(sym)
        if top_items:
            self._push_log(
                f"🔥 Top Shortlist Breakdown [Manual Scan]: " + " | ".join(top_items),
                level="info",
            )

        self._push_log(
            f"Scanning shortlisted {len(self.dynamic_watchlist)} stocks across 26 technical strategies...",
            level="info",
        )

        def handle_manual_signal(signal):
            if signal.get("confidence", 0) >= 70:
                self._push_signal(signal)

        signals = scanner.scan_watchlist(
            self.dynamic_watchlist, on_signal=handle_manual_signal
        )

        from .market_regime import get_current_market_regime
        regime = get_current_market_regime()
        if signals:
            syms = ", ".join(s["tradingsymbol"] for s in signals[:5])
            self._push_log(
                f"Manual scan complete: {len(signals)} setup(s) identified ({syms}). Regime: {regime}.",
                level="order",
            )
        else:
            self._push_log(
                f"Manual scan complete: 0 trade setups met the 3-family confluence & R:R gate across {len(self.dynamic_watchlist)} stocks under {regime} regime.",
                level="info",
            )

        next_slot = self.get_next_screener_slot()
        self._push_log(
            f"⏱️ Next autonomous 30-min scan scheduled at: {next_slot}.",
            level="info",
        )

        return signals or []

    def execute_signal(self, signal: dict):
        can_trade, reason = risk_manager.can_trade()
        if not can_trade:
            self._push_log(
                f"Cannot execute signal {signal.get('id', 'unknown')}: {reason}"
            )
            return False

        tradingsymbol = signal.get("tradingsymbol", "")
        entry_price = float(
            signal.get("entryPrice")
            or signal.get("entry_price")
            or signal.get("price")
            or 0.0
        )
        stop_loss = float(signal.get("stopLoss") or signal.get("stop_loss") or 0.0)
        target = float(signal.get("target") or 0.0)
        direction = signal.get("direction", "BUY").upper()
        exchange = signal.get("exchange", "NSE")

        if not tradingsymbol or entry_price <= 0 or stop_loss <= 0:
            self._push_log(
                f"Cannot execute signal: missing tradingsymbol ({tradingsymbol}), "
                f"entryPrice ({entry_price}), or stopLoss ({stop_loss})"
            )
            return False

        qty = risk_manager.calculate_position_size(entry_price, stop_loss)
        if qty <= 0:
            self._push_log(
                f"Position size calculated as 0 for {tradingsymbol}. Skipping trade."
            )
            return False

        # Pre-Trade Statutory Friction Guard (Angel One estimateCharges validation)
        charges_info = smart_api_client.estimate_round_trip_charges(
            tradingsymbol,
            entry_price,
            target,
            qty,
            product="INTRADAY",
            exchange=exchange,
            direction=direction,
        )
        if not charges_info.get("is_friction_safe", True):
            self._push_log(
                f"Statutory Friction Guard: Trade on {tradingsymbol} rejected. "
                f"Expected gain ₹{charges_info.get('gross_pnl', 0)} < 3.5x Angel One charges (₹{charges_info.get('total_charges', 0)}).",
                level="warning",
            )
            return False

        self._push_log(
            f"Friction check passed for {tradingsymbol}: Net gain ₹{charges_info.get('net_pnl', 0)} "
            f"(Charges: ₹{charges_info.get('total_charges', 0)}, Multiple: {charges_info.get('friction_multiple', 0)}x)",
            level="info",
        )

        transaction_type = "BUY" if direction == "BUY" else "SELL"

        try:
            risk_cfg = config_manager.get_risk_config()
            pullback_enabled = bool(risk_cfg.get("pullbackEntryEnabled", False))
            scale_in_enabled = pullback_enabled and bool(risk_cfg.get("scaleInEnabled", False))
            leg1_ratio = float(risk_cfg.get("scaleInLeg1Ratio", 0.5))
            partial_enabled = bool(risk_cfg.get("partialBookingEnabled", True))
            target1_rr = float(risk_cfg.get("partialBookingTargetRR", 1.2))
            risk_dist = abs(entry_price - stop_loss)

            # ── 2-Leg Scale-In: Leg 1 qty calculation ─────────────────────
            if scale_in_enabled and qty >= 2:
                leg1_qty = max(1, int(qty * leg1_ratio))
                leg2_qty = qty - leg1_qty
                order_qty = leg1_qty
                scale_in_pending = True
                # Compute Leg 2 pullback price from cached candles (EMA20/VWAP)
                try:
                    token = self._ensure_instrument_map().get(tradingsymbol)
                    if token and token in scanner.candle_cache:
                        from .strategy_engine import calculate_pullback_limit_entry
                        leg2_price = calculate_pullback_limit_entry(
                            df=scanner.candle_cache[token],
                            direction=direction,
                            breakout_level=None,  # no breakout ref — use EMA20/VWAP only
                        )
                    else:
                        leg2_price = 0.0
                except Exception:
                    leg2_price = 0.0
            else:
                order_qty = qty
                leg1_qty = qty
                leg2_qty = 0
                scale_in_pending = False
                leg2_price = 0.0

            order_id = smart_api_client.place_order(
                variety="NORMAL",
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=order_qty,
                product="INTRADAY",
                order_type="LIMIT",
                price=entry_price,
            )

            if scale_in_pending:
                self._push_log(
                    f"Scale-In Leg 1: {transaction_type} {order_qty}/{qty} shares of {tradingsymbol} "
                    f"@ ₹{entry_price:.2f} (Leg 2: {leg2_qty} shares @ pullback ₹{leg2_price:.2f}). "
                    f"Order ID: {order_id}",
                    level="info",
                )
            else:
                self._push_log(
                    f"Executed {transaction_type} for {tradingsymbol}, qty {order_qty}, order_id {order_id}"
                )

            risk_manager.increment_trade()

            # Compute Target 1 for partial booking (based on full position risk_dist)
            target1 = target
            target2 = target
            if partial_enabled and risk_dist > 0:
                if direction == "BUY":
                    target1 = round(entry_price + (risk_dist * target1_rr), 2)
                else:
                    target1 = round(entry_price - (risk_dist * target1_rr), 2)

            self.pending_orders[str(order_id)] = {
                "order_id": str(order_id),
                "tradingsymbol": tradingsymbol,
                "exchange": exchange,
                "direction": direction,
                "quantity": order_qty,
                "total_planned_qty": qty,  # full position size (both legs combined)
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "target": target,
                "target1": target1,
                "target2": target2,
                "original_strategy": signal.get("strategy", "unknown"),
                "atr": signal.get("indicators", {}).get("atr", 0.0),
                "submitted_at": time.time(),
                # Scale-in metadata
                "scale_in_pending": scale_in_pending,
                "scale_in_leg2_qty": leg2_qty,
                "scale_in_leg2_price": leg2_price,
            }
            return True
        except Exception as e:
            self._push_log(f"Failed to execute signal: {e}")
            return False

    def _place_exchange_stop_loss(
        self,
        symbol: str,
        exchange: str,
        direction: str,
        quantity: int,
        stop_loss: float,
    ) -> str:
        """Place native exchange Stop-Loss Limit order to protect position."""
        tx_type = "SELL" if direction == "BUY" else "BUY"
        if tx_type == "SELL":
            limit_price = round(stop_loss * 0.99, 2)
        else:
            limit_price = round(stop_loss * 1.01, 2)

        try:
            sl_order_id = smart_api_client.place_order(
                variety="STOPLOSS",
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=tx_type,
                quantity=quantity,
                product="INTRADAY",
                order_type="STOPLOSS_LIMIT",
                price=limit_price,
                trigger_price=stop_loss,
            )
            self._push_log(
                f"Placed Exchange SL order for {symbol} (trigger: ₹{stop_loss:.2f}, limit: ₹{limit_price:.2f}), SL Order ID: {sl_order_id}"
            )
            return str(sl_order_id)
        except Exception as e:
            self._push_log(
                f"Warning: Failed to place native exchange SL for {symbol}: {e}. Local fallback will monitor.",
                level="warning",
            )
            return ""

    def monitor_pending_orders(self):
        """Monitor pending entry orders. Promote to active_trades on fill, cancel on timeout."""
        if not self.pending_orders:
            return

        try:
            risk_cfg = config_manager.get_risk_config()
            timeout_secs = int(risk_cfg.get("pendingOrderTimeoutSeconds", 15))
            orders = smart_api_client.get_orders(force=True)
            order_map = {str(o.get("orderId")): o for o in orders if o.get("orderId")}
            now = time.time()
            to_remove = []

            for order_id, pending in list(self.pending_orders.items()):
                order_info = order_map.get(order_id)
                status = (order_info.get("status") if order_info else "").upper()
                symbol = pending["tradingsymbol"]

                if status in ("COMPLETE", "COMPLETED"):
                    fill_price = float(
                        order_info.get("averagePrice") or pending["entry_price"]
                    )
                    fill_qty = int(
                        order_info.get("filledQuantity") or pending["quantity"]
                    )
                    direction = pending["direction"]
                    sl = pending["stop_loss"]
                    target = pending["target"]

                    # ── Scale-In Leg 2 fill: weighted average entry update ──
                    if pending.get("is_scale_in_leg2"):
                        leg1_sym = symbol
                        if leg1_sym in self.active_trades:
                            trade = self.active_trades[leg1_sym]
                            leg1_qty = int(trade.get("leg1_qty", trade["initial_quantity"]))
                            leg1_price = float(trade.get("leg1_fill_price", trade["entry_price"]))
                            total_qty = leg1_qty + fill_qty
                            avg_entry = round(
                                (leg1_price * leg1_qty + fill_price * fill_qty) / total_qty, 2
                            )
                            trade["entry_price"] = avg_entry
                            trade["initial_quantity"] = total_qty
                            trade["scale_in_done"] = True
                            config_manager.save_active_trades(self.active_trades)
                            self._push_log(
                                f"Scale-In Leg 2 FILLED for {symbol}: {fill_qty} shares @ ₹{fill_price:.2f}. "
                                f"Avg Entry updated to ₹{avg_entry:.2f} ({total_qty} total shares).",
                                level="info",
                            )
                        to_remove.append(order_id)
                        continue  # skip normal promote-to-active-trades logic

                    self._push_log(
                        f"Entry order {order_id} FILLED for {symbol}: {fill_qty} shares @ ₹{fill_price:.2f}"
                    )

                    # Place native exchange-side Stop Loss (covers full risk from Leg 1)
                    sl_order_id = self._place_exchange_stop_loss(
                        symbol=symbol,
                        exchange=pending["exchange"],
                        direction=direction,
                        quantity=fill_qty,
                        stop_loss=sl,
                    )

                    self.active_trades[symbol] = {
                        "sl": sl,
                        "initial_sl": sl,
                        "sl_order_id": sl_order_id,
                        "target": target,
                        "target1": pending.get("target1", target),
                        "target2": pending.get("target2", target),
                        "partial_booked": False,
                        "initial_quantity": fill_qty,
                        "direction": direction,
                        "entry_price": fill_price,
                        "entry_time": datetime.datetime.now().isoformat(),
                        "original_strategy": pending["original_strategy"],
                        "atr": pending["atr"],
                        "high_water_mark": fill_price,
                        "low_water_mark": fill_price,
                        # Scale-in tracking
                        "leg1_qty": fill_qty,
                        "leg1_fill_price": fill_price,
                        "scale_in_done": False,
                    }
                    config_manager.save_active_trades(self.active_trades)
                    try:
                        ticker_manager.subscribe([symbol])
                    except Exception:
                        pass

                    # ── Scale-In: place Leg 2 at pullback if applicable ────────
                    if pending.get("scale_in_pending") and pending.get("scale_in_leg2_qty", 0) > 0:
                        leg2_qty = int(pending["scale_in_leg2_qty"])
                        leg2_price = float(pending.get("scale_in_leg2_price", 0.0))
                        # Recompute leg2_price if not cached (fresh candle fallback)
                        if leg2_price <= 0:
                            try:
                                token = self._ensure_instrument_map().get(symbol)
                                if token and token in scanner.candle_cache:
                                    from .strategy_engine import calculate_pullback_limit_entry
                                    leg2_price = calculate_pullback_limit_entry(
                                        df=scanner.candle_cache[token],
                                        direction=direction,
                                        breakout_level=None,
                                    )
                            except Exception:
                                leg2_price = 0.0

                        if leg2_price > 0:
                            try:
                                leg2_timeout = int(
                                    risk_cfg.get("pendingOrderTimeoutSeconds", 15)
                                ) * int(risk_cfg.get("scaleInLeg2TimeoutMultiplier", 2))
                                leg2_tx = "BUY" if direction == "BUY" else "SELL"
                                leg2_order_id = smart_api_client.place_order(
                                    variety="NORMAL",
                                    exchange=pending["exchange"],
                                    tradingsymbol=symbol,
                                    transaction_type=leg2_tx,
                                    quantity=leg2_qty,
                                    product="INTRADAY",
                                    order_type="LIMIT",
                                    price=leg2_price,
                                )
                                self.pending_orders[str(leg2_order_id)] = {
                                    "order_id": str(leg2_order_id),
                                    "tradingsymbol": symbol,
                                    "exchange": pending["exchange"],
                                    "direction": direction,
                                    "quantity": leg2_qty,
                                    "entry_price": leg2_price,
                                    "stop_loss": sl,
                                    "target": target,
                                    "target1": pending.get("target1", target),
                                    "target2": pending.get("target2", target),
                                    "original_strategy": pending["original_strategy"],
                                    "atr": pending["atr"],
                                    "submitted_at": time.time(),
                                    "is_scale_in_leg2": True,
                                    "_leg2_timeout": leg2_timeout,
                                }
                                self._push_log(
                                    f"Scale-In Leg 2 queued for {symbol}: {leg2_qty} shares "
                                    f"@ ₹{leg2_price:.2f} LIMIT (timeout: {leg2_timeout}s).",
                                    level="info",
                                )
                            except Exception as e2:
                                self._push_log(
                                    f"Scale-In Leg 2 order failed for {symbol}: {e2}. Leg 1 trade active.",
                                    level="warning",
                                )

                    to_remove.append(order_id)

                elif status in ("CANCELLED", "REJECTED"):
                    reason = (
                        order_info.get("statusMessage", "Cancelled/Rejected")
                        if order_info
                        else "Cancelled"
                    )
                    self._push_log(
                        f"Entry order {order_id} for {symbol} was {status}: {reason}",
                        level="warning",
                    )
                    to_remove.append(order_id)

                elif (now - pending.get("submitted_at", now)) > (
                    pending.get("_leg2_timeout", timeout_secs) if pending.get("is_scale_in_leg2") else timeout_secs
                ):
                    # Timeout: Leg 2 uses 2x timeout multiplier; Leg 1 uses normal timeout
                    is_leg2 = pending.get("is_scale_in_leg2", False)
                    self._push_log(
                        f"{'Scale-In Leg 2' if is_leg2 else 'Entry'} order {order_id} for {symbol} "
                        f"timed out. {'Leg 1 position continues.' if is_leg2 else 'Cancelling.'}",
                        level="warning",
                    )
                    try:
                        smart_api_client.cancel_order(
                            variety="NORMAL", order_id=order_id
                        )
                    except Exception as e:
                        self._push_log(
                            f"Error cancelling timed-out order {order_id}: {e}",
                            level="warning",
                        )
                    to_remove.append(order_id)

            for o_id in to_remove:
                self.pending_orders.pop(o_id, None)

        except Exception as e:
            self._push_log(f"Error in monitor_pending_orders: {e}", level="warning")

    def _get_exit_limit_price(self, ltp: float, tx_type: str) -> float:
        # A pseudo-market limit order to ensure immediate fill without Kite MARKET restrictions
        buffer = 0.01  # 1% buffer
        if tx_type == "BUY":
            return round(ltp * (1 + buffer), 2)
        else:
            return round(ltp * (1 - buffer), 2)

    def monitor_positions(self):
        try:
            positions = smart_api_client.get_positions().get("net", [])
            open_count = sum(1 for p in positions if p["quantity"] != 0)
            risk_manager.set_open_positions(open_count)

            # Get symbols of currently open positions to track manual closures
            open_symbols = set()
            for p in positions:
                if p["quantity"] != 0:
                    sym = p["tradingsymbol"]
                    open_symbols.add(sym)
                    open_symbols.add(sym.replace("-EQ", ""))

            if open_symbols:
                try:
                    ticker_manager.subscribe(list(open_symbols))
                except Exception:
                    pass

            # Clean up active_trades if position was closed manually via Angel One App or SL filled
            symbols_to_remove = []
            for symbol in self.active_trades.keys():
                clean_sym = symbol.replace("-EQ", "")
                if symbol not in open_symbols and clean_sym not in open_symbols:
                    symbols_to_remove.append(symbol)
            for symbol in symbols_to_remove:
                trade = self.active_trades.get(symbol, {})
                sl_id = trade.get("sl_order_id")
                if sl_id:
                    try:
                        smart_api_client.cancel_order(
                            variety="STOPLOSS", order_id=sl_id
                        )
                    except Exception:
                        pass
                self._push_log(
                    f"Detected closure for {symbol}. Removing from tracking."
                )
                del self.active_trades[symbol]
            if symbols_to_remove:
                config_manager.save_active_trades(self.active_trades)

            # Evaluate SL and Targets
            for p in positions:
                if p["quantity"] != 0:
                    symbol = p["tradingsymbol"]
                    clean_symbol = symbol.replace("-EQ", "")
                    active_key = (
                        clean_symbol if clean_symbol in self.active_trades else symbol
                    )

                    # Adopt untracked positions in auto mode
                    if active_key not in self.active_trades and self.mode == "auto":
                        avg_price = p.get("averagePrice", 0)
                        if avg_price > 0:
                            direction = "BUY" if p["quantity"] > 0 else "SELL"
                            risk_config = config_manager.get_risk_config()
                            sl_pct = risk_config.get("defaultStopLossPercent", 1.5)
                            tgt_pct = risk_config.get("defaultTargetPercent", 3.0)

                            if direction == "BUY":
                                sl = round(avg_price * (1 - sl_pct / 100), 2)
                                target = round(avg_price * (1 + tgt_pct / 100), 2)
                            else:
                                sl = round(avg_price * (1 + sl_pct / 100), 2)
                                target = round(avg_price * (1 - tgt_pct / 100), 2)

                            self.active_trades[active_key] = {
                                "sl": sl,
                                "initial_sl": sl,
                                "sl_order_id": "",
                                "target": target,
                                "direction": direction,
                                "entry_price": avg_price,
                                "entry_time": datetime.datetime.now().isoformat(),
                                "original_strategy": "adopted",
                            }
                            sl_id = self._place_exchange_stop_loss(
                                symbol=symbol,
                                exchange=p["exchange"],
                                direction=direction,
                                quantity=abs(p["quantity"]),
                                stop_loss=sl,
                            )
                            self.active_trades[active_key]["sl_order_id"] = sl_id
                            config_manager.save_active_trades(self.active_trades)
                            self._push_log(
                                f"Adopted open position {symbol} ({direction}) at ₹{avg_price}. Auto-calculated SL: ₹{sl}, Target: ₹{target}"
                            )
                            try:
                                ticker_manager.subscribe([active_key])
                            except Exception:
                                pass

                    if active_key in self.active_trades:
                        trade = self.active_trades[active_key]
                        ltp = p.get("lastPrice", 0)
                        if ltp == 0:
                            continue

                        current_qty = abs(p["quantity"])
                        if current_qty == 0:
                            continue

                        risk_config = config_manager.get_risk_config()
                        partial_enabled = bool(
                            risk_config.get("partialBookingEnabled", True)
                        )

                        # ── Check Target 1 (Partial Profit Booking) ───────────
                        if (
                            partial_enabled
                            and not trade.get("partial_booked", False)
                            and current_qty >= 2
                        ):
                            from .watchdog import watchdog
                            from .order_manager import order_manager

                            t1_eval = watchdog.evaluate_exit_curve(
                                trade=trade,
                                ltp=ltp,
                                current_qty=current_qty,
                                exchange=p.get("exchange", "NSE"),
                                product_type=p.get("product", "INTRADAY"),
                                target1_r_mult=float(risk_config.get("partialBookingTargetRR", 1.2)),
                            )

                            if t1_eval.get("trigger_t1"):
                                exit_qty = t1_eval["t1_exit_qty"]
                                be_sl = t1_eval["breakeven_sl"]
                                tx_type = "SELL" if p["quantity"] > 0 else "BUY"

                                smart_api_client.place_order(
                                    variety="NORMAL",
                                    exchange=p["exchange"],
                                    tradingsymbol=symbol,
                                    transaction_type=tx_type,
                                    quantity=exit_qty,
                                    product=p.get("product", "INTRADAY"),
                                    order_type="LIMIT",
                                    price=self._get_exit_limit_price(ltp, tx_type),
                                )

                                remaining_qty = current_qty - exit_qty
                                trade["sl"] = be_sl
                                trade["partial_booked"] = True
                                trade["target"] = trade.get("target2", trade["target"])

                                self._push_log(t1_eval.get("message", f"Target 1 booked for {symbol}"))

                                # Atomic Stop-Loss Ratchet via OrderManager
                                old_sl_id = trade.get("sl_order_id")
                                if old_sl_id and remaining_qty > 0:
                                    mod_res = order_manager.atomic_modify_stop_loss(
                                        order_id=old_sl_id,
                                        symbol=symbol,
                                        exchange=p["exchange"],
                                        direction=trade["direction"],
                                        quantity=remaining_qty,
                                        trigger_price=be_sl,
                                        variety="STOPLOSS",
                                        product_type=p.get("product", "INTRADAY"),
                                    )
                                    if mod_res["success"]:
                                        self._push_log(
                                            f"Atomically modified exchange SL {old_sl_id} for {symbol} "
                                            f"to Breakeven+Friction @ ₹{be_sl:.2f} (qty: {remaining_qty})."
                                        )
                                    elif mod_res.get("emergency_exit_required"):
                                        # Emergency market close to eliminate unhedged exposure
                                        self._push_log(
                                            f"CRITICAL: Atomic SL modification failed for {symbol}. "
                                            f"Triggering emergency market close for {remaining_qty} shares to eliminate unhedged exposure.",
                                            level="warning",
                                        )
                                        order_manager.emergency_market_close(
                                            symbol=symbol,
                                            exchange=p["exchange"],
                                            quantity=remaining_qty,
                                            direction=trade["direction"],
                                            product=p.get("product", "INTRADAY"),
                                        )
                                        self.active_trades.pop(symbol, None)
                                        config_manager.save_active_trades(self.active_trades)
                                        continue

                                config_manager.save_active_trades(self.active_trades)
                                expected_gain = abs(ltp - trade["entry_price"]) * exit_qty
                                self._push_log(
                                    f"🎯 PARTIAL TARGET 1 HIT for {symbol}: Booked {exit_qty} shares at ₹{ltp:.2f} "
                                    f"(+₹{expected_gain:.2f}). Moved SL to Breakeven+Friction @ ₹{be_sl:.2f}. "
                                    f"{remaining_qty} runner shares targeting ₹{trade['target']:.2f}."
                                )

                                try:
                                    notifier.notify_trade_exit(
                                        {
                                            "tradingsymbol": symbol,
                                            "direction": trade.get("direction", "BUY"),
                                            "entryPrice": trade["entry_price"],
                                            "exitPrice": ltp,
                                            "quantity": exit_qty,
                                            "pnl": round(expected_gain, 2),
                                            "pnlPercent": round(
                                                abs(ltp - trade["entry_price"])
                                                / trade["entry_price"]
                                                * 100,
                                                2,
                                            ),
                                            "exitReason": "PARTIAL_TARGET",
                                            "mode": f"Live Trading ({self.mode.capitalize()})",
                                        }
                                    )
                                except Exception:
                                    pass
                                continue

                        hit_sl = False
                        hit_target = False

                        if trade["direction"] == "BUY":
                            if ltp <= trade["sl"]:
                                hit_sl = True
                            if ltp >= trade["target"]:
                                hit_target = True
                        else:
                            if ltp >= trade["sl"]:
                                hit_sl = True
                            if ltp <= trade["target"]:
                                hit_target = True

                        if hit_sl or hit_target:
                            # Cancel resting exchange SL order if target was hit or before sending manual exit
                            sl_id = trade.get("sl_order_id")
                            if sl_id:
                                try:
                                    smart_api_client.cancel_order(
                                        variety="STOPLOSS", order_id=sl_id
                                    )
                                except Exception:
                                    pass
                            trade["sl_order_id"] = ""
                            config_manager.save_active_trades(self.active_trades)

                            reason = (
                                "Breakeven Stop Loss"
                                if (hit_sl and trade.get("partial_booked", False))
                                else ("Stop Loss" if hit_sl else "Target")
                            )
                            self._push_log(
                                f"{reason} hit for {symbol} at {ltp}. Exiting position."
                            )

                            tx_type = "SELL" if p["quantity"] > 0 else "BUY"
                            smart_api_client.place_order(
                                variety="NORMAL",
                                exchange=p["exchange"],
                                tradingsymbol=symbol,
                                transaction_type=tx_type,
                                quantity=abs(p["quantity"]),
                                product=p.get("product", "INTRADAY"),
                                order_type="LIMIT",
                                price=self._get_exit_limit_price(ltp, tx_type),
                            )

                            # Dispatch Telegram notification
                            try:
                                entry_p = float(trade.get("entry_price", ltp) or ltp)
                                qty = abs(p["quantity"])
                                is_buy = trade.get("direction", "BUY") == "BUY"
                                pnl = (
                                    (ltp - entry_p) * qty
                                    if is_buy
                                    else (entry_p - ltp) * qty
                                )
                                pnl_pct = (
                                    ((ltp - entry_p) / entry_p * 100)
                                    * (1 if is_buy else -1)
                                    if entry_p > 0
                                    else 0.0
                                )
                                notifier.notify_trade_exit(
                                    {
                                        "tradingsymbol": symbol,
                                        "direction": trade.get("direction", "BUY"),
                                        "entryPrice": entry_p,
                                        "exitPrice": ltp,
                                        "quantity": qty,
                                        "pnl": round(pnl, 2),
                                        "pnlPercent": round(pnl_pct, 2),
                                        "exitReason": "TARGET"
                                        if hit_target
                                        else "STOPLOSS",
                                        "mode": f"Live Trading ({self.mode.capitalize()})",
                                    }
                                )
                            except Exception as notif_err:
                                self._push_log(
                                    f"Telegram exit alert error: {notif_err}",
                                    level="warning",
                                )

                            # Let the manual closure cleanup handle removing it on the next loop
                        else:
                            # ── ATR Trailing Stop-Loss ─────────────────────────
                            risk_config = config_manager.get_risk_config()
                            if risk_config.get("trailingSlEnabled", True):
                                tsl_mult = float(
                                    risk_config.get("trailingSlAtrMultiplier", 2.0)
                                )
                                trade["cushion_r"] = float(
                                    risk_config.get("trailingSlProfitCushionR", 1.0)
                                )
                                # Reuse ATR stored at entry; refresh if 0
                                atr = float(trade.get("atr", 0))
                                if atr <= 0:
                                    # Try to compute from cached candles
                                    try:
                                        from .strategies.utils import compute_atr

                                        token = self._ensure_instrument_map().get(
                                            active_key
                                        )
                                        if token and token in scanner.candle_cache:
                                            atr = compute_atr(
                                                scanner.candle_cache[token]
                                            )
                                            trade["atr"] = atr
                                    except Exception:
                                        pass

                                new_sl = risk_manager.update_trailing_sl(
                                    trade, ltp, atr, tsl_mult
                                )
                                if new_sl is not None:
                                    old_sl = trade["sl"]
                                    trade["sl"] = new_sl
                                    # Modify exchange-side SL order trigger and limit price
                                    sl_id = trade.get("sl_order_id")
                                    if sl_id:
                                        tx_type = (
                                            "SELL"
                                            if trade["direction"] == "BUY"
                                            else "BUY"
                                        )
                                        lim_p = (
                                            round(new_sl * 0.99, 2)
                                            if tx_type == "SELL"
                                            else round(new_sl * 1.01, 2)
                                        )
                                        try:
                                            smart_api_client.modify_order(
                                                variety="STOPLOSS",
                                                order_id=sl_id,
                                                tradingsymbol=symbol,
                                                order_type="STOPLOSS_LIMIT",
                                                price=lim_p,
                                                trigger_price=new_sl,
                                            )
                                        except Exception as e:
                                            self._push_log(
                                                f"Error modifying exchange SL {sl_id}: {e}",
                                                level="warning",
                                            )

                                    self._push_log(
                                        f"Trailing SL ratcheted for {symbol}: "
                                        f"₹{old_sl:.2f} → ₹{new_sl:.2f} "
                                        f"(ATR {atr:.2f} × {tsl_mult})"
                                    )
                                    config_manager.save_active_trades(
                                        self.active_trades
                                    )
        except Exception as e:
            self._push_log(f"Error monitoring positions: {e}")

    def _reevaluate_positions(self):
        """Re-evaluate open positions against current strategy signals (thesis invalidation)."""
        if not self.active_trades:
            return

        risk_config = config_manager.get_risk_config()
        weak_exit_mins = risk_config.get("positionRevalWeakExitMins", 15)
        breakeven_mins = risk_config.get("positionRevalBreakevenMins", 20)
        instrument_map = self._ensure_instrument_map()
        now = datetime.datetime.now()

        # Get current positions for P&L and LTP data
        try:
            positions = smart_api_client.get_positions().get("net", [])
            position_map = {
                p["tradingsymbol"]: p for p in positions if p["quantity"] != 0
            }
            # Also map clean symbol
            for p in positions:
                if p["quantity"] != 0:
                    position_map[p["tradingsymbol"].replace("-EQ", "")] = p
        except Exception as e:
            self._push_log(f"Error fetching positions for re-evaluation: {e}")
            return

        # Snapshot keys to avoid modifying dict during iteration
        symbols_to_evaluate = list(self.active_trades.keys())

        for symbol in symbols_to_evaluate:
            if symbol not in self.active_trades:
                continue  # May have been removed by a prior iteration

            trade = self.active_trades[symbol]
            token = instrument_map.get(symbol)
            if not token:
                continue

            # Get current position data
            pos = position_map.get(symbol)
            if not pos:
                continue  # Position already closed

            # Evaluate current strategy signals for this symbol
            try:
                evaluation = scanner.evaluate_position(symbol, token)
            except Exception as e:
                self._push_log(f"Error evaluating {symbol}: {e}")
                continue

            direction = trade["direction"]
            entry_time = trade.get("entry_time", now)
            entry_price = trade.get("entry_price", pos.get("averagePrice", 0))
            mins_held = (now - entry_time).total_seconds() / 60
            ltp = pos.get("lastPrice", 0)

            # Determine P&L direction
            if direction == "BUY":
                in_loss = ltp < entry_price
                supporting = evaluation["buy_signals"]
                opposing = evaluation["sell_signals"]
            else:
                in_loss = ltp > entry_price
                supporting = evaluation["sell_signals"]
                opposing = evaluation["buy_signals"]

            # === Graduated Exit Rules ===

            # Rule 1: Strong opposing signal — thesis fully invalidated
            if opposing >= 2 and supporting == 0:
                reason = f"Thesis invalidated for {symbol}: {opposing} opposing signals, 0 supporting. Exiting."
                self._push_log(reason, level="warning")
                if self.mode == "auto":
                    self._exit_position(pos, symbol, reason)
                continue

            # Rule 2: Weak conviction — no support + in loss + time elapsed
            if supporting == 0 and in_loss and mins_held >= weak_exit_mins:
                reason = f"Weak conviction for {symbol}: 0 supporting signals, in loss, held {mins_held:.0f} mins. Exiting."
                self._push_log(reason, level="warning")
                if self.mode == "auto":
                    self._exit_position(pos, symbol, reason)
                continue

            # Rule 3: Idle Trade Circuit Breaker (held >= 35 mins without +0.6R)
            from .watchdog import watchdog

            stagnation_mins = float(risk_config.get("stagnationTimeoutMins", 35.0))
            stagnation_r = float(risk_config.get("stagnationMinRequiredR", 0.6))
            idle_exit, idle_reason = watchdog.check_idle_trade_circuit_breaker(
                trade=trade,
                ltp=ltp,
                mins_held=mins_held,
                stagnation_timeout_mins=stagnation_mins,
                min_required_r=stagnation_r,
            )
            if idle_exit:
                self._push_log(idle_reason, level="warning")
                if self.mode == "auto":
                    self._exit_position(pos, symbol, idle_reason)
                continue

            # Rule 3b: Time decay — tighten to breakeven if held >= breakeven_mins
            if mins_held >= breakeven_mins:
                if entry_price > 0 and trade["sl"] != entry_price:
                    old_sl = trade["sl"]
                    self._tighten_to_breakeven(symbol)
                    self._push_log(
                        f"Time decay for {symbol}: held {mins_held:.0f} mins. SL tightened from ₹{old_sl} to breakeven ₹{entry_price}."
                    )
                continue

            # Rule 4: Thesis still valid — hold
            if supporting > 0:
                self._push_log(
                    f"Thesis valid for {symbol}: {supporting} supporting, {opposing} opposing. Holding."
                )

    def _tighten_to_breakeven(self, symbol: str):
        """Move the stop-loss to the entry price (breakeven) atomically."""
        if symbol in self.active_trades:
            trade = self.active_trades[symbol]
            entry_price = trade.get("entry_price", 0)
            if entry_price > 0:
                trade["sl"] = entry_price
                sl_id = trade.get("sl_order_id")
                if sl_id:
                    from .order_manager import order_manager

                    qty = int(trade.get("initial_quantity", 1))
                    mod_res = order_manager.atomic_modify_stop_loss(
                        order_id=sl_id,
                        symbol=symbol,
                        exchange=trade.get("exchange", "NSE"),
                        direction=trade["direction"],
                        quantity=qty,
                        trigger_price=entry_price,
                        variety="STOPLOSS",
                    )
                    if not mod_res["success"]:
                        self._push_log(
                            f"Error modifying exchange SL order {sl_id} to breakeven: {mod_res.get('message')}",
                            level="warning",
                        )
                config_manager.save_active_trades(self.active_trades)

    def _exit_position(self, position: dict, symbol: str, reason: str):
        """Exit a position due to thesis invalidation."""
        try:
            if symbol in self.active_trades:
                sl_id = self.active_trades[symbol].get("sl_order_id")
                if sl_id:
                    try:
                        smart_api_client.cancel_order(
                            variety="STOPLOSS", order_id=sl_id
                        )
                    except Exception:
                        pass
                self.active_trades[symbol]["sl_order_id"] = ""
                config_manager.save_active_trades(self.active_trades)

            ltp = position.get("lastPrice", 0)
            if ltp == 0:
                self._push_log(f"Cannot exit {symbol}: no LTP available")
                return

            tx_type = "SELL" if position["quantity"] > 0 else "BUY"
            smart_api_client.place_order(
                variety="NORMAL",
                exchange=position["exchange"],
                tradingsymbol=symbol,
                transaction_type=tx_type,
                quantity=abs(position["quantity"]),
                product=position.get("product", "INTRADAY"),
                order_type="LIMIT",
                price=self._get_exit_limit_price(ltp, tx_type),
            )
            self._push_log(f"Thesis exit order placed for {symbol} ({tx_type})")
            # Cleanup will happen via the manual closure detection in monitor_positions
        except Exception as e:
            self._push_log(f"Failed to exit {symbol}: {e}")

    def square_off_all(self):
        self._push_log("Squaring off all open positions")
        try:
            positions = smart_api_client.get_positions().get("net", [])
            for p in positions:
                if p["quantity"] != 0:
                    sym = p["tradingsymbol"]
                    clean = sym.replace("-EQ", "")
                    for k in (sym, clean):
                        if k in self.active_trades:
                            sl_id = self.active_trades[k].get("sl_order_id")
                            if sl_id:
                                try:
                                    smart_api_client.cancel_order(
                                        variety="STOPLOSS", order_id=sl_id
                                    )
                                except Exception:
                                    pass

                    tx_type = "SELL" if p["quantity"] > 0 else "BUY"
                    ltp = p.get("lastPrice", 0)

                    smart_api_client.place_order(
                        variety="NORMAL",
                        exchange=p["exchange"],
                        tradingsymbol=p["tradingsymbol"],
                        transaction_type=tx_type,
                        quantity=abs(p["quantity"]),
                        product=p.get("product", "INTRADAY"),
                        order_type="LIMIT",
                        price=self._get_exit_limit_price(ltp, tx_type)
                        if ltp > 0
                        else 0,
                    )
                    if p["tradingsymbol"] in self.active_trades:
                        del self.active_trades[p["tradingsymbol"]]
                    if clean in self.active_trades:
                        del self.active_trades[clean]
            config_manager.save_active_trades(self.active_trades)
        except Exception as e:
            self._push_log(f"Error in square off: {e}")

        # Send daily Telegram session summary
        self._send_eod_summary()

    def _send_eod_summary(self):
        try:
            positions = smart_api_client.get_positions(force=True).get("net", [])
            trades_today = len(positions)
            winning_trades = sum(
                1 for p in positions if p.get("pnl", p.get("m2m", 0)) > 0
            )
            losing_trades = sum(
                1 for p in positions if p.get("pnl", p.get("m2m", 0)) < 0
            )
            win_rate = (
                (winning_trades / trades_today * 100) if trades_today > 0 else 0.0
            )
            realised_pnl = sum(p.get("realised", 0) for p in positions)
            total_pnl = sum(p.get("pnl", p.get("m2m", 0)) for p in positions)

            # Retrieve executed orders to compute broker commissions
            completed_orders = []
            try:
                orders = smart_api_client.get_orders(force=True)
                completed_orders = [
                    o for o in orders if str(o.get("status", "")).upper() == "COMPLETE"
                ]
                executed_orders = len(completed_orders)
            except Exception:
                executed_orders = 0

            # Fallback: if orderbook was empty but positions exist, 2 orders per round-trip trade
            if executed_orders == 0 and trades_today > 0:
                executed_orders = trades_today * 2

            # Query Angel One's live estimateCharges API for exact brokerage, STT, and taxes
            brokerage = round(executed_orders * 20.0, 2)
            total_charges = brokerage
            taxes_and_charges = 0.0

            if completed_orders:
                try:
                    charges_data = smart_api_client.estimate_charges(completed_orders)
                    summary_data = charges_data.get("summary", {})
                    total_api_charges = float(
                        summary_data.get("total_charges", 0.0) or 0.0
                    )
                    if total_api_charges > 0:
                        total_charges = round(total_api_charges, 2)
                        for item in summary_data.get("breakup", []):
                            if "brokerage" in str(item.get("name", "")).lower():
                                brokerage = round(
                                    float(item.get("amount", 0.0) or 0.0), 2
                                )
                        taxes_and_charges = round(
                            max(0.0, total_charges - brokerage), 2
                        )
                except Exception as e:
                    self._push_log(
                        f"Charges estimation fallback to standard tariff: {e}"
                    )

            gross_pnl = round(realised_pnl or total_pnl or risk_manager.daily_pnl, 2)
            net_pnl = round(gross_pnl - total_charges, 2)

            notifier.notify_session_summary(
                {
                    "totalTrades": trades_today,
                    "executedOrders": executed_orders,
                    "winningTrades": winning_trades,
                    "losingTrades": losing_trades,
                    "winRate": round(win_rate, 2),
                    "grossPnl": gross_pnl,
                    "brokerage": brokerage,
                    "totalCharges": total_charges,
                    "taxesAndCharges": taxes_and_charges,
                    "netPnl": net_pnl,
                    "realisedPnl": net_pnl,
                    "totalPnl": round(total_pnl or risk_manager.daily_pnl, 2),
                    "mode": f"Live Trading ({self.mode.capitalize()} Mode)",
                }
            )
            self._push_log("Daily Telegram session summary dispatched")
        except Exception as e:
            self._push_log(f"Failed to dispatch EOD summary: {e}", level="warning")


trading_engine = TradingEngine()
