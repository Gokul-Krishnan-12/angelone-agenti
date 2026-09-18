import json
import logging
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

import pyotp
import requests
import SmartApi.smartConnect
from requests.adapters import HTTPAdapter
from SmartApi import SmartConnect
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def _create_pooled_http_session(
    pool_size: int = 50, max_retries: int = 3
) -> requests.Session:
    """Create a persistent requests.Session with HTTP Keep-Alive, TCP socket reuse, and retries."""
    session = requests.Session()
    retries = Retry(
        total=max_retries,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        pool_connections=25,
        pool_maxsize=pool_size,
        max_retries=retries,
        pool_block=False,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# Bundled fallback tokens for NIFTY 50 and major NSE equities
# Used when offline or while downloading the full OpenAPI scrip master
BUNDLED_NSE_TOKENS: Dict[str, str] = {
    "RELIANCE": "2885",
    "TCS": "11536",
    "HDFCBANK": "1333",
    "INFY": "1594",
    "ICICIBANK": "4963",
    "HINDUNILVR": "1394",
    "ITC": "1660",
    "SBIN": "3045",
    "BHARTIARTL": "10604",
    "KOTAKBANK": "1922",
    "LT": "11483",
    "AXISBANK": "5900",
    "ASIANPAINT": "236",
    "MARUTI": "10999",
    "TITAN": "3506",
    "SUNPHARMA": "3351",
    "BAJFINANCE": "317",
    "WIPRO": "3787",
    "ULTRACEMCO": "11532",
    "NESTLEIND": "17963",
    "ADANIENT": "25",
    "ADANIPORTS": "15083",
    "APOLLOHOSP": "157",
    "BAJAJ-AUTO": "16669",
    "BAJAJFINSV": "16675",
    "BEL": "383",
    "CIPLA": "694",
    "COALINDIA": "20374",
    "DRREDDY": "881",
    "EICHERMOT": "910",
    "GRASIM": "1232",
    "HCLTECH": "7229",
    "HINDALCO": "1363",
    "HDFCLIFE": "467",
    "INDIGO": "11195",
    "JIOFIN": "19487",
    "JSWSTEEL": "11723",
    "M&M": "2031",
    "NTPC": "11630",
    "ONGC": "2475",
    "POWERGRID": "14977",
    "SBILIFE": "21808",
    "SHRIRAMFIN": "4306",
    "TATACONSUM": "3432",
    "TATASTEEL": "3499",
    "TECHM": "13538",
    "TRENT": "1964",
    "MAXHEALTH": "2142",
    "TMPV": "3456",
    "ETERNAL": "547",
}

INTERVAL_MAP: Dict[str, str] = {
    "minute": "ONE_MINUTE",
    "1minute": "ONE_MINUTE",
    "3minute": "THREE_MINUTE",
    "5minute": "FIVE_MINUTE",
    "10minute": "TEN_MINUTE",
    "15minute": "FIFTEEN_MINUTE",
    "30minute": "THIRTY_MINUTE",
    "60minute": "ONE_HOUR",
    "hour": "ONE_HOUR",
    "day": "ONE_DAY",
    "ONE_MINUTE": "ONE_MINUTE",
    "THREE_MINUTE": "THREE_MINUTE",
    "FIVE_MINUTE": "FIVE_MINUTE",
    "TEN_MINUTE": "TEN_MINUTE",
    "FIFTEEN_MINUTE": "FIFTEEN_MINUTE",
    "THIRTY_MINUTE": "THIRTY_MINUTE",
    "ONE_HOUR": "ONE_HOUR",
    "ONE_DAY": "ONE_DAY",
}


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def convert_keys(obj: Any) -> Any:
    if isinstance(obj, list):
        return [convert_keys(i) for i in obj]
    elif isinstance(obj, dict):
        return {to_camel(k): convert_keys(v) for k, v in obj.items()}
    else:
        return obj


class SmartApiClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SmartApiClient, cls).__new__(cls)
            cls._instance.http_session = _create_pooled_http_session()
            cls._instance.smart_api = None
            cls._instance.api_key = ""
            cls._instance.client_code = ""
            cls._instance.jwt_token = ""
            cls._instance.refresh_token = ""
            cls._instance.feed_token = ""
            cls._instance.user_profile = {}
            cls._instance.instruments_cache = None
            cls._instance.token_map = {}
            cls._instance.symbol_map = {}
            cls._instance._cache = {}
            cls._instance._cache_ttl = 3.5
            cls._instance._charges_cache = {}
            cls._instance._last_candle_fetch_time = 0.0
            cls._instance._candle_lock = threading.Lock()
            cls._instance._last_api_request_time = 0.0
            cls._instance._api_lock = threading.Lock()
            cls._instance._init_token_maps()
        return cls._instance

    def _get_cached(self, key: str) -> Any:
        """Return cached result if within TTL, else None."""
        entry = getattr(self, "_cache", {}).get(key)
        if entry and (time.time() - entry["time"] < getattr(self, "_cache_ttl", 3.5)):
            return entry["data"]
        return None

    def _set_cached(self, key: str, data: Any):
        """Set cached result with current timestamp."""
        if not hasattr(self, "_cache"):
            self._cache = {}
        self._cache[key] = {"data": data, "time": time.time()}

    def clear_cache(self, key: str = ""):
        if not hasattr(self, "_cache"):
            self._cache = {}
            return
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    def _init_token_maps(self):
        """Pre-populate token and symbol maps with bundled symbols."""
        for sym, tok in BUNDLED_NSE_TOKENS.items():
            self.token_map[sym] = tok
            self.token_map[f"{sym}-EQ"] = tok
            self.symbol_map[sym] = f"{sym}-EQ"
            self.symbol_map[tok] = f"{sym}-EQ"

    def init(self, api_key: str, client_code: str = "", timeout: int = 20):
        self.api_key = api_key
        self.client_code = client_code
        if not hasattr(self, "http_session") or self.http_session is None:
            self.http_session = _create_pooled_http_session()
        SmartApi.smartConnect.requests.request = self.http_session.request
        self.smart_api = SmartConnect(api_key=api_key, timeout=timeout)
        self.smart_api.timeout = timeout

    def set_session_tokens(
        self,
        jwt_token: str,
        refresh_token: str = "",
        feed_token: str = "",
        client_code: str = "",
    ):
        clean_jwt = (
            (jwt_token or "").replace("Bearer ", "").replace("bearer ", "").strip()
        )
        self.jwt_token = clean_jwt
        self.refresh_token = refresh_token
        self.feed_token = feed_token
        if client_code:
            self.client_code = client_code

        if self.smart_api:
            self.smart_api.access_token = clean_jwt
            self.smart_api.refresh_token = refresh_token
            self.smart_api.feed_token = feed_token
            try:
                self.smart_api.setAccessToken(clean_jwt)
            except Exception:
                pass
            try:
                self.smart_api.setRefreshToken(refresh_token)
            except Exception:
                pass
            try:
                self.smart_api.setFeedToken(feed_token)
            except Exception:
                pass

    def generate_totp(self, totp_secret_or_code: str) -> str:
        """Generate a 6-digit TOTP code if secret provided, or clean manual code."""
        code_or_secret = (totp_secret_or_code or "").strip().replace(" ", "")
        if not code_or_secret:
            return ""
        if code_or_secret.isdigit() and len(code_or_secret) == 6:
            return code_or_secret
        try:
            return pyotp.TOTP(code_or_secret).now()
        except Exception as e:
            logger.warning("Failed to generate TOTP from secret: %s", e)
            return code_or_secret

    def login(
        self,
        api_key: str,
        client_code: str,
        pin: str,
        totp_secret_or_code: str,
    ) -> Dict[str, Any]:
        """Direct, headless login to Angel One SmartAPI."""
        self.init(api_key, client_code)
        totp = self.generate_totp(totp_secret_or_code)
        if not totp:
            raise ValueError("Invalid TOTP or TOTP Secret Key")

        session_res = self.smart_api.generateSession(client_code, pin, totp)
        if not session_res:
            raise RuntimeError("Empty response received from SmartAPI login")

        if not session_res.get("status"):
            error_msg = session_res.get("message") or session_res.get(
                "errorcode", "Authentication failed"
            )
            raise RuntimeError(f"SmartAPI login failed: {error_msg}")

        data = session_res.get("data", {})
        raw_jwt = data.get("jwtToken", "")
        clean_jwt = (
            (raw_jwt or "").replace("Bearer ", "").replace("bearer ", "").strip()
        )
        refresh_token = data.get("refreshToken", "")
        feed_token = data.get("feedToken", "")

        self.set_session_tokens(clean_jwt, refresh_token, feed_token, client_code)

        # Retrieve user profile if available
        user_name = client_code
        try:
            profile_res = self.smart_api.getProfile(refresh_token)
            if profile_res and profile_res.get("status") and profile_res.get("data"):
                self.user_profile = profile_res["data"]
                user_name = self.user_profile.get("name") or client_code
        except Exception as e:
            logger.debug("Could not fetch profile details: %s", e)

        return {
            "is_valid": True,
            "user_id": client_code,
            "user_name": user_name,
            "jwt_token": clean_jwt,
            "access_token": clean_jwt,  # compatibility alias
            "refresh_token": refresh_token,
            "feed_token": feed_token,
        }

    def renew_access_token(self) -> bool:
        """Renew JWT token using the refresh token."""
        if not self.smart_api or not self.refresh_token:
            return False
        try:
            self.smart_api.access_token = self.jwt_token
            self.smart_api.refresh_token = self.refresh_token
            res = self.smart_api.renewAccessToken()
            if res and isinstance(res, dict):
                data = res.get("data") if isinstance(res.get("data"), dict) else res
                new_jwt = data.get("jwtToken")
                if new_jwt:
                    clean_jwt = (
                        new_jwt.replace("Bearer ", "").replace("bearer ", "").strip()
                    )
                    self.jwt_token = clean_jwt
                    self.smart_api.setAccessToken(clean_jwt)
                    new_refresh = data.get("refreshToken")
                    if new_refresh:
                        self.refresh_token = new_refresh
                        self.smart_api.setRefreshToken(new_refresh)
                    return True
        except Exception as e:
            logger.warning("Error renewing SmartAPI access token: %s", e)
        return False

    def reauthenticate(self) -> bool:
        """Attempt token renewal or headless re-login using saved encrypted credentials."""
        # 1. Try renew_access_token first
        if self.renew_access_token():
            logger.info("Successfully renewed SmartAPI session token via refresh token")
            return True

        # 2. Fall back to headless login using encrypted credentials
        try:
            from .config import config_manager

            creds = config_manager.get_credentials()
            api_key = creds.get("apiKey") or self.api_key
            client_code = creds.get("clientCode") or self.client_code
            pin = creds.get("pin")
            totp_secret = creds.get("totpSecret")

            if api_key and client_code and pin and totp_secret:
                logger.info("Re-authenticating headlessly with SmartAPI via TOTP...")
                res = self.login(api_key, client_code, pin, totp_secret)
                if res and res.get("is_valid"):
                    config_manager.save_credentials(
                        api_key=api_key,
                        client_code=client_code,
                        pin=pin,
                        totp_secret=totp_secret,
                        jwt_token=res.get("jwt_token", ""),
                        refresh_token=res.get("refresh_token", ""),
                        feed_token=res.get("feed_token", ""),
                    )
                    logger.info("Headless re-authentication successful.")
                    return True
        except Exception as e:
            logger.error("Failed to re-authenticate with SmartAPI: %s", e)
        return False

    def _execute_with_auth_retry(self, api_func, *args, **kwargs):
        """Execute an API function with automatic token refresh on auth failure and network resilience."""
        auth_keywords = (
            "token",
            "unauthorized",
            "ag8001",
            "ag8002",
            "ag8003",
            "ab1004",
            "session",
            "expired",
            "invalid",
        )
        network_keywords = (
            "remotedisconnected",
            "connection aborted",
            "connection reset",
            "connection refused",
            "read timed out",
            "readtimeout",
            "connecttimeout",
            "broken pipe",
        )

        rate_limit_keywords = (
            "exceeding access rate",
            "access rate",
            "rate limit",
            "too many requests",
            "429",
            "access denied because of exceeding",
        )

        max_network_retries = 3
        for attempt in range(max_network_retries):
            try:
                # Global account-wide request pacer (<= 2.85 req/sec) to eliminate burst 429 rate limit violations
                api_lock = getattr(self, "_api_lock", None)
                if api_lock is not None:
                    with api_lock:
                        now = time.time()
                        elapsed = now - getattr(self, "_last_api_request_time", 0.0)
                        if elapsed < 0.35:
                            time.sleep(0.35 - elapsed)
                        self._last_api_request_time = time.time()

                res = api_func(*args, **kwargs)
                if isinstance(res, dict) and (
                    not res.get("status") or res.get("success") is False
                ):
                    err_code = str(
                        res.get("errorcode") or res.get("errorCode") or ""
                    ).upper()
                    err_msg = str(res.get("message", "")).lower()
                    combined = f"{err_code} {err_msg}"
                    if any(k in combined for k in auth_keywords):
                        if self.reauthenticate():
                            return api_func(*args, **kwargs)
                    if any(k in combined for k in rate_limit_keywords):
                        if attempt < max_network_retries - 1:
                            backoff = 1.5 * (attempt + 1)
                            logger.warning(
                                "SmartAPI rate limit hit (%s). Backing off for %.1fs (attempt %d/%d)...",
                                combined,
                                backoff,
                                attempt + 1,
                                max_network_retries,
                            )
                            time.sleep(backoff)
                            continue
                return res
            except Exception as e:
                err_str = str(e).lower()
                # 1. Check for auth failure
                if any(k in err_str for k in auth_keywords):
                    if self.reauthenticate():
                        return api_func(*args, **kwargs)
                    raise
                # 2. Check for rate limiting (HTTP 429 / exceeding access rate)
                if any(k in err_str for k in rate_limit_keywords):
                    if attempt < max_network_retries - 1:
                        backoff = 1.5 * (attempt + 1)
                        logger.warning(
                            "SmartAPI rate limit hit (%s). Backing off for %.1fs (attempt %d/%d)...",
                            e,
                            backoff,
                            attempt + 1,
                            max_network_retries,
                        )
                        time.sleep(backoff)
                        continue
                # 3. Check for transient network disconnection or read timeout
                if any(k in err_str for k in network_keywords):
                    if attempt < max_network_retries - 1:
                        backoff = 1.0 * (attempt + 1)
                        logger.warning(
                            "SmartAPI network glitch (%s). Retrying call in %.1fs (attempt %d/%d)...",
                            e,
                            backoff,
                            attempt + 1,
                            max_network_retries,
                        )
                        time.sleep(backoff)
                        continue
                raise

    def get_positions(self, force: bool = False) -> Dict[str, Any]:
        """Fetch open & day positions and normalize into {'net': [...], 'day': [...]}."""
        if not force:
            cached = self._get_cached("positions")
            if cached is not None:
                return cached

        if not self.smart_api:
            return {"net": [], "day": []}

        try:
            res = self._execute_with_auth_retry(self.smart_api.position)
            if (
                not res
                or not res.get("status")
                or not isinstance(res.get("data"), list)
            ):
                return {"net": [], "day": []}

            positions_data = res["data"]
            net_positions = []
            for p in positions_data:
                qty = int(p.get("netqty", 0))
                avg_price = float(
                    p.get("netavgprice")
                    or p.get("buyavgprice")
                    or p.get("sellavgprice")
                    or 0.0
                )
                ltp = float(p.get("ltp", 0.0))
                pnl = float(p.get("pnl", 0.0))
                prod = p.get("producttype", "INTRADAY")
                # Map INTRADAY to MIS for frontend compatibility
                mapped_product = "MIS" if prod in ("INTRADAY", "MIS") else prod

                symbol = p.get("tradingsymbol", "")
                clean_symbol = symbol.replace("-EQ", "")

                net_positions.append(
                    {
                        "tradingsymbol": symbol,
                        "symbol": clean_symbol,
                        "exchange": p.get("exchange", "NSE"),
                        "instrumentToken": p.get("symboltoken", ""),
                        "product": mapped_product,
                        "quantity": qty,
                        "overnightQuantity": int(p.get("cfbuyqty", 0))
                        - int(p.get("cfsellqty", 0)),
                        "averagePrice": avg_price,
                        "lastPrice": ltp,
                        "closePrice": float(p.get("close", 0.0) or ltp),
                        "pnl": pnl,
                        "realised": float(p.get("realisedpnl") or p.get("rpnl") or 0.0),
                        "unrealised": float(
                            p.get("unrealisedpnl") or p.get("upnl") or 0.0
                        ),
                        "buyQuantity": int(p.get("buyqty", 0)),
                        "sellQuantity": int(p.get("sellqty", 0)),
                        "buyPrice": float(p.get("buyavgprice", 0.0)),
                        "sellPrice": float(p.get("sellavgprice", 0.0)),
                        "multiplier": float(p.get("multiplier", 1.0)),
                        "value": float(p.get("netvalue", 0.0)),
                        "dayBuyQuantity": int(p.get("buyqty", 0)),
                        "daySellQuantity": int(p.get("sellqty", 0)),
                    }
                )

            # Enrich open positions with live real-time LTP
            open_symbols = [
                p["tradingsymbol"] for p in net_positions if p["quantity"] != 0
            ]
            if open_symbols:
                try:
                    live_ltps = self.get_ltp(open_symbols)
                    for p in net_positions:
                        if p["quantity"] != 0:
                            sym = p["tradingsymbol"]
                            clean = p["symbol"]
                            ltp_info = live_ltps.get(sym) or live_ltps.get(clean)
                            if ltp_info and ltp_info.get("lastPrice", 0) > 0:
                                live_ltp = float(ltp_info["lastPrice"])
                                p["lastPrice"] = live_ltp
                                avg = p["averagePrice"]
                                qty = p["quantity"]
                                unrealised = (
                                    (live_ltp - avg) * qty
                                    if qty > 0
                                    else (avg - live_ltp) * abs(qty)
                                )
                                p["unrealised"] = round(unrealised, 2)
                                p["pnl"] = round(p["realised"] + p["unrealised"], 2)
                except Exception as e:
                    logger.debug("Failed to enrich open positions with live LTP: %s", e)

            result = convert_keys({"net": net_positions, "day": net_positions})
            self._set_cached("positions", result)
            return result
        except Exception as e:
            logger.error("Error getting positions: %s", e)
            return {"net": [], "day": []}

    def get_orders(self, force: bool = False) -> List[Dict[str, Any]]:
        """Fetch orders, merge with tracked orders, and normalize."""
        from .config import config_manager

        if not force:
            cached = self._get_cached("orders")
            if cached is not None:
                return cached

        if not self.smart_api:
            return []

        try:
            res = self._execute_with_auth_retry(self.smart_api.orderBook)
            orders_raw = res.get("data", []) if (res and res.get("status")) else []
        except Exception as e:
            logger.error("Error fetching orderBook: %s", e)
            orders_raw = []

        app_orders = config_manager.get_app_order_ids()
        historical = config_manager.get_historical_orders()

        orders_changed = False
        for o in orders_raw:
            o_id = str(o.get("orderid", ""))
            if o_id:
                if o_id not in historical or historical[o_id] != o:
                    historical[o_id] = o
                    orders_changed = True

        if orders_changed:
            config_manager.save_historical_orders(historical)
        all_raw = list(historical.values())

        normalized_orders = []
        for o in all_raw:
            o_id = str(o.get("orderid") or o.get("order_id") or "")
            prod = o.get("producttype", "INTRADAY")
            mapped_product = "MIS" if prod in ("INTRADAY", "MIS") else prod

            ts = str(
                o.get("updatetime")
                or o.get("ordertime")
                or o.get("order_timestamp")
                or ""
            )

            status = str(o.get("orderstatus") or o.get("status") or "PENDING").upper()
            if status in ("COMPLETE", "COMPLETED"):
                status = "COMPLETE"
            elif status in ("CANCELLED", "CANCELED"):
                status = "CANCELLED"
            elif status in ("REJECTED",):
                status = "REJECTED"

            normalized_orders.append(
                {
                    "orderId": o_id,
                    "isAppOrder": o_id in app_orders,
                    "tradingsymbol": o.get("tradingsymbol", ""),
                    "exchange": o.get("exchange", "NSE"),
                    "transactionType": o.get("transactiontype", "BUY").upper(),
                    "quantity": int(o.get("quantity", 0)),
                    "filledQuantity": int(
                        o.get("filledshares") or o.get("filled_quantity") or 0
                    ),
                    "pendingQuantity": int(
                        o.get("unfilledshares") or o.get("pending_quantity") or 0
                    ),
                    "price": float(o.get("price", 0.0)),
                    "averagePrice": float(
                        o.get("averageprice") or o.get("average_price") or 0.0
                    ),
                    "triggerPrice": float(
                        o.get("triggerprice") or o.get("trigger_price") or 0.0
                    ),
                    "product": mapped_product,
                    "orderType": o.get("ordertype") or o.get("order_type") or "LIMIT",
                    "variety": o.get("variety", "NORMAL"),
                    "status": status,
                    "statusMessage": o.get("text")
                    or o.get("rejectionreason")
                    or o.get("status_message")
                    or "",
                    "tag": o.get("ordertag") or o.get("tag") or "",
                    "orderTimestamp": ts,
                    "exchangeTimestamp": str(
                        o.get("exchtime") or o.get("exchange_timestamp") or ts
                    ),
                }
            )

        normalized_orders.sort(key=lambda x: x["orderTimestamp"], reverse=True)
        result = convert_keys(normalized_orders)
        self._set_cached("orders", result)
        return result

    def get_trades(self) -> List[Dict[str, Any]]:
        """Fetch trade book from SmartAPI."""
        if not self.smart_api:
            return []
        try:
            res = self._execute_with_auth_retry(self.smart_api.tradeBook)
            if (
                not res
                or not res.get("status")
                or not isinstance(res.get("data"), list)
            ):
                return []
            trades = []
            for t in res["data"]:
                trades.append(convert_keys(t))
            return trades
        except Exception as e:
            logger.error("Error getting trade book: %s", e)
            return []

    def estimate_charges(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Query SmartAPI estimateCharges API to fetch broker fees, STT, GST, and regulatory charges.

        Parameters
        ----------
        orders : list of dicts with keys:
            tradingsymbol / symbol_name, product / product_type, transactionType / transaction_type,
            quantity / filledQuantity, price / averagePrice, exchange, token
        """
        if not self.smart_api:
            return {}
        try:
            formatted_orders = []
            for o in orders:
                sym = str(o.get("symbol_name") or o.get("tradingsymbol") or "")
                clean_sym = sym.replace("-EQ", "").upper()
                exchange = str(o.get("exchange") or "NSE").upper()
                token = str(o.get("token") or self.resolve_token(clean_sym, exchange))
                prod = str(
                    o.get("product_type") or o.get("product") or "INTRADAY"
                ).upper()
                if prod == "MIS":
                    prod = "INTRADAY"

                qty = int(o.get("quantity") or o.get("filledQuantity") or 1)
                price = float(o.get("price") or o.get("averagePrice") or 0.0)
                tx_type = str(
                    o.get("transaction_type") or o.get("transactionType") or "BUY"
                ).upper()

                if clean_sym and token:
                    formatted_orders.append(
                        {
                            "product_type": prod,
                            "transaction_type": tx_type,
                            "quantity": str(qty),
                            "price": str(round(price, 2)),
                            "exchange": exchange,
                            "symbol_name": clean_sym,
                            "token": str(token),
                        }
                    )

            if not formatted_orders:
                return {}

            res = self._execute_with_auth_retry(
                self.smart_api.estimateCharges, {"orders": formatted_orders}
            )
            if res and res.get("status") and isinstance(res.get("data"), dict):
                return res["data"]
            return {}
        except Exception as e:
            logger.error("Error calling estimateCharges API: %s", e)
            return {}

    def estimate_round_trip_charges(
        self,
        symbol: str,
        entry_price: float,
        target_price: float,
        qty: int,
        product: str = "INTRADAY",
        exchange: str = "NSE",
        direction: str = "BUY",
    ) -> Dict[str, Any]:
        """
        Query Angel One's live estimateCharges API for complete round-trip trade charges.
        Features a 5-minute memory cache and sub-millisecond local statutory tariff fallback.
        """
        clean_sym = symbol.replace("-EQ", "").strip().upper()
        cache_key = (
            clean_sym,
            round(entry_price, 2),
            round(target_price, 2),
            int(qty),
            product.upper(),
            direction.upper(),
        )

        now_ts = time.time()
        # 1. Check memory cache (5-minute TTL)
        charges_cache = getattr(self, "_charges_cache", {})
        cached = charges_cache.get(cache_key)
        if cached and (now_ts - cached[0]) < 300:
            return cached[1]

        leg1_type = "BUY" if direction.upper() == "BUY" else "SELL"
        leg2_type = "SELL" if direction.upper() == "BUY" else "BUY"

        # 2. Try Angel One live estimateCharges API
        token = self.resolve_token(clean_sym, exchange)
        if token and self.smart_api:
            orders = [
                {
                    "symbol_name": clean_sym,
                    "token": str(token),
                    "exchange": exchange,
                    "product_type": product,
                    "transaction_type": leg1_type,
                    "quantity": int(qty),
                    "price": float(entry_price),
                },
                {
                    "symbol_name": clean_sym,
                    "token": str(token),
                    "exchange": exchange,
                    "product_type": product,
                    "transaction_type": leg2_type,
                    "quantity": int(qty),
                    "price": float(target_price),
                },
            ]
            try:
                api_data = self.estimate_charges(orders)
                if api_data and "summary" in api_data:
                    summary = api_data.get("summary", {})
                    total_charges = float(summary.get("total_charges", 0.0) or 0.0)
                    trade_value = float(summary.get("trade_value", 0.0) or 0.0)

                    brokerage = 0.0
                    ext_charges = 0.0
                    taxes = 0.0
                    stt = 0.0
                    gst = 0.0
                    stamp_duty = 0.0
                    exchange_tx = 0.0
                    sebi = 0.0

                    for b in summary.get("breakup", []):
                        name = str(b.get("name", "")).lower()
                        amt = float(b.get("amount", 0.0) or 0.0)
                        if "brokerage" in name:
                            brokerage = amt
                        elif "external" in name:
                            ext_charges = amt
                            for sub in b.get("breakup") or []:
                                sub_name = str(sub.get("name", "")).lower()
                                sub_amt = float(sub.get("amount", 0.0) or 0.0)
                                if "stamp" in sub_name:
                                    stamp_duty = sub_amt
                                elif "exchange" in sub_name:
                                    exchange_tx = sub_amt
                                elif "sebi" in sub_name:
                                    sebi = sub_amt
                        elif "tax" in name:
                            taxes = amt
                            for sub in b.get("breakup") or []:
                                sub_name = str(sub.get("name", "")).lower()
                                sub_amt = float(sub.get("amount", 0.0) or 0.0)
                                if "security" in sub_name or "stt" in sub_name:
                                    stt = sub_amt
                                elif "gst" in sub_name:
                                    gst = sub_amt

                    gross_gain = round(abs(target_price - entry_price) * qty, 2)
                    net_gain = round(gross_gain - total_charges, 2)
                    f_mult = (
                        round(gross_gain / total_charges, 2)
                        if total_charges > 0
                        else 999.0
                    )

                    result = {
                        "total_charges": round(total_charges, 2),
                        "trade_value": round(trade_value, 2),
                        "brokerage": round(brokerage, 2),
                        "external_charges": round(ext_charges, 2),
                        "taxes": round(taxes, 2),
                        "stt": round(stt, 2),
                        "exchange_turnover": round(exchange_tx, 2),
                        "stamp_duty": round(stamp_duty, 2),
                        "sebi_fees": round(sebi, 4),
                        "gst": round(gst, 2),
                        "gross_pnl": gross_gain,
                        "net_pnl": net_gain,
                        "friction_multiple": f_mult,
                        "is_friction_safe": bool(f_mult >= 3.5),
                        "source": "smartapi_estimate_charges",
                    }
                    charges_cache[cache_key] = (now_ts, result)
                    return result
            except Exception as e:
                logger.warning("estimateCharges API call failed; using local tariff: %s", e)

        # 3. Fallback to ultra-fast local calculation
        result = calculate_statutory_charges_fast(
            entry_price=entry_price,
            exit_price=target_price,
            qty=qty,
            product_type=product,
            exchange=exchange,
            direction=direction,
        )
        charges_cache[cache_key] = (now_ts, result)
        return result


    @staticmethod
    def calculate_statutory_charges_fast(
        entry_price: float,
        exit_price: float,
        qty: int,
        product_type: str = "INTRADAY",
        exchange: str = "NSE",
        direction: str = "BUY",
    ) -> Dict[str, Any]:
        """
        Ultra-fast local calculation conforming to Angel One and SEBI/NSE statutory tariff.
        Executes in < 0.001 ms for high-throughput screening and offline pre-trade analysis.
        """
        buy_price = entry_price if direction.upper() == "BUY" else exit_price
        sell_price = exit_price if direction.upper() == "BUY" else entry_price

        buy_turnover = float(buy_price * qty)
        sell_turnover = float(sell_price * qty)
        total_turnover = buy_turnover + sell_turnover

        is_intraday = product_type.upper() in ("INTRADAY", "MIS")

        if is_intraday:
            # Angel One: Min(0.1%, ₹20) per order with min ₹5
            buy_brokerage = max(5.0, min(20.0, buy_turnover * 0.001))
            sell_brokerage = max(5.0, min(20.0, sell_turnover * 0.001))
            brokerage = round(buy_brokerage + sell_brokerage, 2)
            # STT: 0.025% on sell side only
            stt = round(sell_turnover * 0.00025, 2)
        else:
            # Delivery: ₹0 brokerage on Angel One, STT 0.1% both sides
            brokerage = 0.0
            stt = round(total_turnover * 0.001, 2)

        # Exchange transaction charges: NSE ~0.00297%
        exchange_charges = round(total_turnover * 0.0000297, 2)
        # Stamp duty: 0.003% on buy side only
        stamp_duty = round(buy_turnover * 0.00003, 2)
        # SEBI fees: ₹10/crore = 0.0001%
        sebi_fees = round(total_turnover * 0.000001, 4)
        # GST: 18% on (Brokerage + Exchange Charges + SEBI Fees)
        gst = round((brokerage + exchange_charges + sebi_fees) * 0.18, 2)

        external_charges = round(exchange_charges + stamp_duty + sebi_fees, 2)
        total_taxes = round(stt + gst, 2)
        total_charges = round(brokerage + external_charges + total_taxes, 2)

        gross_pnl = round(abs(exit_price - entry_price) * qty, 2)
        net_pnl = round(gross_pnl - total_charges, 2)
        friction_multiple = (
            round(gross_pnl / total_charges, 2) if total_charges > 0 else 999.0
        )

        return {
            "total_charges": total_charges,
            "trade_value": round(total_turnover, 2),
            "brokerage": brokerage,
            "external_charges": external_charges,
            "taxes": total_taxes,
            "stt": stt,
            "exchange_turnover": exchange_charges,
            "stamp_duty": stamp_duty,
            "sebi_fees": sebi_fees,
            "gst": gst,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "friction_multiple": friction_multiple,
            "is_friction_safe": bool(friction_multiple >= 3.5),
            "source": "local_tariff_engine",
        }

    def resolve_token(self, tradingsymbol: str, exchange: str = "NSE") -> str:
        """Resolve a trading symbol (e.g. 'RELIANCE' or 'RELIANCE-EQ') to an Angel One token."""
        clean = tradingsymbol.replace("-EQ", "").upper()
        if clean in self.token_map:
            return self.token_map[clean]

        # Ensure instruments are loaded
        self.get_instruments(exchange)
        return self.token_map.get(clean, self.token_map.get(f"{clean}-EQ", ""))

    def resolve_trading_symbol(self, tradingsymbol: str, exchange: str = "NSE") -> str:
        """Resolve a trading symbol to Angel One's standard format (e.g. RELIANCE-EQ)."""
        clean = tradingsymbol.replace("-EQ", "").upper()
        if exchange == "NSE":
            return f"{clean}-EQ"
        return tradingsymbol

    def place_order(
        self,
        variety="NORMAL",
        exchange="NSE",
        tradingsymbol="",
        transaction_type="BUY",
        quantity=1,
        product="INTRADAY",
        order_type="LIMIT",
        price=None,
        trigger_price=None,
        disclosed_quantity=None,
        squareoff=None,
        stoploss=None,
        trailing_stoploss=None,
        tag=None,
        **kwargs,
    ) -> str:
        """Place an order through Angel One SmartAPI."""
        from .config import config_manager

        if not self.smart_api:
            raise RuntimeError("SmartAPI client not initialized")

        # Normalize product type
        if product == "MIS":
            prod_type = "INTRADAY"
        elif product == "CNC":
            prod_type = "DELIVERY"
        elif product == "NRML":
            prod_type = "CARRYFORWARD"
        else:
            prod_type = product.upper()

        # Normalize order type
        ord_type = order_type.upper()
        if ord_type == "SL":
            ord_type = "STOPLOSS_LIMIT"
        elif ord_type == "SL-M":
            ord_type = "STOPLOSS_MARKET"

        # Normalize variety
        var = "NORMAL"
        if variety:
            var_upper = variety.upper()
            if var_upper in ("REGULAR", "NORMAL"):
                var = "NORMAL"
            elif var_upper in ("AMO", "ROBO", "STOPLOSS"):
                var = var_upper

        token = self.resolve_token(tradingsymbol, exchange)
        actual_symbol = self.resolve_trading_symbol(tradingsymbol, exchange)

        order_params = {
            "variety": var,
            "tradingsymbol": actual_symbol,
            "symboltoken": str(token),
            "transactiontype": transaction_type.upper(),
            "exchange": exchange.upper(),
            "ordertype": ord_type,
            "producttype": prod_type,
            "duration": str(kwargs.get("duration", "DAY")).upper(),
            "price": str(round(float(price), 2)) if price else "0",
            "quantity": str(int(quantity)),
            "triggerprice": str(round(float(trigger_price), 2))
            if trigger_price
            else "0",
        }
        if squareoff:
            order_params["squareoff"] = str(squareoff)
        if stoploss:
            order_params["stoploss"] = str(stoploss)
        if trailing_stoploss:
            order_params["trailingstoploss"] = str(trailing_stoploss)

        res = self._execute_with_auth_retry(self.smart_api.placeOrder, order_params)
        if not res:
            raise RuntimeError("No response received from placeOrder")

        order_id = ""
        if isinstance(res, str):
            order_id = res
        elif isinstance(res, dict):
            if res.get("status") and res.get("data"):
                order_id = str(res["data"].get("orderid", ""))
            elif not res.get("status"):
                raise RuntimeError(
                    res.get("message") or res.get("errorcode", "Order placement failed")
                )

        if not order_id:
            order_id = str(res)

        config_manager.add_app_order_id(order_id)
        self.clear_cache()
        return order_id

    def cancel_order(self, variety="NORMAL", order_id="", parent_order_id=None):
        if not self.smart_api:
            return {}
        var = "NORMAL" if variety in ("regular", "NORMAL") else variety
        res = self._execute_with_auth_retry(self.smart_api.cancelOrder, order_id, var)
        self.clear_cache()
        return res

    def modify_order(
        self,
        variety="NORMAL",
        order_id="",
        parent_order_id=None,
        exchange="NSE",
        tradingsymbol=None,
        transaction_type=None,
        quantity=None,
        price=None,
        order_type=None,
        product=None,
        trigger_price=None,
        **kwargs,
    ):
        if not self.smart_api:
            return {}

        prod_type = (
            "INTRADAY" if product in ("MIS", "INTRADAY") else (product or "INTRADAY")
        )
        ord_type = order_type or "LIMIT"
        if ord_type == "SL":
            ord_type = "STOPLOSS_LIMIT"
        elif ord_type == "SL-M":
            ord_type = "STOPLOSS_MARKET"

        var = "NORMAL" if variety in ("regular", "NORMAL") else variety
        token = self.resolve_token(tradingsymbol, exchange) if tradingsymbol else ""
        actual_symbol = (
            self.resolve_trading_symbol(tradingsymbol, exchange)
            if tradingsymbol
            else ""
        )

        params = {
            "variety": var,
            "orderid": str(order_id),
            "ordertype": ord_type,
            "producttype": prod_type,
            "duration": str(kwargs.get("duration", "DAY")).upper(),
            "price": str(price) if price is not None else "0",
            "quantity": str(quantity) if quantity is not None else "1",
            "exchange": exchange,
        }
        if actual_symbol:
            params["tradingsymbol"] = actual_symbol
        if token:
            params["symboltoken"] = str(token)
        if trigger_price:
            params["triggerprice"] = str(trigger_price)

        res = self._execute_with_auth_retry(self.smart_api.modifyOrder, params)
        self.clear_cache()
        return res

    def get_margins(self, force: bool = False) -> Dict[str, Any]:
        """Fetch RMS Limits and structure into standard margin representation."""
        if not force:
            cached = self._get_cached("margins")
            if cached is not None:
                return cached

        if not self.smart_api:
            return {}
        try:
            res = self._execute_with_auth_retry(self.smart_api.rmsLimit)
            data = res.get("data", {}) if (res and res.get("status")) else {}

            net = float(data.get("net", 0.0) or 0.0)
            avail_cash = float(data.get("availablecash", 0.0) or 0.0)
            collateral = float(data.get("collateral", 0.0) or 0.0)
            live_bal = avail_cash if avail_cash > 0 else net

            result = {
                "equity": {
                    "net": net,
                    "available": {
                        "live_balance": live_bal,
                        "cash": avail_cash,
                        "collateral": collateral,
                        "net": net,
                    },
                    "utilised": {
                        "debits": float(data.get("utiliseddebits", 0.0) or 0.0),
                        "m2mRealised": float(data.get("m2mrealized", 0.0) or 0.0),
                        "m2mUnrealised": float(data.get("m2munrealized", 0.0) or 0.0),
                    },
                }
            }
            self._set_cached("margins", result)
            return result
        except Exception as e:
            logger.error("Error getting RMS limits: %s", e)
            return {}

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Fetch Demat holdings and normalize."""
        if not self.smart_api:
            return []
        try:
            res = self._execute_with_auth_retry(self.smart_api.holding)
            holdings = res.get("data", []) if (res and res.get("status")) else []
            normalized = []
            for h in holdings:
                normalized.append(
                    {
                        "tradingsymbol": h.get("tradingsymbol", ""),
                        "exchange": h.get("exchange", "NSE"),
                        "instrumentToken": h.get("symboltoken", ""),
                        "quantity": int(h.get("quantity", 0)),
                        "averagePrice": float(h.get("averageprice", 0.0)),
                        "lastPrice": float(h.get("ltp", 0.0)),
                        "pnl": float(h.get("pnl", 0.0)),
                        "closePrice": float(h.get("close", 0.0) or h.get("ltp", 0.0)),
                    }
                )
            return convert_keys(normalized)
        except Exception as e:
            logger.error("Error getting holdings: %s", e)
            return []

    def get_historical_data(
        self,
        instrument_token: Any,
        from_date: Any,
        to_date: Any,
        interval: str = "5minute",
        exchange: str = "NSE",
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Fetch historical candle data via SmartAPI getCandleData."""
        if not self.smart_api:
            return []

        mapped_interval = INTERVAL_MAP.get(interval, "FIVE_MINUTE")

        # Format dates as YYYY-MM-DD HH:MM
        def format_date(d):
            if hasattr(d, "strftime"):
                return d.strftime("%Y-%m-%d %H:%M")
            return str(d)[:16]

        from_str = format_date(from_date)
        to_str = format_date(to_date)

        historic_params = {
            "exchange": exchange,
            "symboltoken": str(instrument_token),
            "interval": mapped_interval,
            "fromdate": from_str,
            "todate": to_str,
        }

        # Enforce rate-limit pacing on getCandleData (max 3 req/sec -> 0.55s delay)
        candle_lock = getattr(self, "_candle_lock", None)
        if candle_lock is not None:
            with candle_lock:
                now_t = time.time()
                last_t = getattr(self, "_last_candle_fetch_time", 0.0)
                elapsed = now_t - last_t
                if elapsed < 0.55:
                    time.sleep(0.55 - elapsed)
                self._last_candle_fetch_time = time.time()

        try:
            res = self._execute_with_auth_retry(
                self.smart_api.getCandleData, historic_params
            )
            if (
                not res
                or not res.get("status")
                or not isinstance(res.get("data"), list)
            ):
                return []

            records = []
            for row in res["data"]:
                if len(row) >= 6:
                    records.append(
                        {
                            "date": row[0],
                            "open": float(row[1]),
                            "high": float(row[2]),
                            "low": float(row[3]),
                            "close": float(row[4]),
                            "volume": float(row[5]),
                        }
                    )
            return records
        except Exception as e:
            logger.error(
                "Error getting candle data for token %s: %s", instrument_token, e
            )
            return []

    def get_ltp(self, instruments: List[str]) -> Dict[str, Any]:
        """Fetch LTP for given instruments ['NSE:RELIANCE', 'SBIN', ...]."""
        res_map = {}
        for inst in instruments:
            clean = inst.replace("NSE:", "").replace("-EQ", "").upper()
            token = self.resolve_token(clean)
            symbol = self.resolve_trading_symbol(clean)
            price_val = 0.0
            if self.smart_api and token:
                try:
                    time.sleep(0.35)
                    data = self._execute_with_auth_retry(
                        self.smart_api.ltpData, "NSE", symbol, token
                    )
                    if data and data.get("status") and data.get("data"):
                        price_val = float(data["data"].get("ltp", 0.0))
                except Exception:
                    pass
            entry = {
                "last_price": price_val,
                "lastPrice": price_val,
                "ltp": price_val,
            }
            res_map[inst] = entry
            res_map[clean] = entry
        return res_map

    def get_quote(self, instruments: List[str]) -> Dict[str, Any]:
        """Fetch quote information for list of instruments."""
        result = {}
        tokens_to_fetch = []
        token_to_inst = {}

        for inst in instruments:
            clean = inst.replace("NSE:", "").replace("-EQ", "").upper()
            token = self.resolve_token(clean)
            if token:
                tokens_to_fetch.append(token)
                token_to_inst[token] = inst

        if self.smart_api and tokens_to_fetch:
            try:
                # Use SmartAPI getMarketData
                market_data = self._execute_with_auth_retry(
                    self.smart_api.getMarketData, "FULL", {"NSE": tokens_to_fetch}
                )
                if (
                    market_data
                    and market_data.get("status")
                    and market_data.get("data")
                ):
                    fetched = market_data["data"].get("fetched", [])
                    for item in fetched:
                        tok = str(item.get("symbolToken", ""))
                        orig_inst = token_to_inst.get(tok)
                        if orig_inst:
                            ltp = float(item.get("ltp", 0.0) or 0.0)
                            open_p = float(item.get("open", 0.0) or 0.0)
                            high_p = float(item.get("high", 0.0) or 0.0)
                            low_p = float(item.get("low", 0.0) or 0.0)
                            close_p = float(item.get("close", 0.0) or 0.0)
                            vol = float(item.get("tradeVolume", 0.0) or 0.0)

                            result[orig_inst] = {
                                "last_price": ltp,
                                "volume": vol,
                                "ohlc": {
                                    "open": open_p,
                                    "high": high_p,
                                    "low": low_p,
                                    "close": close_p,
                                },
                            }
            except Exception as e:
                logger.warning("Error fetching batch market data: %s", e)

        # Fallback for instruments not yet retrieved
        for inst in instruments:
            if inst not in result:
                clean = inst.replace("NSE:", "").replace("-EQ", "").upper()
                token = self.resolve_token(clean)
                symbol = self.resolve_trading_symbol(clean)
                ltp = 0.0
                if self.smart_api and token:
                    try:
                        time.sleep(0.35)
                        ltp_res = self._execute_with_auth_retry(
                            self.smart_api.ltpData, "NSE", symbol, token
                        )
                        if ltp_res and ltp_res.get("status") and ltp_res.get("data"):
                            ltp = float(ltp_res["data"].get("ltp", 0.0))
                    except Exception:
                        pass
                result[inst] = {
                    "last_price": ltp,
                    "volume": 100000.0,
                    "ohlc": {
                        "open": ltp,
                        "high": ltp * 1.01,
                        "low": ltp * 0.99,
                        "close": ltp,
                    },
                }

        return result

    def get_ohlc(self, instruments: List[str]) -> Dict[str, Any]:
        """Fetch OHLC and last price for list of instruments."""
        quotes = self.get_quote(instruments)
        result = {}
        for inst, q in quotes.items():
            result[inst] = {
                "instrument_token": q.get("instrument_token", ""),
                "last_price": q.get("last_price", 0.0),
                "ohlc": q.get("ohlc", {}),
            }
        return result

    def get_instruments(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        """Retrieve instrument list, using disk cache and falling back to bundled mappings."""
        if self.instruments_cache:
            if exchange:
                return [
                    i for i in self.instruments_cache if i.get("exchange") == exchange
                ]
            return self.instruments_cache

        cache_dir = Path.home() / ".smartapi-agentic-trading"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "scrip_master.json"

        instruments_raw = None

        # Check local disk cache
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    instruments_raw = json.load(f)
            except Exception as e:
                logger.warning("Failed to load cached scrip master: %s", e)

        # If not cached, attempt download from Angel One OpenAPI
        if not instruments_raw:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "SmartApi-Trading/1.0"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    instruments_raw = json.loads(response.read().decode("utf-8"))
                    with open(cache_file, "w") as f:
                        json.dump(instruments_raw, f)
            except Exception as e:
                logger.info("Using bundled scrip tokens (offline/timeout): %s", e)

        normalized = []
        if isinstance(instruments_raw, list):
            for item in instruments_raw:
                tok = str(item.get("token", ""))
                sym = item.get("symbol", "")
                exch = item.get("exch_seg", "")
                if exch == "NSE" and sym:
                    clean = sym.replace("-EQ", "")
                    self.token_map[clean] = tok
                    self.token_map[sym] = tok
                    self.symbol_map[clean] = sym
                    self.symbol_map[tok] = sym

                normalized.append(
                    {
                        "instrument_token": tok,
                        "tradingsymbol": sym,
                        "name": item.get("name", sym),
                        "exchange": exch,
                        "tick_size": float(item.get("tick_size") or 0.05),
                        "lot_size": int(item.get("lotsize") or 1),
                        "instrument_type": item.get("instrumenttype", ""),
                    }
                )
        else:
            # Populate from bundled list
            for sym, tok in BUNDLED_NSE_TOKENS.items():
                normalized.append(
                    {
                        "instrument_token": tok,
                        "tradingsymbol": f"{sym}-EQ",
                        "name": sym,
                        "exchange": "NSE",
                        "tick_size": 0.05,
                        "lot_size": 1,
                        "instrument_type": "EQ",
                    }
                )

        self.instruments_cache = normalized
        if exchange:
            return [i for i in normalized if i.get("exchange") == exchange]
        return normalized

    def search_instruments(
        self, query: str, exchange: str = "NSE"
    ) -> List[Dict[str, Any]]:
        query_upper = query.upper().strip()
        instruments = self.get_instruments(exchange or "NSE")
        results = [
            i
            for i in instruments
            if query_upper in i["tradingsymbol"]
            or query_upper in i.get("name", "").upper()
        ][:50]
        return results


smart_api_client = SmartApiClient()
