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

    def status(self) -> dict:
        return {"running": self.running, "tokens": list(self.tokens)}

    def subscribe(self, tokens: list):
        from .smartapi_client import smart_api_client

        added_tokens = []
        for item in tokens:
            if not item:
                continue
            item_str = str(item).strip()
            # If not pure numeric, resolve trading symbol to instrument token
            if not item_str.isdigit():
                tok = smart_api_client.resolve_token(item_str)
                if tok:
                    tok_str = str(tok)
                    clean_sym = item_str.replace("NSE:", "").replace("-EQ", "").upper()
                    smart_api_client.symbol_map[tok_str] = clean_sym
                    self.tokens.add(tok_str)
                    added_tokens.append(tok_str)
            else:
                self.tokens.add(item_str)
                added_tokens.append(item_str)

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
        from .smartapi_client import smart_api_client

        str_tokens = []
        for item in tokens:
            if not item:
                continue
            item_str = str(item).strip()
            if not item_str.isdigit():
                tok = smart_api_client.resolve_token(item_str)
                if tok:
                    str_tokens.append(str(tok))
            else:
                str_tokens.append(item_str)

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
            # SmartWebSocketV2 sends price fields in PAISE (1 INR = 100 paise)
            raw_ltp = data.get("last_traded_price")
            if raw_ltp is not None:
                ltp = float(raw_ltp) / 100.0
            else:
                ltp = float(data.get("ltp") or data.get("last_price") or 0.0)

            # Also extract OHLC if available (SmartWebSocketV2 sends these in paise)
            raw_open = data.get("open_price_of_the_day")
            raw_high = data.get("high_price_of_the_day")
            raw_low = data.get("low_price_of_the_day")
            raw_close = data.get("closed_price")

            ohlc_open = (
                float(raw_open) / 100.0
                if raw_open is not None
                else float(data.get("open") or 0.0)
            )
            ohlc_high = (
                float(raw_high) / 100.0
                if raw_high is not None
                else float(data.get("high") or 0.0)
            )
            ohlc_low = (
                float(raw_low) / 100.0
                if raw_low is not None
                else float(data.get("low") or 0.0)
            )
            ohlc_close = (
                float(raw_close) / 100.0
                if raw_close is not None
                else float(data.get("close") or 0.0)
            )

            token = (
                data.get("token")
                or data.get("symbol_token")
                or data.get("instrument_token")
            )
            token_str = str(token) if token is not None else None

            # Look up trading symbol from token
            tradingsymbol = ""
            if token_str:
                from .smartapi_client import smart_api_client

                mapped = smart_api_client.symbol_map.get(token_str)
                if mapped:
                    tradingsymbol = mapped.replace("-EQ", "").upper()

            if not tradingsymbol:
                raw_sym = data.get("tradingsymbol") or data.get("symbol") or ""
                tradingsymbol = (
                    str(raw_sym).replace("-EQ", "").replace("NSE:", "").upper()
                )

            price_val = float(ltp)
            event = {
                "event": "ticker:tick",
                "data": {
                    "instrument_token": token_str,
                    "tradingsymbol": tradingsymbol,
                    "symbol": tradingsymbol,
                    "last_price": price_val,
                    "lastPrice": price_val,
                    "ltp": price_val,
                    "ohlc": {
                        "open": ohlc_open,
                        "high": ohlc_high,
                        "low": ohlc_low,
                        "close": ohlc_close,
                    },
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
