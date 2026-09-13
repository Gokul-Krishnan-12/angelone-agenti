"""
Two-Legged Native Exchange Order Router.
Submits aggressive limit entry orders and immediately places native exchange STOPLOSS_LIMIT orders.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from loguru import logger
from SmartApi import SmartConnect

from ..config.settings import Settings, get_settings
from ..strategies.base import Signal


@dataclass
class ActiveTrade:
    """State of an active executing trade with an exchange-side stop-loss trigger order."""

    trade_id: str
    tradingsymbol: str
    token: str
    direction: str  # 'BUY' or 'SELL'
    quantity: int
    entry_price: float
    current_sl: float
    initial_sl: float
    target_price: float
    entry_order_id: str
    sl_order_id: str  # Exchange-side STOPLOSS_LIMIT order ID
    hwm: float  # High Water Mark for BUY
    lwm: float  # Low Water Mark for SELL
    atr: float
    entry_time: datetime.datetime
    status: str = "OPEN"  # OPEN, PARTIAL_CLOSED, CLOSED
    partial_booked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderRouter:
    """
    Executes trades through Angel One SmartAPI using native exchange STOPLOSS_LIMIT orders.
    Eliminates client-side memory stop-loss execution risk.
    """

    def __init__(
        self, smart_api: SmartConnect | None = None, settings: Settings | None = None
    ):
        self.settings = settings or get_settings()
        self.smart_api = smart_api
        self.active_trades: Dict[str, ActiveTrade] = {}  # tradingsymbol -> ActiveTrade

    def set_smart_api(self, client: SmartConnect):
        """Bind authenticated SmartConnect instance."""
        self.smart_api = client

    def execute_two_legged_trade(
        self, signal: Signal, token: str, quantity: int
    ) -> Optional[ActiveTrade]:
        """
        Execute two-legged native order flow:
        Leg 1: Submit aggressive LIMIT entry order.
        Leg 2: Immediately place native exchange-side STOPLOSS_LIMIT order upon entry fill.
        """
        if quantity <= 0:
            logger.warning(
                "OrderRouter: Rejected trade with quantity 0 for %s",
                signal.tradingsymbol,
            )
            return None

        symbol = signal.tradingsymbol
        direction = signal.direction
        entry_price = signal.entry_price
        sl_price = signal.stop_loss
        target_price = signal.target_price
        atr = float(signal.indicators.get("atr", 0.0))

        # Leg 1: Entry Order (Aggressive Limit to cross spread)
        spread_cushion = 0.0005  # 0.05%
        if direction == "BUY":
            entry_limit = round(entry_price * (1.0 + spread_cushion), 2)
            entry_tx = "BUY"
            exit_tx = "SELL"
        else:
            entry_limit = round(entry_price * (1.0 - spread_cushion), 2)
            entry_tx = "SELL"
            exit_tx = "BUY"

        trade_id = str(uuid.uuid4())[:8]

        # Dispatch Entry Order
        entry_order_id = self._place_entry_order(
            tradingsymbol=symbol,
            token=token,
            transaction_type=entry_tx,
            quantity=quantity,
            price=entry_limit,
        )

        if not entry_order_id:
            logger.error(
                "OrderRouter: Entry order placement failed for %s. Aborting trade.",
                symbol,
            )
            return None

        logger.success(
            "OrderRouter [Leg 1 FILL]: %s %d %s @ ₹%.2f (Order ID: %s)",
            entry_tx,
            quantity,
            symbol,
            entry_limit,
            entry_order_id,
        )

        # Leg 2: Native Exchange-Side STOPLOSS_LIMIT Order
        # SEBI has banned raw SL-M. We set limit price 0.50% beyond triggerprice to guarantee fill.
        sl_cushion = 0.0050  # 0.50%
        if exit_tx == "SELL":
            sl_trigger = round(sl_price, 2)
            sl_limit_price = round(sl_trigger * (1.0 - sl_cushion), 2)
        else:
            sl_trigger = round(sl_price, 2)
            sl_limit_price = round(sl_trigger * (1.0 + sl_cushion), 2)

        sl_order_id = self._place_stoploss_order(
            tradingsymbol=symbol,
            token=token,
            transaction_type=exit_tx,
            quantity=quantity,
            trigger_price=sl_trigger,
            limit_price=sl_limit_price,
        )

        if not sl_order_id:
            logger.critical(
                "OrderRouter [Leg 2 FAILED]: Stop-Loss order failed for %s! "
                "Executing immediate emergency market exit to prevent naked position.",
                symbol,
            )
            self.emergency_exit_position(symbol, token, quantity, exit_tx)
            return None

        logger.success(
            "OrderRouter [Leg 2 ARMED]: Placed native exchange STOPLOSS_LIMIT for %s "
            "(Trigger: ₹%.2f, Limit: ₹%.2f, Order ID: %s)",
            symbol,
            sl_trigger,
            sl_limit_price,
            sl_order_id,
        )

        active_trade = ActiveTrade(
            trade_id=trade_id,
            tradingsymbol=symbol,
            token=token,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            current_sl=sl_trigger,
            initial_sl=sl_trigger,
            target_price=target_price,
            entry_order_id=entry_order_id,
            sl_order_id=sl_order_id,
            hwm=entry_price,
            lwm=entry_price,
            atr=atr,
            entry_time=datetime.datetime.now(),
            status="OPEN",
            metadata={"strategy": signal.strategy_name, "family": signal.family},
        )
        self.active_trades[symbol] = active_trade
        return active_trade

    def _place_entry_order(
        self,
        tradingsymbol: str,
        token: str,
        transaction_type: str,
        quantity: int,
        price: float,
    ) -> str:
        """Submit Limit entry order to SmartAPI."""
        if self.settings.mode == "paper" or not self.smart_api:
            return f"SIM_ENTRY_{uuid.uuid4().hex[:6]}"

        try:
            params = {
                "variety": "NORMAL",
                "tradingsymbol": f"{tradingsymbol}-EQ",
                "symboltoken": str(token),
                "transactiontype": transaction_type,
                "exchange": "NSE",
                "ordertype": "LIMIT",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": str(round(price, 2)),
                "quantity": str(quantity),
            }
            res = self.smart_api.placeOrder(params)
            if isinstance(res, dict) and res.get("status") and res.get("data"):
                return str(res["data"].get("orderid", ""))
            elif isinstance(res, str):
                return res
        except Exception as e:
            logger.error("Error placing entry order: %s", e)
        return ""

    def _place_stoploss_order(
        self,
        tradingsymbol: str,
        token: str,
        transaction_type: str,
        quantity: int,
        trigger_price: float,
        limit_price: float,
    ) -> str:
        """Submit native exchange-side STOPLOSS_LIMIT order."""
        if self.settings.mode == "paper" or not self.smart_api:
            return f"SIM_SL_{uuid.uuid4().hex[:6]}"

        try:
            params = {
                "variety": "STOPLOSS",
                "tradingsymbol": f"{tradingsymbol}-EQ",
                "symboltoken": str(token),
                "transactiontype": transaction_type,
                "exchange": "NSE",
                "ordertype": "STOPLOSS_LIMIT",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": str(round(limit_price, 2)),
                "triggerprice": str(round(trigger_price, 2)),
                "quantity": str(quantity),
            }
            res = self.smart_api.placeOrder(params)
            if isinstance(res, dict) and res.get("status") and res.get("data"):
                return str(res["data"].get("orderid", ""))
            elif isinstance(res, str):
                return res
        except Exception as e:
            logger.error("Error placing STOPLOSS_LIMIT order: %s", e)
        return ""

    def cancel_order(self, order_id: str, variety: str = "STOPLOSS") -> bool:
        """Cancel an open exchange order."""
        if self.settings.mode == "paper" or not self.smart_api:
            return True
        try:
            res = self.smart_api.cancelOrder(order_id, variety)
            return bool(res and res.get("status"))
        except Exception as e:
            logger.error("Error cancelling order %s: %s", order_id, e)
            return False

    def emergency_exit_position(
        self,
        tradingsymbol: str,
        token: str,
        quantity: int,
        transaction_type: str,
        current_ltp: float = 0.0,
    ):
        """Execute urgent liquidation order with aggressive limit buffer."""
        buffer = 0.01  # 1.0% buffer to guarantee fill
        price = (
            round(
                current_ltp
                * (1.0 - buffer if transaction_type == "SELL" else 1.0 + buffer),
                2,
            )
            if current_ltp > 0
            else 0.0
        )
        if self.settings.mode == "paper" or not self.smart_api:
            logger.info(
                "SIMULATED EMERGENCY EXIT: %s %d %s",
                transaction_type,
                quantity,
                tradingsymbol,
            )
            return

        try:
            params = {
                "variety": "NORMAL",
                "tradingsymbol": f"{tradingsymbol}-EQ",
                "symboltoken": str(token),
                "transactiontype": transaction_type,
                "exchange": "NSE",
                "ordertype": "LIMIT" if price > 0 else "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": str(price) if price > 0 else "0",
                "quantity": str(quantity),
            }
            self.smart_api.placeOrder(params)
            logger.warning(
                "Emergency exit order dispatched for %s (%s)",
                tradingsymbol,
                transaction_type,
            )
        except Exception as e:
            logger.critical("Failed emergency liquidation for %s: %s", tradingsymbol, e)
