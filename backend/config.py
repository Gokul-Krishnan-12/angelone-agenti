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
                "maxCapitalPerTrade": 10000,
                "maxDailyLoss": 2000,
                "maxSimultaneousPositions": 5,
                "noNewTradesAfter": "15:00",
                "autoSquareOff": True,
                "squareOffTime": "15:15",
                "defaultStopLossPercent": 1.5,
                "defaultTargetPercent": 3,
                "positionRevalWeakExitMins": 15,
                "positionRevalBreakevenMins": 45,
                # ── Quality filters ──────────────────────────────────
                "minConfluenceScore": 3,  # 3 independent families required (raised from 2)
                "minRiskReward": 1.8,  # minimum R:R ratio for any trade
                "noEntryFirstMins": 45,  # skip first 45 min (9:15–10:00 opening chaos)
                # ── Trailing stop-loss ────────────────────────────
                "trailingSlEnabled": True,  # enable ATR trailing SL
                "trailingSlAtrMultiplier": 1.5,  # trail N × ATR behind high-water mark
            },
            "strategies": {
                # ── Top 10 strategies by backtest P&L (6mo, daily, 20 Nifty 50 stocks) ──
                # Rank  Strategy                    P&L (₹)
                #  1    volume_delta_divergence      3,007   ← new institutional strategy
                #  2    cmf_accumulation             2,216
                #  3    keltner_breakout             2,119
                #  4    williams_r                   2,079
                #  5    cci_reversal                 1,603
                #  6    macd_cross                   1,346
                #  7    bollinger_breakout           1,135
                #  8    stochastic_reversal            909
                #  9    tsi_cross                      877
                # 10    psar_trend                     567
                # ────────────────────────────────────────────────────────────────────────
                "volume_delta_divergence": {"enabled": True},  # rank 1  ₹3,007
                "cmf_accumulation": {"enabled": True},  # rank 2  ₹2,216
                "keltner_breakout": {"enabled": True},  # rank 3  ₹2,119
                "williams_r": {"enabled": True},  # rank 4  ₹2,079
                "cci_reversal": {"enabled": True},  # rank 5  ₹1,603
                "macd_cross": {"enabled": True},  # rank 6  ₹1,346
                "bollinger_breakout": {"enabled": True},  # rank 7  ₹1,135
                "stochastic_reversal": {"enabled": True},  # rank 8  ₹  909
                "tsi_cross": {"enabled": True},  # rank 9  ₹  877
                "psar_trend": {"enabled": True},  # rank 10 ₹  567
                # ── Disabled — underperformed in 6-month backtest ───────────────────────
                "awesome_oscillator": {"enabled": False},  # ₹525  (cut)
                "stoc_rsi": {"enabled": False},  # ₹514  (cut)
                "adx_momentum": {"enabled": False},  # ₹251  (cut)
                "donchian_breakout": {"enabled": False},  # ₹172  (cut)
                "rsi_reversal": {"enabled": False},  # ₹131  (cut)
                "ema_crossover": {"enabled": False},  # ₹ 99  (cut)
                "mfi_exhaustion": {"enabled": False},  # ₹ -7  (cut)
                "order_block_fvg": {"enabled": False},  # ₹-113 (cut)
                "institutional_absorption": {
                    "enabled": False
                },  # ₹  0  (no signal on daily)
                "supertrend": {"enabled": False},  # ₹  0  (no signal on daily)
                "vwap_bounce": {"enabled": False},  # ₹  0  (no signal on daily)
                # ── High-win-rate reversal strategies (new) ──────────────────
                "opening_range_breakout": {"enabled": True},  # ~65-72% win rate
                "liquidity_grab_reversal": {"enabled": True},  # ~68-78% win rate
                "gap_fill": {"enabled": True},  # ~65-70% win rate
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
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded = json.load(f)

                self.config = self.default_config.copy()
                for k, v in loaded.items():
                    if isinstance(v, dict) and k in self.config:
                        self.config[k].update(v)
                    else:
                        self.config[k] = v
            except json.JSONDecodeError:
                self.config = self.default_config.copy()
        else:
            self.config = self.default_config.copy()
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
        return self.config.get("risk", self.default_config["risk"])

    def get_strategy_config(self):
        return self.config.get("strategies", self.default_config["strategies"])

    def get_watchlist(self):
        return self.config.get("watchlist", self.default_config["watchlist"])

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


config_manager = ConfigManager()
