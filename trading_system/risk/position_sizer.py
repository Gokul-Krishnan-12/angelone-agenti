"""
Quantitative Position Sizing Engine.
Implements 1R Fixed-Fractional Volatility Parity sizing with strict boundary clamping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from loguru import logger

from ..config.settings import Settings, get_settings


@dataclass(frozen=True)
class PositionSizeResult:
    """Calculated position sizing output and allocation metrics."""

    quantity: int
    risk_budget: float
    per_share_risk: float
    notional_allocation: float
    round_trip_turnover: float
    is_valid: bool
    rejection_reason: str


class PositionSizer:
    """
    Computes volatility-adjusted position size based on 1R risk budget.
    Guarantees that a full stop-out loss equals exactly 1R (e.g. 1% of portfolio equity).
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def calculate_size(
        self,
        entry_price: float,
        stop_loss: float,
        portfolio_equity: float | None = None,
    ) -> Tuple[int, PositionSizeResult]:
        """
        Calculate 1R volatility parity position size.

        Parameters
        ----------
        entry_price : float
            Projected entry limit price.
        stop_loss : float
            Initial hard structural stop-loss price.
        portfolio_equity : float, optional
            Current account equity in INR (defaults to settings.portfolio_equity).

        Returns
        -------
        Tuple[int, PositionSizeResult]
            (quantity, details)
        """
        equity = (
            portfolio_equity
            if portfolio_equity is not None
            else self.settings.portfolio_equity
        )
        risk_pct = self.settings.risk_percent / 100.0  # e.g., 1.0% -> 0.01
        risk_budget = round(equity * risk_pct, 2)
        per_share_risk = round(abs(entry_price - stop_loss), 2)

        # Pre-validation
        if entry_price <= 0 or stop_loss <= 0 or per_share_risk <= 0:
            res = PositionSizeResult(
                quantity=0,
                risk_budget=risk_budget,
                per_share_risk=per_share_risk,
                notional_allocation=0.0,
                round_trip_turnover=0.0,
                is_valid=False,
                rejection_reason="Invalid price levels (entry, SL <= 0 or entry == SL)",
            )
            return 0, res

        # 1R Volatility Parity Formula
        raw_quantity = math.floor(risk_budget / per_share_risk)

        if raw_quantity <= 0:
            res = PositionSizeResult(
                quantity=0,
                risk_budget=risk_budget,
                per_share_risk=per_share_risk,
                notional_allocation=0.0,
                round_trip_turnover=0.0,
                is_valid=False,
                rejection_reason=(
                    f"Calculated 0 quantity (risk budget ₹{risk_budget:.2f} < "
                    f"per-share risk ₹{per_share_risk:.2f})"
                ),
            )
            logger.info("PositionSizer: %s", res.rejection_reason)
            return 0, res

        # Bounds Check: Cap by maximum nominal capital per trade
        max_allocation = self.settings.max_capital_per_trade
        max_allowed_shares = math.floor(max_allocation / entry_price)
        final_quantity = min(raw_quantity, max_allowed_shares)

        notional_allocation = round(final_quantity * entry_price, 2)
        round_trip_turnover = round(notional_allocation * 2.0, 2)

        # Hard guard: Drop signal if quantity clamped to 0 or turnover below statutory threshold
        if final_quantity <= 0:
            res = PositionSizeResult(
                quantity=0,
                risk_budget=risk_budget,
                per_share_risk=per_share_risk,
                notional_allocation=0.0,
                round_trip_turnover=0.0,
                is_valid=False,
                rejection_reason=(
                    f"Quantity capped to 0 by max capital per trade ₹{max_allocation:,.2f} "
                    f"(stock price ₹{entry_price:.2f} exceeds allocation)"
                ),
            )
            logger.warning("PositionSizer: %s", res.rejection_reason)
            return 0, res

        if round_trip_turnover < self.settings.min_turnover_threshold:
            res = PositionSizeResult(
                quantity=0,
                risk_budget=risk_budget,
                per_share_risk=per_share_risk,
                notional_allocation=notional_allocation,
                round_trip_turnover=round_trip_turnover,
                is_valid=False,
                rejection_reason=(
                    f"Turnover ₹{round_trip_turnover:,.2f} below statutory threshold "
                    f"₹{self.settings.min_turnover_threshold:,.2f}. Dropping signal to prevent fee drag."
                ),
            )
            logger.warning("PositionSizer: %s", res.rejection_reason)
            return 0, res

        res = PositionSizeResult(
            quantity=final_quantity,
            risk_budget=risk_budget,
            per_share_risk=per_share_risk,
            notional_allocation=notional_allocation,
            round_trip_turnover=round_trip_turnover,
            is_valid=True,
            rejection_reason="",
        )
        logger.info(
            f"PositionSizer approved: {final_quantity} shares @ ₹{entry_price:.2f} "
            f"(Turnover ₹{round_trip_turnover:,.2f}, 1R Risk ₹{per_share_risk * final_quantity:.2f})"
        )
        return final_quantity, res
