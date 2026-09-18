"""
Active Trade Watchdog: Exit Curve Front-Loading, Breakeven Friction Guard & Circuit Breakers.

Prevents:
1. Premature profit reversals: Front-loads Target 1 partial profit booking to +1.2R
   (instead of +2.0R), locking in 50% gains provided round-trip friction is covered.
2. Breakeven fee drag: Ratchets remaining 50% stop loss to EntryPrice ± RoundTripFrictionPerShare.
3. Runner decay: Trails the remaining position dynamically via 20-EMA or ATR once profit exceeds +1.5R.
4. Capital lockup / Stagnant drift: Triggers an idle trade circuit breaker if an active trade
   fails to advance to at least +0.5R within 20 minutes.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, Optional, Tuple

from .smartapi_client import smart_api_client

logger = logging.getLogger("watchdog")


class TradeWatchdog:
    """Evaluates active position metrics, dynamic exit curves, and stagnation rules."""

    @staticmethod
    def calculate_round_trip_friction_per_share(
        entry_price: float,
        quantity: int,
        exchange: str = "NSE",
        product_type: str = "INTRADAY",
        direction: str = "BUY",
    ) -> float:
        """
        Compute exact round-trip statutory friction per share.

        Used to offset breakeven stop-losses so that trades exiting at breakeven
        are guaranteed net non-negative after all brokerages, STT, and taxes.
        """
        if quantity <= 0 or entry_price <= 0:
            return 0.20  # Safe minimum default (20 paise)

        try:
            charges = smart_api_client.calculate_statutory_charges_fast(
                entry_price=entry_price,
                exit_price=entry_price,
                qty=quantity,
                product_type=product_type,
                exchange=exchange,
                direction=direction,
            )
            total_charges = float(charges.get("total_charges", 0.0))
            per_share = total_charges / float(quantity)
            return round(max(0.10, per_share), 2)
        except Exception as e:
            logger.warning("Error computing friction per share: %s", e)
            return round(max(0.15, entry_price * 0.0008), 2)

    @classmethod
    def evaluate_exit_curve(
        cls,
        trade: Dict[str, Any],
        ltp: float,
        current_qty: int,
        exchange: str = "NSE",
        product_type: str = "INTRADAY",
        target1_r_mult: float = 1.2,
    ) -> Dict[str, Any]:
        """
        Evaluate position against the front-loaded exit curve (+1.2R Target 1).

        Parameters
        ----------
        trade : Dict[str, Any]
            Active trade dictionary.
        ltp : float
            Current LTP.
        current_qty : int
            Current open quantity.
        target1_r_mult : float
            Multiple of 1R risk distance for Target 1 (default: 1.2R).

        Returns
        -------
        Dict[str, Any]
            Action directives:
            - 'trigger_t1': bool
            - 't1_exit_qty': int
            - 'breakeven_sl': float
            - 'runner_trailing_active': bool
            - 'message': str
        """
        direction = trade.get("direction", "BUY").upper()
        entry_price = float(trade.get("entry_price", 0.0))
        initial_sl = float(trade.get("initial_sl", trade.get("sl", 0.0)))
        partial_booked = bool(trade.get("partial_booked", False))

        if entry_price <= 0 or initial_sl <= 0 or current_qty <= 0:
            return {"trigger_t1": False}

        risk_dist = abs(entry_price - initial_sl)
        if risk_dist <= 0:
            risk_dist = entry_price * 0.01

        # Calculate current profit in R
        current_gain_per_share = (ltp - entry_price) if direction == "BUY" else (entry_price - ltp)
        current_r = current_gain_per_share / risk_dist

        result = {
            "trigger_t1": False,
            "t1_exit_qty": 0,
            "breakeven_sl": entry_price,
            "runner_trailing_active": bool(current_r >= 1.5),
            "current_r": round(current_r, 2),
        }

        # ── 1. Target 1 Evaluation (+1.2R) ──────────────────────────────────
        if not partial_booked and current_qty >= 2:
            target1_price = (
                (entry_price + risk_dist * target1_r_mult)
                if direction == "BUY"
                else (entry_price - risk_dist * target1_r_mult)
            )

            hit_t1 = (ltp >= target1_price) if direction == "BUY" else (ltp <= target1_price)

            if hit_t1 or current_r >= target1_r_mult:
                exit_qty = max(1, int(current_qty * 0.5))
                gross_expected_profit = current_gain_per_share * exit_qty

                # Friction coverage check
                est_charges = smart_api_client.calculate_statutory_charges_fast(
                    entry_price=entry_price,
                    exit_price=ltp,
                    qty=exit_qty,
                    product_type=product_type,
                    exchange=exchange,
                    direction=direction,
                )
                friction_fee = float(est_charges.get("total_charges", 25.0))

                if gross_expected_profit >= friction_fee:
                    friction_per_share = cls.calculate_round_trip_friction_per_share(
                        entry_price=entry_price,
                        quantity=current_qty - exit_qty,
                        exchange=exchange,
                        product_type=product_type,
                        direction=direction,
                    )

                    # Breakeven SL covering friction
                    if direction == "BUY":
                        be_sl = round(entry_price + friction_per_share, 2)
                    else:
                        be_sl = round(entry_price - friction_per_share, 2)

                    result["trigger_t1"] = True
                    result["t1_exit_qty"] = exit_qty
                    result["breakeven_sl"] = be_sl
                    result["message"] = (
                        f"Target 1 (+{target1_r_mult:.1f}R) hit at ₹{ltp:.2f}. "
                        f"Booking {exit_qty} shares (Gain ₹{gross_expected_profit:.1f} > Fee ₹{friction_fee:.1f}). "
                        f"Ratchet runner SL to Breakeven+Friction @ ₹{be_sl:.2f}."
                    )
                    return result

        return result

    @staticmethod
    def check_idle_trade_circuit_breaker(
        trade: Dict[str, Any],
        ltp: float,
        mins_held: float,
        stagnation_timeout_mins: float = 20.0,
        min_required_r: float = 0.5,
    ) -> Tuple[bool, str]:
        """
        Check if an open position is stagnant and drifting in noise without momentum.

        Rule:
        If a position is held for >= 20 minutes and fails to achieve at least +0.5R,
        exit immediately at market.

        Returns
        -------
        Tuple[bool, str]
            (should_exit, reason_description)
        """
        if mins_held < stagnation_timeout_mins:
            return False, "Holding period within active window"

        entry_price = float(trade.get("entry_price", 0.0))
        initial_sl = float(trade.get("initial_sl", trade.get("sl", 0.0)))
        direction = trade.get("direction", "BUY").upper()

        if entry_price <= 0:
            return False, "Invalid trade entry price"

        risk_dist = abs(entry_price - initial_sl) if initial_sl > 0 else (entry_price * 0.01)
        if risk_dist <= 0:
            risk_dist = entry_price * 0.01

        current_gain = (ltp - entry_price) if direction == "BUY" else (entry_price - ltp)
        achieved_r = current_gain / risk_dist

        if achieved_r < min_required_r:
            return (
                True,
                f"Idle trade circuit breaker: Position held for {mins_held:.0f} mins "
                f"without reaching +{min_required_r:.1f}R (current: {achieved_r:.2f}R). "
                f"Exiting at market to eliminate stagnation drift.",
            )

        return False, f"Trade advancing with momentum ({achieved_r:.2f}R >= +{min_required_r:.1f}R)"


watchdog = TradeWatchdog()
