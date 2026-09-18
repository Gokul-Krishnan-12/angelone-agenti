import json
import shutil
from pathlib import Path

from cryptography.fernet import Fernet


class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".smartapi-agentic-trading"
        self.legacy_dir = Path.home() / ".kite-agentic-trading"
        self.config_file = self.config_dir / "config.json"
        self.key_file = self.config_dir / ".key"
        self.config = {}

        self.default_config = {
            "risk": {
                "maxCapitalPerTrade": 8000,
                "riskPerTrade": 700.0,  # 1R risk budget per trade in INR (scaled with capital to dilute friction)
                "riskPercent": 1.0,  # 1.0% of portfolio equity risk per trade
                "maxDailyLoss": 2000,  # raised from ₹800 → prevents premature engine shutdown after 1-2 SLs
                "maxSimultaneousPositions": 4,
                "maxDailyTrades": 8,
                "noNewTradesAfter": "15:00",
                "autoSquareOff": True,
                "squareOffTime": "15:15",
                "defaultStopLossPercent": 1.2,
                "defaultTargetPercent": 2.4,  # exact 1:2 R:R against 1.2% stop-loss
                "positionRevalWeakExitMins": 15,
                "positionRevalBreakevenMins": 20,  # idle trade circuit breaker stagnation timeout (20 mins)
                # ── Quality filters ──────────────────────────────────
                "minConfluenceScore": 3,  # 3 independent families required for CHOPPY_RANGE regime
                "minConfluenceScoreTrending": 2,  # 2 families allowed in TRENDING_BULL/TRENDING_BEAR regimes
                "minRiskReward": 2.0,  # minimum 1:2 R:R ratio for any trade
                "minStopLossPercent": 1.0,  # minimum 1.0% SL width to prevent noise stop-outs
                "trendAlignmentFilter": True,  # trade only in direction of 50-period EMA
                "noEntryFirstMins": 15,  # skip first 15 min (9:15–9:30 opening chaos)
                "pendingOrderTimeoutSeconds": 15,  # unexecuted limit cancellation window (15s to prevent stale fills on fading moves)
                # ── Market Regime Filter ──────────────────────────
                "marketRegimeFilterEnabled": True,  # quantitative regime & volatility filter
                "marketRegimeMinADX": 20.0,  # trend strength threshold
                "marketRegimeMinKER": 0.35,  # Kaufman efficiency ratio threshold
                "marketRegimeBlockChoppyBreakouts": True,  # suppress false-breakout churn in chop
                # ── Trailing stop-loss ────────────────────────────
                "trailingSlEnabled": True,  # enable ATR trailing SL
                "trailingSlAtrMultiplier": 2.2,  # ATR multiplier for trailing distance
                "trailingSlProfitCushionR": 1.5,  # trail only after reaching +1.5R profit (prevents premature choking)
                # ── Partial Profit Booking ────────────────────────
                "partialBookingEnabled": True,  # book 50% at Target 1 and move SL to breakeven
                "partialBookingRatio": 0.5,  # 50% quantity exit at Target 1
                "partialBookingMinProfit": 250.0,  # minimum ₹250 gain to justify extra ₹20 brokerage order
                "partialBookingTargetRR": 1.2,  # front-load Target 1 at +1.2R (covers round-trip friction)
                # ── 2-Leg Scale-In Entry ─────────────────────────
                "scaleInEnabled": True,  # 50% qty at breakout, 50% on EMA20/VWAP pullback → improves avg entry
                "scaleInLeg1Ratio": 0.5,  # fraction of calculated qty placed as Leg 1
                "scaleInLeg2TimeoutMultiplier": 2,  # Leg 2 waits 2× pendingOrderTimeoutSeconds before being skipped
            },
            "strategies": {
                # ── Top alpha strategies: breakout, structure, volume ──
                "donchian_breakout": {"enabled": True},
                "keltner_breakout": {"enabled": True},
                "bollinger_breakout": {"enabled": True},
                "volume_delta_divergence": {"enabled": True},
                "cmf_accumulation": {"enabled": True},
                "liquidity_grab_reversal": {"enabled": True},
                "gap_fill": {"enabled": True},
                "fixed_range_volume_profile": {"enabled": True},
                # ── Negative alpha on 5m intraday ──
                "institutional_absorption": {"enabled": False},  # -₹3,226 drag on 5m
                "cpr_breakout_reversal": {"enabled": False},  # Whipsaws on 5m rolling windows
                "order_block_fvg": {"enabled": False},  # Whipsaw prone on 5m
                "opening_range_breakout": {"enabled": False},  # False breakout chop in opening 15m
                # ── Pruned lagging indicators & negative expectancy oscillators ──
                "psar_trend": {"enabled": False},  # -₹8,575 P&L in backtests
                "ema_crossover": {"enabled": False},  # -₹2,201 P&L in backtests
                "macd_cross": {"enabled": False},  # Flat/negative fee drag
                "supertrend": {"enabled": False},  # Whipsaw prone on 15m
                "tsi_cross": {"enabled": True},  # consistent positive alpha: +₹5,575/+₹7,967 across backtests
                "awesome_oscillator": {"enabled": False},
                "stoc_rsi": {"enabled": False},
                "stochastic_reversal": {"enabled": False},
                "mfi_exhaustion": {"enabled": False},
                "williams_r": {"enabled": False},  # 56.8% SL rate, -₹2,446 P&L
                "cci_reversal": {"enabled": False},  # 63.3% SL rate, -₹1,813 P&L
                "adx_momentum": {"enabled": False},  # 62.0% SL rate, -₹291 P&L
                "rsi_reversal": {"enabled": False},  # 57.9% SL rate, -₹228 P&L
                "vwap_bounce": {"enabled": False},  # 88.9% SL rate, -₹172 P&L
            },
            "watchlist": [
                "RELIANCE",
                "TCS",
                "HDFCBANK",
                "INFY",
                "ICICIBANK",
                "HINDUNILVR",
                "ITC",
                "SBIN",
                "BHARTIARTL",
                "KOTAKBANK",
                "LT",
                "AXISBANK",
                "ASIANPAINT",
                "MARUTI",
                "TITAN",
                "SUNPHARMA",
                "BAJFINANCE",
                "WIPRO",
                "ULTRACEMCO",
                "NESTLEIND",
            ],
            "notifications": {
                "telegram": {
                    "enabled": False,
                    "botToken": "",
                    "chatId": "",
                    "notifyOnTradeExit": True,
                    "notifyOnSessionEnd": True,
                }
            },
            "mode": "confirm",  # default to confirmation mode for safety
            "credentials": {
                "apiKey": "",
                "clientCode": "",
                "pin": "",
                "totpSecret": "",
                "jwtToken": "",
                "refreshToken": "",
                "feedToken": "",
            },
        }

        self._init_dir()
        self._init_key()
        self.load()

    def _init_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        # Migrate non-credential settings from legacy directory if needed
        if not self.config_file.exists() and (self.legacy_dir / "config.json").exists():
            try:
                with open(self.legacy_dir / "config.json", "r") as f:
                    legacy_cfg = json.load(f)
                new_cfg = self.default_config.copy()
                if "risk" in legacy_cfg:
                    new_cfg["risk"].update(legacy_cfg["risk"])
                if "strategies" in legacy_cfg:
                    new_cfg["strategies"].update(legacy_cfg["strategies"])
                if "watchlist" in legacy_cfg:
                    new_cfg["watchlist"] = legacy_cfg["watchlist"]
                with open(self.config_file, "w") as f:
                    json.dump(new_cfg, f, indent=4)
            except Exception:
                pass

    def _init_key(self):
        if not self.key_file.exists():
            # Check legacy key
            legacy_key_file = self.legacy_dir / ".key"
            if legacy_key_file.exists():
                try:
                    shutil.copy(legacy_key_file, self.key_file)
                except Exception:
                    pass

        if not self.key_file.exists():
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)

        with open(self.key_file, "rb") as f:
            self.cipher_suite = Fernet(f.read())

    def _encrypt(self, text: str) -> str:
        if not text:
            return ""
        return self.cipher_suite.encrypt(text.encode()).decode()

    def _decrypt(self, text: str) -> str:
        if not text:
            return ""
        try:
            return self.cipher_suite.decrypt(text.encode()).decode()
        except Exception:
            return ""

    def load(self):
        import copy

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded = json.load(f)

                self.config = copy.deepcopy(self.default_config)
                for k, v in loaded.items():
                    if isinstance(v, dict) and k in self.config:
                        self.config[k].update(v)
                    else:
                        self.config[k] = v
            except json.JSONDecodeError:
                self.config = copy.deepcopy(self.default_config)
        else:
            self.config = copy.deepcopy(self.default_config)
            self.save()

    def save(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def get_credentials(self):
        creds = self.config.get("credentials", {})
        api_key = self._decrypt(creds.get("apiKey", ""))
        client_code = self._decrypt(creds.get("clientCode", ""))
        pin = self._decrypt(creds.get("pin", ""))
        totp_secret = self._decrypt(creds.get("totpSecret", ""))
        jwt_token = self._decrypt(creds.get("jwtToken", ""))
        if jwt_token:
            jwt_token = jwt_token.replace("Bearer ", "").replace("bearer ", "").strip()
        refresh_token = self._decrypt(creds.get("refreshToken", ""))
        feed_token = self._decrypt(creds.get("feedToken", ""))

        # Backward compatibility
        legacy_secret = self._decrypt(creds.get("apiSecret", ""))

        return {
            "apiKey": api_key,
            "clientCode": client_code,
            "pin": pin,
            "totpSecret": totp_secret,
            "jwtToken": jwt_token,
            "accessToken": jwt_token,  # alias
            "refreshToken": refresh_token,
            "feedToken": feed_token,
            "apiSecret": legacy_secret,  # alias
        }

    def save_credentials(
        self,
        api_key: str,
        client_code: str = "",
        pin: str = "",
        totp_secret: str = "",
        jwt_token: str = "",
        refresh_token: str = "",
        feed_token: str = "",
        api_secret: str = "",
        access_token: str = "",
    ):
        if "credentials" not in self.config:
            self.config["credentials"] = {}

        if api_key:
            self.config["credentials"]["apiKey"] = self._encrypt(api_key)
        if client_code:
            self.config["credentials"]["clientCode"] = self._encrypt(client_code)
        if pin:
            self.config["credentials"]["pin"] = self._encrypt(pin)
        if totp_secret:
            self.config["credentials"]["totpSecret"] = self._encrypt(totp_secret)
        if jwt_token or access_token:
            token = (
                (jwt_token or access_token)
                .replace("Bearer ", "")
                .replace("bearer ", "")
                .strip()
            )
            self.config["credentials"]["jwtToken"] = self._encrypt(token)
            self.config["credentials"]["accessToken"] = self._encrypt(token)
        if refresh_token:
            self.config["credentials"]["refreshToken"] = self._encrypt(refresh_token)
        if feed_token:
            self.config["credentials"]["feedToken"] = self._encrypt(feed_token)
        if api_secret:
            self.config["credentials"]["apiSecret"] = self._encrypt(api_secret)

        self.save()

    def get_risk_config(self):
        self.load()
        return self.config.get("risk", self.default_config["risk"])

    def get_strategy_config(self):
        self.load()
        return self.config.get("strategies", self.default_config["strategies"])

    def get_watchlist(self):
        self.load()
        return self.config.get("watchlist", self.default_config["watchlist"])

    def get_notifications_config(self) -> dict:
        return self.config.get(
            "notifications", self.default_config.get("notifications", {})
        )

    def get_app_order_ids(self) -> set:
        path = self.config_dir / "app_orders.json"
        if path.exists():
            try:
                with open(path, "r") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def add_app_order_id(self, order_id: str):
        if not order_id:
            return
        orders = self.get_app_order_ids()
        orders.add(str(order_id))
        path = self.config_dir / "app_orders.json"
        with open(path, "w") as f:
            json.dump(list(orders), f)

    def get_historical_orders(self) -> dict:
        path = self.config_dir / "historical_orders.json"
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_historical_orders(self, orders: dict):
        path = self.config_dir / "historical_orders.json"
        with open(path, "w") as f:
            json.dump(orders, f, indent=4, default=str)

    def get_active_trades(self) -> dict:
        path = self.config_dir / "active_trades.json"
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_active_trades(self, trades: dict):
        path = self.config_dir / "active_trades.json"
        try:
            with open(path, "w") as f:
                json.dump(trades, f, indent=4, default=str)
        except Exception:
            pass


config_manager = ConfigManager()
