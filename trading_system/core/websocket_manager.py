"""
SmartWebSocketV2 Client Manager.
Ingests live market data, converts Paise to INR, and feeds the BarAggregator.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Callable, Dict, List, Optional, Set

from loguru import logger
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from ..config.settings import Settings, get_settings


class WebSocketManager:
    """
    Manages connection lifecycle and tick stream processing for Angel One SmartWebSocketV2.
    Normalizes binary/JSON Paise pricing into standard INR floats.
    """

    def __init__(
        self,
        on_tick: Optional[Callable[[str, str, float, float, float], None]] = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.on_tick = on_tick
        self.sws: SmartWebSocketV2 | None = None
        self._thread: threading.Thread | None = None
        self._is_running: bool = False
        self._tokens: Set[str] = set()
        self._token_to_symbol: Dict[str, str] = {}
        self._symbol_to_token: Dict[str, str] = {}

    def register_symbol_mapping(self, token_symbol_pairs: Dict[str, str]):
        """Map instrument tokens to clean trading symbols."""
        for tok, sym in token_symbol_pairs.items():
            tok_str = str(tok).strip()
            clean_sym = sym.replace("-EQ", "").strip().upper()
            self._token_to_symbol[tok_str] = clean_sym
            self._symbol_to_token[clean_sym] = tok_str

    def start(
        self,
        api_key: str,
        jwt_token: str,
        client_code: str,
        feed_token: str,
        initial_tokens: Optional[List[str]] = None,
    ):
        """Start the SmartWebSocketV2 listener thread."""
        if self._is_running:
            logger.warning("WebSocketManager is already active.")
            return

        if self.settings.mode == "paper" and (
            not jwt_token or jwt_token.startswith("SIMULATED")
        ):
            logger.info(
                "WebSocketManager running in paper/simulated mode. Mock feed ready."
            )
            self._is_running = True
            return

        if not jwt_token or not feed_token:
            raise ValueError("Cannot start WebSocket: Missing jwt_token or feed_token.")

        ws_auth = (
            jwt_token if jwt_token.startswith("Bearer ") else f"Bearer {jwt_token}"
        )
        if initial_tokens:
            for t in initial_tokens:
                self._tokens.add(str(t))

        logger.info("Initializing SmartWebSocketV2 connection for %s...", client_code)
        try:
            self.sws = SmartWebSocketV2(
                auth_token=ws_auth,
                api_key=api_key,
                client_code=client_code,
                feed_token=feed_token,
            )
            self.sws.on_open = self._on_open
            self.sws.on_data = self._on_data
            self.sws.on_error = self._on_error
            self.sws.on_close = self._on_close

            self._is_running = True
            self._thread = threading.Thread(
                target=self._run_ws_loop, daemon=True, name="SmartWebSocketThread"
            )
            self._thread.start()
            logger.success("SmartWebSocketV2 client daemon started.")
        except Exception as e:
            self._is_running = False
            logger.error("Failed to initialize SmartWebSocketV2: %s", e)
            raise

    def _run_ws_loop(self):
        """Worker thread loop maintaining the persistent socket connection."""
        while self._is_running:
            try:
                if self.sws:
                    self.sws.connect()
            except Exception as e:
                logger.error("SmartWebSocket disconnected unexpectedly: %s", e)
            if self._is_running:
                logger.info("Reconnecting SmartWebSocketV2 in 3 seconds...")
                time.sleep(3.0)

    def _on_open(self, wsapp):
        logger.success("SmartWebSocketV2 connection established.")
        if self._tokens:
            self.subscribe(list(self._tokens))

    def _on_data(self, wsapp, message):
        """Process incoming binary/JSON tick payload."""
        try:
            data = json.loads(message) if isinstance(message, str) else message
            if not isinstance(data, dict):
                data = getattr(message, "__dict__", {})

            # 1. Price Normalization: SmartAPI sends tick prices in PAISE
            raw_ltp = data.get("last_traded_price")
            if raw_ltp is not None:
                ltp = float(raw_ltp) / 100.0
            else:
                raw_alt = data.get("ltp") or data.get("last_price") or 0.0
                ltp = float(raw_alt)

            if ltp <= 0:
                return

            # Token resolution
            token_raw = (
                data.get("token")
                or data.get("symbol_token")
                or data.get("instrument_token")
            )
            if not token_raw:
                return
            token = str(token_raw).strip()

            symbol = self._token_to_symbol.get(token, f"TOK_{token}")
            day_vol = float(
                data.get("volume_trade_for_the_day") or data.get("volume") or 0.0
            )

            # Timestamp parsing
            now_ts = time.time()
            ex_ts_raw = data.get("exchange_timestamp") or data.get("timestamp")
            if ex_ts_raw and str(ex_ts_raw).isdigit():
                # Timestamp in ms or s
                num_ts = float(ex_ts_raw)
                now_ts = num_ts / 1000.0 if num_ts > 1e11 else num_ts

            if self.on_tick:
                self.on_tick(token, symbol, ltp, day_vol, now_ts)

        except Exception as e:
            logger.debug("Error processing raw tick message: %s", e)

    def _on_error(self, wsapp, error):
        logger.error("SmartWebSocketV2 Error: %s", error)

    def _on_close(self, wsapp):
        logger.warning("SmartWebSocketV2 connection closed.")

    def subscribe(self, tokens: List[str]):
        """Subscribe scrips in Mode 2 (QUOTE)."""
        clean_tokens = [str(t).strip() for t in tokens if t]
        for t in clean_tokens:
            self._tokens.add(t)

        if self.sws and self._is_running and clean_tokens:
            try:
                token_list = [{"exchangeType": 1, "tokens": clean_tokens}]  # 1 = NSE_CM
                self.sws.subscribe("agent_sub", 2, token_list)  # Mode 2 = QUOTE
                logger.info(
                    "Subscribed %d instruments on SmartWebSocketV2 (Mode 2)",
                    len(clean_tokens),
                )
            except Exception as e:
                logger.error("Error subscribing scrips: %s", e)

    def unsubscribe(self, tokens: List[str]):
        """Unsubscribe scrips."""
        clean_tokens = [str(t).strip() for t in tokens if t]
        for t in clean_tokens:
            self._tokens.discard(t)

        if self.sws and self._is_running and clean_tokens:
            try:
                token_list = [{"exchangeType": 1, "tokens": clean_tokens}]
                self.sws.unsubscribe("agent_unsub", 2, token_list)
            except Exception as e:
                logger.error("Error unsubscribing scrips: %s", e)

    def stop(self):
        """Close socket connection and terminate worker thread."""
        self._is_running = False
        if self.sws:
            try:
                self.sws.close_connection()
            except Exception:
                pass
        logger.info("SmartWebSocketManager stopped.")
