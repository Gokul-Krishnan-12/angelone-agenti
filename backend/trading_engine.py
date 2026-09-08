import datetime
import json
import sys
import threading
import time
import uuid

from .config import config_manager
from .notifier import notifier
from .risk_manager import risk_manager
from .scanner import scanner
from .smartapi_client import smart_api_client
from .utils import DateTimeEncoder


class TradingEngine:
    def __init__(self):
        self.running = False
        self.thread = None
        self.mode = "confirm"  # auto or confirm
        self.interval = 60  # seconds
        self.active_trades = {}  # tradingsymbol -> { sl, target, direction, entry_price, entry_time, original_strategy }
        self._instrument_map = {}  # cached symbol -> instrument_token map
        self._last_eod_summary_date = None
        self.dynamic_watchlist = []
        self.screener_interval = 3600  # 1 hour periodic dynamic re-screening
        self._last_screener_time = 0.0
        self._last_screener_date = None

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
        event = {
            "event": "log:entry",
            "data": {
                "id": str(uuid.uuid4()),
                "level": level,
                "message": message,
                "timestamp": datetime.datetime.now().isoformat(),
            },
        }
        print(json.dumps(event, cls=DateTimeEncoder))
        sys.stdout.flush()

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
                # 1. Fast polling: Monitor live positions for Stop-Loss / Target
                self.monitor_positions()

                # 2. Check End of Day square off
                if risk_manager.should_square_off():
                    self.square_off_all()
                    self.stop()
                    break

                # Check EOD session summary (triggered around squareOffTime)
                now_dt = datetime.datetime.now()
                today_str = now_dt.strftime("%Y-%m-%d")
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

        # Hourly Dynamic Screener: re-screen every 1 hour (or on new day) for top 35 in-play stocks
        now_ts = time.time()
        today_date = datetime.date.today()
        screener_due = (
            not getattr(self, "dynamic_watchlist", None)
            or getattr(self, "_last_screener_date", None) != today_date
            or (now_ts - getattr(self, "_last_screener_time", 0.0))
            >= getattr(self, "screener_interval", 3600)
        )

        if screener_due:
            from .fno_universe import get_fno_universe
            from .screener import screener_engine

            custom_watchlist = config_manager.get_watchlist()
            full_universe = list(set(get_fno_universe() + custom_watchlist))

            self._push_log(
                f"Running dynamic momentum, RVOL & institutional participation screener across {len(full_universe)} F&O stocks..."
            )
            screened_stocks = screener_engine.generate_daily_watchlist(
                universe=full_universe, limit=35
            )

            # Preserve any currently open active trades so position monitoring and trailing exits are never lost
            combined_watchlist = list(screened_stocks)
            for sym in self.active_trades:
                if sym not in combined_watchlist:
                    combined_watchlist.append(sym)

            self.dynamic_watchlist = combined_watchlist
            self._last_screener_time = now_ts
            self._last_screener_date = today_date

            self._push_log(
                f"Dynamic Watchlist updated: Top {len(self.dynamic_watchlist)} in-play stocks selected "
                f"(hourly re-screen): {', '.join(self.dynamic_watchlist[:10])}..."
            )

        def handle_new_signal(signal):
            if signal["confidence"] >= 70:
                self._push_signal(signal)
                confluence_score = signal.get("confluenceScore", 0)

                if self.mode == "confirm":
                    if signal["confidence"] >= 80 and confluence_score >= 2:
                        notifier.notify_signal_approval(signal)
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
        scanner.scan_watchlist(self.dynamic_watchlist, on_signal=handle_new_signal)

        # Re-evaluate open positions for thesis invalidation
        if self.active_trades:
            self._reevaluate_positions()

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

        transaction_type = "BUY" if direction == "BUY" else "SELL"

        try:
            order_id = smart_api_client.place_order(
                variety="NORMAL",
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=qty,
                product="INTRADAY",
                order_type="LIMIT",
                price=entry_price,
            )
            self._push_log(
                f"Executed {transaction_type} for {tradingsymbol}, qty {qty}, order_id {order_id}"
            )
            self.active_trades[tradingsymbol] = {
                "sl": stop_loss,
                "target": target,
                "direction": direction,
                "entry_price": entry_price,
                "entry_time": datetime.datetime.now(),
                "original_strategy": signal.get("strategy", "unknown"),
                # ATR trailing SL support — seeded from signal indicators if present
                "atr": signal.get("indicators", {}).get("atr", 0.0),
                "high_water_mark": entry_price,  # for BUY
                "low_water_mark": entry_price,  # for SELL
            }
            return True
        except Exception as e:
            self._push_log(f"Failed to execute signal: {e}")
            return False

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

            # Clean up active_trades if position was closed manually via Angel One App
            symbols_to_remove = []
            for symbol in self.active_trades.keys():
                clean_sym = symbol.replace("-EQ", "")
                if symbol not in open_symbols and clean_sym not in open_symbols:
                    symbols_to_remove.append(symbol)
            for symbol in symbols_to_remove:
                self._push_log(
                    f"Detected manual closure for {symbol}. Removing from tracking."
                )
                del self.active_trades[symbol]

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
                                "target": target,
                                "direction": direction,
                                "entry_price": avg_price,
                                "entry_time": datetime.datetime.now(),
                                "original_strategy": "adopted",
                            }
                            self._push_log(
                                f"Adopted open position {symbol} ({direction}) at ₹{avg_price}. Auto-calculated SL: ₹{sl}, Target: ₹{target}"
                            )

                    if active_key in self.active_trades:
                        trade = self.active_trades[active_key]
                        ltp = p.get("lastPrice", 0)
                        if ltp == 0:
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
                            reason = "Stop Loss" if hit_sl else "Target"
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
                                    risk_config.get("trailingSlAtrMultiplier", 1.5)
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
                                    self._push_log(
                                        f"Trailing SL ratcheted for {symbol}: "
                                        f"₹{old_sl:.2f} → ₹{new_sl:.2f} "
                                        f"(ATR {atr:.2f} × {tsl_mult})"
                                    )
        except Exception as e:
            self._push_log(f"Error monitoring positions: {e}")

    def _reevaluate_positions(self):
        """Re-evaluate open positions against current strategy signals (thesis invalidation)."""
        if not self.active_trades:
            return

        risk_config = config_manager.get_risk_config()
        weak_exit_mins = risk_config.get("positionRevalWeakExitMins", 15)
        breakeven_mins = risk_config.get("positionRevalBreakevenMins", 45)
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

            # Rule 3: Time decay — tighten to breakeven
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
        """Move the stop-loss to the entry price (breakeven)."""
        if symbol in self.active_trades:
            entry_price = self.active_trades[symbol].get("entry_price", 0)
            if entry_price > 0:
                self.active_trades[symbol]["sl"] = entry_price

    def _exit_position(self, position: dict, symbol: str, reason: str):
        """Exit a position due to thesis invalidation."""
        try:
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
                    clean = p["tradingsymbol"].replace("-EQ", "")
                    if p["tradingsymbol"] in self.active_trades:
                        del self.active_trades[p["tradingsymbol"]]
                    if clean in self.active_trades:
                        del self.active_trades[clean]
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

            notifier.notify_session_summary(
                {
                    "totalTrades": trades_today,
                    "winningTrades": winning_trades,
                    "losingTrades": losing_trades,
                    "winRate": round(win_rate, 2),
                    "realisedPnl": round(
                        realised_pnl or total_pnl or risk_manager.daily_pnl, 2
                    ),
                    "totalPnl": round(total_pnl or risk_manager.daily_pnl, 2),
                    "mode": f"Live Trading ({self.mode.capitalize()} Mode)",
                }
            )
            self._push_log("Daily Telegram session summary dispatched")
        except Exception as e:
            self._push_log(f"Failed to dispatch EOD summary: {e}", level="warning")


trading_engine = TradingEngine()
