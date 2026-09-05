import json
import logging
import sys
import threading

from .utils import DateTimeEncoder

logger = logging.getLogger(__name__)


class TickerManager:
    def __init__(self):
        self.sws = None
        self.thread = None
        self.tokens = set()
        self.running = False
        self.api_key = ""
        self.auth_token = ""
        self.client_code = ""
        self.feed_token = ""

    def start(
        self,
        api_key: str,
        auth_token: str,
        client_code: str = "",
        feed_token: str = "",
    ):
        if self.running:
            return

        from .config import config_manager
        from .smartapi_client import smart_api_client

        self.api_key = api_key or smart_api_client.api_key
        self.auth_token = auth_token or smart_api_client.jwt_token
        self.client_code = (
            client_code
            or smart_api_client.client_code
            or config_manager.get_credentials().get("clientCode", "")
        )
        self.feed_token = (
            feed_token
            or smart_api_client.feed_token
            or config_manager.get_credentials().get("feedToken", "")
        )

        if not self.auth_token or not self.feed_token:
            logger.info("Ticker skipped: Missing auth_token or feed_token")
            return

        try:
            from SmartApi.smartWebSocketV2 import SmartWebSocketV2

            ws_token = (
                self.auth_token
                if self.auth_token.startswith("Bearer ")
                else f"Bearer {self.auth_token}"
            )
            self.sws = SmartWebSocketV2(
                ws_token, self.api_key, self.client_code, self.feed_token
            )
            self.sws.on_open = self._on_open
            self.sws.on_data = self._on_data
            self.sws.on_error = self._on_error
            self.sws.on_close = self._on_close

            self.running = True
            self.thread = threading.Thread(target=self._run_ws, daemon=True)
            self.thread.start()
            logger.info("SmartWebSocketV2 thread started")
        except Exception as e:
            logger.error("Failed to initialize SmartWebSocketV2: %s", e)
            self.running = False

    def _run_ws(self):
        try:
            if self.sws:
                self.sws.connect()
        except Exception as e:
            logger.error("SmartWebSocket connection error: %s", e)
        finally:
            self.running = False

    def stop(self):
        if self.sws and self.running:
            self.running = False
            try:
                self.sws.close_connection()
            except Exception:
                pass

    def subscribe(self, tokens: list):
        for token in tokens:
            self.tokens.add(str(token))
        if self.sws and self.running and self.tokens:
            try:
                token_list = [
                    {
                        "exchangeType": 1,  # NSE_CM
                        "tokens": list(self.tokens),
                    }
                ]
                self.sws.subscribe("agent_sub", 2, token_list)  # Mode 2: QUOTE
            except Exception as e:
                logger.error("Error subscribing tokens: %s", e)

    def unsubscribe(self, tokens: list):
        str_tokens = [str(t) for t in tokens]
        for token in str_tokens:
            if token in self.tokens:
                self.tokens.remove(token)
        if self.sws and self.running and str_tokens:
            try:
                token_list = [{"exchangeType": 1, "tokens": str_tokens}]
                self.sws.unsubscribe("agent_unsub", 2, token_list)
            except Exception as e:
                logger.error("Error unsubscribing tokens: %s", e)

    def _on_open(self, wsapp):
        logger.info("SmartWebSocketV2 connected successfully")
        if self.tokens:
            self.subscribe(list(self.tokens))

    def _on_data(self, wsapp, message):
        try:
            if isinstance(message, str):
                try:
                    data = json.loads(message)
                except Exception:
                    data = {"raw": message}
            elif isinstance(message, dict):
                data = message
            else:
                data = getattr(message, "__dict__", {})

            # Extract price fields
            ltp = data.get("last_traded_price") or data.get("ltp") or 0.0
            # If price is provided in paise (common in exchange binary/raw ticks > 100x), scale
            if isinstance(ltp, (int, float)) and ltp > 1000000:
                ltp = ltp / 100.0

            token = (
                data.get("token")
                or data.get("symbol_token")
                or data.get("instrument_token")
            )

            event = {
                "event": "tick",
                "data": {
                    "instrument_token": str(token) if token else None,
                    "last_price": float(ltp),
                    "volume": float(
                        data.get("volume_trade_for_the_day")
                        or data.get("volume")
                        or 0.0
                    ),
                    "buy_quantity": int(
                        data.get("total_buy_quantity") or data.get("buy_quantity") or 0
                    ),
                    "sell_quantity": int(
                        data.get("total_sell_quantity")
                        or data.get("sell_quantity")
                        or 0
                    ),
                    "timestamp": str(
                        data.get("exchange_timestamp") or data.get("timestamp") or ""
                    ),
                },
            }
            print(json.dumps(event, cls=DateTimeEncoder))
            sys.stdout.flush()
        except Exception as e:
            logger.debug("Error processing tick message: %s", e)

    def _on_error(self, wsapp, error):
        print(f"Ticker Error: {error}", file=sys.stderr)

    def _on_close(self, wsapp):
        logger.info("SmartWebSocket connection closed")
        self.running = False


ticker_manager = TickerManager()
