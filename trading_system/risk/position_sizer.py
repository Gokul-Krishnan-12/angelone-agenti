"""
Quantitative Position Sizing Engine.
Implements 1R Fixed-Fractional Volatility Parity sizing with strict boundary clamping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from loguru import logger

from ..config.settings import Settings, get_settings
from .friction_guard import FrictionBreakdown, FrictionGuard


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
    friction_breakdown: Optional[FrictionBreakdown] = None


class PositionSizer:
    """
    Computes volatility-adjusted position size based on 1R risk budget.
    Guarantees that a full stop-out loss equals exactly 1R (e.g. 1.0% to 1.5% of account equity)
    and enforces an MIS leverage ceiling of 1.5x (₹30,000 max on ₹20,000 capital).
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.friction_guard = FrictionGuard(self.settings)

    def calculate_size(
        self,
        entry_price: float,
        stop_loss: float,
        target_price: float | None = None,
        portfolio_equity: float | None = None,
    ) -> Tuple[int, PositionSizeResult]:
        """
        Calculate 1R volatility parity position size with statutory friction guard.

        Parameters
        ----------
        entry_price : float
            Projected entry limit price.
        stop_loss : float
            Initial hard structural stop-loss price.
        target_price : float, optional
            Expected take-profit price for payoff ratio validation.
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
        # Strictly clamp risk percent between 1.0% and 1.5%
        risk_pct = max(0.01, min(0.015, self.settings.risk_percent / 100.0))
        risk_budget = round(equity * risk_pct, 2)
        per_share_risk = round(abs(entry_price - stop_loss), 2)

        # 1. Pre-validation
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

        # 2. Fixed-Fractional 1R Risk Sizing Formula
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
                    f"Calculated 0 quantity: risk budget ₹{risk_budget:.2f} < "
                    f"per-share risk ₹{per_share_risk:.2f}"
                ),
            )
            logger.info("PositionSizer: %s", res.rejection_reason)
            return 0, res

        # 3. Leverage Cap: 1.5x of equity (max ₹30,000 for ₹20k account)
        max_leverage_capital = round(equity * 1.5, 2)
        max_allocation = min(self.settings.max_capital_per_trade, max_leverage_capital)
        max_allowed_shares = math.floor(max_allocation / entry_price)
        final_quantity = min(raw_quantity, max_allowed_shares)

        notional_allocation = round(final_quantity * entry_price, 2)
        round_trip_turnover = round(notional_allocation * 2.0, 2)

        if final_quantity <= 0:
            res = PositionSizeResult(
                quantity=0,
                risk_budget=risk_budget,
                per_share_risk=per_share_risk,
                notional_allocation=0.0,
                round_trip_turnover=0.0,
                is_valid=False,
                rejection_reason=(
                    f"Quantity capped to 0 by max capital limit ₹{max_allocation:,.2f} "
                    f"(stock price ₹{entry_price:.2f} exceeds allocation)"
                ),
            )
            logger.warning("PositionSizer: %s", res.rejection_reason)
            return 0, res

        # 4. Statutory Friction & Turnover Guard
        breakdown = self.friction_guard.calculate_round_trip_friction(
            entry_price=entry_price,
            exit_price=target_price if target_price else entry_price,
            quantity=final_quantity,
        )

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
                    f"₹{self.settings.min_turnover_threshold:,.2f} (drag {breakdown.friction_pct:.2f}%)."
                ),
                friction_breakdown=breakdown,
            )
            logger.warning("PositionSizer: %s", res.rejection_reason)
            return 0, res

        # 5. Friction Payoff Multiple Gate: Expected gain must be >= 3.5x friction
        if target_price and target_price > 0:
            expected_gain = round(abs(target_price - entry_price) * final_quantity, 2)
            required_gain = round(
                breakdown.total_friction * self.settings.min_profit_friction_multiple, 2
            )
            if expected_gain < required_gain:
                res = PositionSizeResult(
                    quantity=0,
                    risk_budget=risk_budget,
                    per_share_risk=per_share_risk,
                    notional_allocation=notional_allocation,
                    round_trip_turnover=round_trip_turnover,
                    is_valid=False,
                    rejection_reason=(
                        f"Expected gain ₹{expected_gain:.2f} < {self.settings.min_profit_friction_multiple}x "
                        f"friction (₹{breakdown.total_friction:.2f} friction requires >= ₹{required_gain:.2f})"
                    ),
                    friction_breakdown=breakdown,
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
            friction_breakdown=breakdown,
        )
        logger.info(
            f"PositionSizer approved: {final_quantity} shares @ ₹{entry_price:.2f} "
            f"(Turnover ₹{round_trip_turnover:,.2f}, 1R Risk ₹{per_share_risk * final_quantity:.2f}, "
            f"Est. Friction ₹{breakdown.total_friction:.2f})"
        )
        return final_quantity, res
