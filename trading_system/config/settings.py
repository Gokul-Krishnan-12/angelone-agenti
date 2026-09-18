"""
Settings and configuration management using Pydantic Settings.
Incorporates Indian regulatory tax rates, exchange fees, and risk thresholds.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System-wide trading engine settings loaded from environment or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Angel One SmartAPI Credentials ──────────────────────────────
    api_key: str = Field(default="", description="SmartAPI Application API Key")
    client_code: str = Field(default="", description="Angel One Client Code (User ID)")
    pin: str = Field(default="", description="Angel One 4-digit MPIN or password")
    totp_secret: str = Field(default="", description="Base32 TOTP Secret Key")

    # ── Operating Mode ──────────────────────────────────────────────
    mode: str = Field(
        default="paper", description="'paper' (simulated) or 'live' (broker orders)"
    )

    # ── Capital & Risk Allocation ───────────────────────────────────
    portfolio_equity: float = Field(
        default=20_000.0, description="Total account portfolio equity in INR"
    )
    risk_percent: float = Field(
        default=1.0,
        description="1R percentage of equity risked per trade (1.0% = ₹200 on ₹20k)",
    )
    max_capital_per_trade: float = Field(
        default=30_000.0,
        description="Hard cap on notional capital allocated per trade (1.5x leverage ceiling)",
    )
    max_daily_loss: float = Field(
        default=600.0,
        description="Cumulative realized + unrealized loss circuit kill-switch (-3% of account)",
    )
    max_open_positions: int = Field(
        default=1,
        description="Maximum concurrent open positions (single-position discipline)",
    )
    max_daily_trades: int = Field(
        default=5, description="Maximum completed trades per calendar session"
    )

    # ── Time Boundaries (IST) ────────────────────────────────────────
    warmup_end_time: str = Field(
        default="09:30",
        description="Warm-up period end (HH:MM). Ingest ticks only before this",
    )
    no_entry_after: str = Field(
        default="15:00", description="Cutoff time for opening new positions (HH:MM)"
    )
    square_off_time: str = Field(
        default="15:15", description="Hard mandatory intraday square-off time (HH:MM)"
    )

    # ── Statutory & Transaction Cost Rates (NSE Cash Intraday MIS) ──
    flat_brokerage_per_order: float = Field(
        default=20.0, description="Flat brokerage charged per executed order in INR"
    )
    stt_rate_sell: float = Field(
        default=0.00025,
        description="Securities Transaction Tax: 0.025% on sell turnover",
    )
    exchange_turnover_rate: float = Field(
        default=0.0000297, description="NSE turnover fee: 0.00297% on both buy & sell (SEBI True-to-Label)"
    )
    sebi_turnover_rate: float = Field(
        default=0.000001, description="SEBI charge: ₹10 per crore (0.0001%)"
    )
    stamp_duty_rate_buy: float = Field(
        default=0.00003, description="Stamp duty: 0.003% on buy turnover"
    )
    gst_rate: float = Field(
        default=0.18, description="GST: 18% applied on (Brokerage + Exchange + SEBI)"
    )

    # ── Friction Guard Criteria ─────────────────────────────────────
    min_turnover_threshold: float = Field(
        default=10_000.0,
        description="Minimum turnover in INR to contain percentage drag",
    )
    min_profit_friction_multiple: float = Field(
        default=3.5, description="Expected profit must be >= N * estimated friction"
    )

    # ── Alpha & Strategy Controls ───────────────────────────────────
    min_confluence: int = Field(
        default=2,
        description="Minimum distinct strategy families required to trigger entry",
    )
    min_risk_reward: float = Field(
        default=1.8, description="Minimum theoretical reward-to-risk ratio"
    )
    min_stop_loss_percent: float = Field(
        default=1.0, description="Minimum safe SL width (%) to avoid market noise"
    )
    trailing_sl_atr_multiplier: float = Field(
        default=2.2,
        description="Trailing stop-loss ATR distance multiplier (widened from 1.5x)",
    )
    breakeven_trigger_r: float = Field(
        default=1.0,
        description="Profit in R units required before moving SL to Breakeven",
    )
    trailing_trigger_r: float = Field(
        default=1.0,
        description="Profit in R units required before activating dynamic ATR trail",
    )

    # ── Watchlist ───────────────────────────────────────────────────
    watchlist_raw: str = Field(
        default="PAYTM,ATHERENERG,SHREECEM,PIIND,MCX,PFC,BOSCHLTD,KAYNES,ADANIENSOL,IDEA",
        alias="WATCHLIST",
        description="High-momentum F&O equities, excluding static low-winrate names (e.g. SOLARINDS)",
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("paper", "live"):
            raise ValueError(f"Invalid mode '{v}'. Must be either 'paper' or 'live'.")
        return clean

    @property
    def watchlist(self) -> List[str]:
        """Parsed list of uppercase tradingsymbols."""
        return [
            sym.strip().upper() for sym in self.watchlist_raw.split(",") if sym.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton instance of Settings."""
    return Settings()
