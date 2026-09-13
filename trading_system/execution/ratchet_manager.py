"""
Live Trailing Stop-Loss Ratchet & Target Manager.
Modifies native exchange-side trigger orders as price reaches +1.0R and +1.5R profit cushions.
"""

from __future__ import annotations

from typing import Callable, Optional

from loguru import logger
from SmartApi import SmartConnect

from ..config.settings import Settings, get_settings
from .order_router import ActiveTrade, OrderRouter


class RatchetManager:
    """
    Monitors live ticks for active trades, updates High/Low Water Marks,
    and transmits exchange `modifyOrder` calls to tighten native stop-losses.
    """

    def __init__(
        self,
        order_router: OrderRouter,
        smart_api: SmartConnect | None = None,
        settings: Settings | None = None,
        on_trade_closed: Optional[Callable[[ActiveTrade, float, str], None]] = None,
    ):
        self.order_router = order_router
        self.smart_api = smart_api or order_router.smart_api
        self.settings = settings or get_settings()
        self.on_trade_closed = on_trade_closed

    def update_with_tick(self, token: str, symbol: str, ltp: float):
        """
        Process incoming tick for any open position in this scrip.
        """
        trade = self.order_router.active_trades.get(symbol)
        if not trade or trade.status != "OPEN":
            return

        direction = trade.direction
        entry = trade.entry_price
        initial_risk = abs(entry - trade.initial_sl)
        if initial_risk <= 0:
            return

        # 1. Target Check
        hit_target = False
        if direction == "BUY" and ltp >= trade.target_price:
            hit_target = True
        elif direction == "SELL" and ltp <= trade.target_price:
            hit_target = True

        if hit_target:
            logger.success(
                "🎯 TARGET REACHED for %s at ₹%.2f (Target: ₹%.2f)",
                symbol,
                ltp,
                trade.target_price,
            )
            self._close_position_with_target(trade, ltp)
            return

        # 2. Update High / Low Water Mark
        if direction == "BUY":
            trade.hwm = max(trade.hwm, ltp)
            gain_in_r = (trade.hwm - entry) / initial_risk
        else:
            trade.lwm = min(trade.lwm, ltp)
            gain_in_r = (entry - trade.lwm) / initial_risk

        # 3. Dynamic Stop-Loss Ratchet Evaluation
        # Position MUST advance at least +1.0R into profit before trailing activates.
        if gain_in_r < self.settings.breakeven_trigger_r:
            return

        new_sl: Optional[float] = None
        atr = trade.atr if trade.atr > 0 else (entry * 0.015)
        distance = round(atr * self.settings.trailing_sl_atr_multiplier, 2)

        if direction == "BUY":
            # Ratchet candidate: at least breakeven, trailing 2.2x ATR below High Water Mark
            candidate_sl = round(max(entry, trade.hwm - distance), 2)
            if candidate_sl > trade.current_sl:
                new_sl = candidate_sl
        else:
            # Ratchet candidate: at least breakeven, trailing 2.2x ATR above Low Water Mark
            candidate_sl = round(min(entry, trade.lwm + distance), 2)
            if candidate_sl < trade.current_sl:
                new_sl = candidate_sl

        # If a tighter stop-loss has been calculated, transmit modifyOrder to exchange
        if new_sl is not None and new_sl != trade.current_sl:
            self._modify_exchange_stoploss(trade, new_sl)

    def _modify_exchange_stoploss(self, trade: ActiveTrade, new_sl_trigger: float):
        """Transmit native modifyOrder payload to SmartAPI."""
        old_sl = trade.current_sl
        direction = trade.direction
        sl_cushion = 0.0050  # 0.50% limit cushion

        # Calculate limit price with cushion
        if direction == "BUY":
            # Exit leg is SELL: limit price is below trigger price
            new_limit_price = round(new_sl_trigger * (1.0 - sl_cushion), 2)
        else:
            # Exit leg is BUY: limit price is above trigger price
            new_limit_price = round(new_sl_trigger * (1.0 + sl_cushion), 2)

        logger.info(
            "Ratcheting native exchange SL for %s: ₹%.2f ──► ₹%.2f (HWM: ₹%.2f, Limit: ₹%.2f)",
            trade.tradingsymbol,
            old_sl,
            new_sl_trigger,
            trade.hwm if direction == "BUY" else trade.lwm,
            new_limit_price,
        )

        success = True
        if self.settings.mode != "paper" and self.smart_api and trade.sl_order_id:
            try:
                params = {
                    "variety": "STOPLOSS",
                    "orderid": trade.sl_order_id,
                    "ordertype": "STOPLOSS_LIMIT",
                    "producttype": "INTRADAY",
                    "duration": "DAY",
                    "price": str(new_limit_price),
                    "triggerprice": str(new_sl_trigger),
                    "quantity": str(trade.quantity),
                }
                res = self.smart_api.modifyOrder(params)
                if not (res and res.get("status")):
                    logger.warning("SmartAPI modifyOrder returned error: %s", res)
                    success = False
            except Exception as e:
                logger.error("Failed to modify exchange stop-loss order: %s", e)
                success = False

        if success:
            trade.current_sl = new_sl_trigger

    def _close_position_with_target(self, trade: ActiveTrade, exit_price: float):
        """Cancel open STOPLOSS_LIMIT order and liquidate position to capture profit."""
        trade.status = "CLOSED"
        symbol = trade.tradingsymbol
        exit_tx = "SELL" if trade.direction == "BUY" else "BUY"

        # 1. Cancel active exchange trigger order
        if trade.sl_order_id:
            self.order_router.cancel_order(trade.sl_order_id, variety="STOPLOSS")

        # 2. Submit target liquidation order
        self.order_router.emergency_exit_position(
            tradingsymbol=symbol,
            token=trade.token,
            quantity=trade.quantity,
            transaction_type=exit_tx,
            current_ltp=exit_price,
        )

        # 3. Calculate trade P&L
        pnl = (
            (exit_price - trade.entry_price) * trade.quantity
            if trade.direction == "BUY"
            else (trade.entry_price - exit_price) * trade.quantity
        )
        logger.success(
            "Trade completed for %s (%s): Entry ₹%.2f ──► Exit ₹%.2f | P&L: +₹%.2f",
            symbol,
            trade.direction,
            trade.entry_price,
            exit_price,
            pnl,
        )

        # Remove from active trades registry
        self.order_router.active_trades.pop(symbol, None)

        if self.on_trade_closed:
            self.on_trade_closed(trade, pnl, "TARGET")
