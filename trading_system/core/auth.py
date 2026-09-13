"""
Headless Authentication & Automatic Token Renewal Service.
Interacts with Angel One SmartAPI using TOTP without manual intervention.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict

import pyotp
from loguru import logger
from SmartApi import SmartConnect

from ..config.settings import Settings, get_settings


@dataclass
class SessionTokens:
    """SmartAPI session authentication tokens."""

    jwt_token: str
    refresh_token: str
    feed_token: str
    client_code: str
    is_authenticated: bool


class AuthManager:
    """
    Manages headless programmatic login and asynchronous background token renewal.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.smart_api: SmartConnect | None = None
        self.session: SessionTokens = SessionTokens(
            jwt_token="",
            refresh_token="",
            feed_token="",
            client_code=self.settings.client_code,
            is_authenticated=False,
        )
        self._renewal_task: asyncio.Task | None = None
        self._is_running: bool = False

    def generate_totp(self) -> str:
        """Generate current 6-digit TOTP code using configured secret."""
        secret = self.settings.totp_secret.strip().replace(" ", "")
        if not secret:
            return ""
        if secret.isdigit() and len(secret) == 6:
            return secret
        try:
            return pyotp.TOTP(secret).now()
        except Exception as e:
            logger.error("Failed to generate TOTP code: %s", e)
            return ""

    def login(self) -> SessionTokens:
        """
        Execute headless login with SmartConnect using Client Code, MPIN, and TOTP.
        In paper mode with dummy credentials, establishes a simulated valid session.
        """
        api_key = self.settings.api_key
        client_code = self.settings.client_code
        pin = self.settings.pin
        totp = self.generate_totp()

        if self.settings.mode == "paper" and (not api_key or not client_code):
            logger.info("Paper trading mode: using simulated session credentials.")
            self.session = SessionTokens(
                jwt_token="SIMULATED_JWT_TOKEN",
                refresh_token="SIMULATED_REFRESH_TOKEN",
                feed_token="SIMULATED_FEED_TOKEN",
                client_code=client_code or "PAPER_TRADER",
                is_authenticated=True,
            )
            return self.session

        if not api_key or not client_code or not pin:
            raise ValueError(
                "SmartAPI credentials (API_KEY, CLIENT_CODE, PIN) must be provided in .env or settings."
            )

        if not totp:
            raise ValueError("Failed to generate TOTP. Verify TOTP_SECRET in .env.")

        logger.info(
            "Authenticating headless session with SmartAPI for user %s...", client_code
        )
        self.smart_api = SmartConnect(api_key=api_key)
        session_data: Dict[str, Any] = self.smart_api.generateSession(
            client_code, pin, totp
        )

        if not session_data or not session_data.get("status"):
            err = session_data.get("message") or session_data.get(
                "errorcode", "Unknown auth failure"
            )
            logger.error("SmartAPI login failed: %s", err)
            raise RuntimeError(f"SmartAPI login failed: {err}")

        data = session_data.get("data", {})
        jwt_raw = data.get("jwtToken", "")
        clean_jwt = jwt_raw.replace("Bearer ", "").replace("bearer ", "").strip()
        refresh_token = data.get("refreshToken", "")
        feed_token = data.get("feedToken", "")

        self.smart_api.setAccessToken(clean_jwt)
        self.smart_api.setRefreshToken(refresh_token)
        self.smart_api.setFeedToken(feed_token)

        self.session = SessionTokens(
            jwt_token=clean_jwt,
            refresh_token=refresh_token,
            feed_token=feed_token,
            client_code=client_code,
            is_authenticated=True,
        )
        logger.success(
            "Headless SmartAPI authentication successful for user %s.", client_code
        )
        return self.session

    def renew_token(self) -> bool:
        """Proactively renew the JWT access token using the active refresh token."""
        if not self.smart_api or not self.session.refresh_token:
            if self.settings.mode == "paper":
                return True
            logger.warning("Cannot renew token: SmartConnect or refreshToken missing.")
            return False

        try:
            logger.info("Initiating proactive JWT access token renewal...")
            res = self.smart_api.renewAccessToken()
            if res and isinstance(res, dict):
                data = res.get("data") if isinstance(res.get("data"), dict) else res
                new_jwt = data.get("jwtToken")
                if new_jwt:
                    clean_jwt = (
                        new_jwt.replace("Bearer ", "").replace("bearer ", "").strip()
                    )
                    self.session.jwt_token = clean_jwt
                    self.smart_api.setAccessToken(clean_jwt)

                    new_refresh = data.get("refreshToken")
                    if new_refresh:
                        self.session.refresh_token = new_refresh
                        self.smart_api.setRefreshToken(new_refresh)

                    logger.success("JWT access token renewed successfully.")
                    return True
        except Exception as e:
            logger.error("Error during SmartAPI access token renewal: %s", e)

        return False

    async def start_auto_renewal_task(self, interval_hours: float = 5.0):
        """Asynchronous background loop to keep the SmartAPI session active indefinitely."""
        self._is_running = True
        interval_seconds = interval_hours * 3600.0
        logger.info(
            "Starting automatic token renewal supervisor (interval: %.1f hours)...",
            interval_hours,
        )

        while self._is_running:
            try:
                await asyncio.sleep(interval_seconds)
                if not self._is_running:
                    break
                self.renew_token()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in token renewal task: %s", e)

    def stop(self):
        """Stop background renewal task."""
        self._is_running = False
        if self._renewal_task and not self._renewal_task.done():
            self._renewal_task.cancel()
