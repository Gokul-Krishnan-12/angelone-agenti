"""
Statutory Indian Market Friction Calculator & Pre-Trade Friction Guard.
Evaluates exact transaction friction for NSE Cash Intraday MIS trades.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from loguru import logger

from ..config.settings import Settings, get_settings


@dataclass(frozen=True)
class FrictionBreakdown:
    """Itemized breakdown of Indian regulatory and broker charges for a round-trip trade."""

    buy_turnover: float
    sell_turnover: float
    total_turnover: float
    brokerage: float
    stt: float
    exchange_fee: float
    sebi_charge: float
    stamp_duty: float
    gst: float
    total_friction: float
    friction_pct: float  # Friction as percentage of total turnover


class FrictionGuard:
    """
    Computes pre-trade transaction friction and prevents negative-expectancy execution
    due to commission drag, regulatory taxes, or small notional turnover.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def calculate_round_trip_friction(
        self,
        entry_price: float,
        exit_price: float,
        quantity: int,
        orders_count: int = 2,
    ) -> FrictionBreakdown:
        """
        Calculate complete statutory taxes, exchange fees, and brokerage for an intraday round-trip.

        Parameters
        ----------
        entry_price : float
            Fill price on the entry leg.
        exit_price : float
            Expected or executed price on the exit leg.
        quantity : int
            Number of shares traded.
        orders_count : int, default=2
            Number of order executions (2 for single entry + exit; 3 if partial profit booking).
        """
        s = self.settings
        qty = abs(quantity)
        buy_turnover = round(entry_price * qty, 2)
        sell_turnover = round(exit_price * qty, 2)
        total_turnover = round(buy_turnover + sell_turnover, 2)

        # 1. Brokerage: Flat ₹20 per executed order
        brokerage = round(orders_count * s.flat_brokerage_per_order, 2)

        # 2. STT: 0.025% on sell-side turnover (equity intraday)
        stt = round(sell_turnover * s.stt_rate_sell, 2)

        # 3. NSE Exchange Turnover Fee: 0.00325% on both buy & sell
        exchange_fee = round(total_turnover * s.exchange_turnover_rate, 2)

        # 4. SEBI Turnover Charge: ₹10 per crore (0.0001%) on both buy & sell
        sebi_charge = round(total_turnover * s.sebi_turnover_rate, 2)

        # 5. Stamp Duty: 0.003% on buy turnover only
        stamp_duty = round(buy_turnover * s.stamp_duty_rate_buy, 2)

        # 6. GST: 18% on (Brokerage + Exchange Turnover Fee + SEBI Charge)
        taxable_services = brokerage + exchange_fee + sebi_charge
        gst = round(taxable_services * s.gst_rate, 2)

        total_friction = round(
            brokerage + stt + exchange_fee + sebi_charge + stamp_duty + gst, 2
        )
        friction_pct = round(
            (total_friction / total_turnover * 100.0) if total_turnover > 0 else 0.0, 4
        )

        return FrictionBreakdown(
            buy_turnover=buy_turnover,
            sell_turnover=sell_turnover,
            total_turnover=total_turnover,
            brokerage=brokerage,
            stt=stt,
            exchange_fee=exchange_fee,
            sebi_charge=sebi_charge,
            stamp_duty=stamp_duty,
            gst=gst,
            total_friction=total_friction,
            friction_pct=friction_pct,
        )

    def validate_trade(
        self,
        entry_price: float,
        target_price: float,
        quantity: int,
    ) -> Tuple[bool, str, FrictionBreakdown]:
        """
        Validate whether the trade passes the pre-trade statutory friction gates:
        1. Minimum turnover threshold (default: ₹35,000 total turnover).
        2. Minimum expected profit multiple (expected gain >= 3.0 * total friction).

        Returns
        -------
        Tuple[bool, str, FrictionBreakdown]
            (is_approved, reason_message, friction_breakdown)
        """
        if quantity <= 0 or entry_price <= 0 or target_price <= 0:
            dummy = self.calculate_round_trip_friction(1.0, 1.0, 1)
            return (
                False,
                "Invalid trade parameters (quantity, entry, or target <= 0)",
                dummy,
            )

        breakdown = self.calculate_round_trip_friction(
            entry_price=entry_price,
            exit_price=target_price,
            quantity=quantity,
            orders_count=2,
        )

        # Gate 1: Turnover threshold check
        if breakdown.total_turnover < self.settings.min_turnover_threshold:
            msg = (
                f"REJECTED by FrictionGuard: Turnover ₹{breakdown.total_turnover:,.2f} "
                f"below required ₹{self.settings.min_turnover_threshold:,.2f} threshold "
                f"(friction would be {breakdown.friction_pct:.2f}% of capital)"
            )
            logger.warning(msg)
            return False, msg, breakdown

        # Gate 2: Expected gross profit vs. friction multiple
        expected_profit = round(abs(target_price - entry_price) * quantity, 2)
        required_profit = round(
            breakdown.total_friction * self.settings.min_profit_friction_multiple, 2
        )

        if expected_profit < required_profit:
            msg = (
                f"REJECTED by FrictionGuard: Expected profit ₹{expected_profit:,.2f} "
                f"is less than {self.settings.min_profit_friction_multiple}x estimated friction "
                f"(₹{breakdown.total_friction:,.2f} friction requires >= ₹{required_profit:,.2f} gain)"
            )
            logger.warning(msg)
            return False, msg, breakdown

        net_expectancy = round(expected_profit - breakdown.total_friction, 2)
        success_msg = (
            f"PASSED FrictionGuard: Turnover ₹{breakdown.total_turnover:,.2f}, "
            f"Friction ₹{breakdown.total_friction:.2f} ({breakdown.friction_pct:.2f}%), "
            f"Expected Net Gain ₹{net_expectancy:,.2f}"
        )
        logger.debug(success_msg)
        return True, success_msg, breakdown
