"""
Circuit Breaker, Session Time Gatekeeper, and Emergency Kill Switch.
Enforces institutional risk boundaries and automated intraday square-off.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, Tuple

from loguru import logger

from ..config.settings import Settings, get_settings


class CircuitBreaker:
    """
    Central risk gatekeeper managing daily drawdown kill switches,
    position counts, and Indian market trading session time boundaries.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.realized_pnl: float = 0.0
        self.unrealized_pnl: float = 0.0
        self.completed_trades_count: int = 0
        self.is_circuit_locked: bool = False
        self.lock_reason: str = ""
        self._last_reset_date: datetime.date = datetime.date.today()

    @property
    def total_pnl(self) -> float:
        """Cumulative day P&L (realized + unrealized)."""
        return round(self.realized_pnl + self.unrealized_pnl, 2)

    def _check_and_reset_day(self):
        """Automatically reset day statistics at the start of a new calendar day."""
        today = datetime.date.today()
        if today != self._last_reset_date:
            logger.info("New calendar session detected. Resetting daily risk metrics.")
            self.realized_pnl = 0.0
            self.unrealized_pnl = 0.0
            self.completed_trades_count = 0
            self.is_circuit_locked = False
            self.lock_reason = ""
            self._last_reset_date = today

    def update_pnl(self, realized_delta: float = 0.0, current_unrealized: float = 0.0):
        """Update P&L tracking and test against daily loss threshold."""
        self._check_and_reset_day()
        self.realized_pnl = round(self.realized_pnl + realized_delta, 2)
        self.unrealized_pnl = round(current_unrealized, 2)

        # Check max daily loss limit breach
        if not self.is_circuit_locked and self.total_pnl <= -abs(
            self.settings.max_daily_loss
        ):
            self.trip_circuit(
                f"Max daily loss threshold breached: Total P&L ₹{self.total_pnl:,.2f} "
                f"exceeds limit -₹{self.settings.max_daily_loss:,.2f}"
            )

    def trip_circuit(self, reason: str):
        """Trip circuit breaker lock-switch. Halts all further trade entries."""
        self.is_circuit_locked = True
        self.lock_reason = reason
        logger.critical("🛑 CIRCUIT BREAKER TRIPPED: %s", reason)

    def record_trade_completion(self, pnl: float):
        """Record completed trade and increment daily counter."""
        self._check_and_reset_day()
        self.completed_trades_count += 1
        self.update_pnl(realized_delta=pnl, current_unrealized=0.0)

    def can_open_new_trade(
        self, current_open_positions: int, current_time: datetime.time | None = None
    ) -> Tuple[bool, str]:
        """
        Evaluate if a new trade order can be submitted right now.

        Enforces:
        1. Circuit Breaker lock status
        2. Session time window: Warm-up (09:15-09:30) & Entry cutoff (15:00)
        3. Max open positions threshold
        4. Max daily trades counter
        """
        self._check_and_reset_day()

        if self.is_circuit_locked:
            return False, f"Engine Locked: {self.lock_reason}"

        now = (
            current_time if current_time is not None else datetime.datetime.now().time()
        )

        # Parse session boundaries
        warmup_time = datetime.datetime.strptime(
            self.settings.warmup_end_time, "%H:%M"
        ).time()
        no_entry_time = datetime.datetime.strptime(
            self.settings.no_entry_after, "%H:%M"
        ).time()
        market_open = datetime.time(9, 15)

        if market_open <= now < warmup_time:
            return (
                False,
                f"Warm-up phase active (09:15 to {self.settings.warmup_end_time} IST). Building indicators.",
            )

        if now >= no_entry_time:
            return (
                False,
                f"Past entry cutoff ({self.settings.no_entry_after} IST). No new positions permitted.",
            )

        if current_open_positions >= self.settings.max_open_positions:
            return (
                False,
                f"Max simultaneous positions ({self.settings.max_open_positions}) reached (Active: {current_open_positions}).",
            )

        if self.completed_trades_count >= self.settings.max_daily_trades:
            return (
                False,
                f"Daily trade limit ({self.settings.max_daily_trades}) reached for today.",
            )

        return True, "OK"

    def should_square_off(
        self, active_positions_count: int, current_time: datetime.time | None = None
    ) -> Tuple[bool, str]:
        """
        Evaluate whether the engine must execute mandatory square-off right now.

        Triggers on:
        1. Circuit breaker trip (with open positions).
        2. Reaching or passing 15:15 IST (`square_off_time`).
        """
        self._check_and_reset_day()

        if active_positions_count <= 0:
            return False, "No active positions"

        if self.is_circuit_locked:
            return True, f"Emergency Square-Off: {self.lock_reason}"

        now = (
            current_time if current_time is not None else datetime.datetime.now().time()
        )
        sq_time = datetime.datetime.strptime(
            self.settings.square_off_time, "%H:%M"
        ).time()

        if now >= sq_time:
            return (
                True,
                f"Mandatory EOD Square-Off reached ({self.settings.square_off_time} IST)",
            )

        return False, "Holding"

    def execute_emergency_kill_switch(self, order_router: Any) -> int:
        """
        Execute emergency kill switch protocol:
        1. Trip circuit breaker lock switch.
        2. Cancel all pending exchange-side STOPLOSS_LIMIT / trigger orders.
        3. Liquidate any open positions immediately via market/aggressive limit.
        4. Lock engine until the next trading session.

        Returns
        -------
        int
            Number of positions liquidated.
        """
        self.trip_circuit(
            "Emergency Kill Switch Triggered (Daily Drawdown / Capital Guard)"
        )

        if not hasattr(order_router, "emergency_square_off_all"):
            logger.error(
                "CircuitBreaker: OrderRouter missing emergency_square_off_all method"
            )
            return 0

        liquidated_count = order_router.emergency_square_off_all()
        logger.critical(
            "🛑 KILL SWITCH EXECUTED: Cancelled all open triggers, liquidated %d positions. Engine locked.",
            liquidated_count,
        )
        return liquidated_count

    def get_status(self) -> Dict[str, Any]:
        """Return snapshot of current circuit breaker state."""
        return {
            "is_locked": self.is_circuit_locked,
            "lock_reason": self.lock_reason,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_pnl": self.total_pnl,
            "completed_trades": self.completed_trades_count,
            "max_trades_allowed": self.settings.max_daily_trades,
            "max_daily_loss": self.settings.max_daily_loss,
            "single_position_lock": self.settings.max_open_positions == 1,
        }
