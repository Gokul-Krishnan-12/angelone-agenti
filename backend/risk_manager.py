import datetime
from typing import Any, Dict, Optional, Tuple

from .config import config_manager
from .market_hours import get_market_status


class RiskManager:
    def __init__(self):
        self.daily_pnl = 0.0
        self.win_count = 0
        self.loss_count = 0
        self.open_positions = 0
        self.daily_trades_count = 0
        self.current_market_ker: float = 0.0  # latest KER for the symbol being evaluated; 0.0 = unknown (safe block)

    def can_trade(self, check_market_hours: bool = True) -> Tuple[bool, str]:
        config = config_manager.get_risk_config()

        # Check market status (holiday, weekend, session hours)
        if check_market_hours and not config.get("bypassMarketHoursCheck", False):
            market_status = get_market_status()
            if not market_status["is_open"]:
                return (
                    False,
                    f"Market is closed ({market_status['display_text']})",
                )

            # Check intraday entry cutoff
            now = datetime.datetime.now().time()
            intraday_cutoff = datetime.time(15, 15)
            try:
                cfg_cutoff = datetime.datetime.strptime(
                    config.get("noNewTradesAfter", "15:00"), "%H:%M"
                ).time()
            except Exception:
                cfg_cutoff = intraday_cutoff

            effective_cutoff = min(cfg_cutoff, intraday_cutoff)
            if now >= effective_cutoff:
                return (
                    False,
                    f"Past intraday entry cutoff ({effective_cutoff.strftime('%H:%M')})",
                )

        # Check max positions
        if self.open_positions >= config.get("maxSimultaneousPositions", 5):
            return (
                False,
                f"Max simultaneous positions ({config.get('maxSimultaneousPositions', 5)}) reached",
            )

        # Check max daily loss
        if self.daily_pnl <= -config.get("maxDailyLoss", 2000):
            return (
                False,
                f"Max daily loss ({-config.get('maxDailyLoss', 2000)}) exceeded",
            )

        # Check max daily trades (8 to 10 limit to prevent overtrading)
        max_daily_trades = int(config.get("maxDailyTrades", 10))
        if self.daily_trades_count >= max_daily_trades:
            return (
                False,
                f"Daily trade limit ({max_daily_trades} trades) reached for today",
            )

        return True, "OK"

    def increment_trade(self):
        self.daily_trades_count += 1

    def reset_daily_trades(self):
        self.daily_trades_count = 0

    def calculate_position_size(self, price: float, stop_loss: float) -> int:
        """Calculate 1R risk-based position size constrained by maximum capital ceiling and 5x MIS leverage."""
        if price <= 0:
            return 0

        config = config_manager.get_risk_config()
        max_margin = float(config.get("maxCapitalPerTrade", 4000.0))
        leverage = float(config.get("leverage", 5.0))
        max_exposure = max_margin * leverage
        risk_budget = float(config.get("riskPerTrade", 500.0))

        per_share_risk = abs(price - stop_loss)
        if per_share_risk > 0 and risk_budget > 0:
            raw_quantity = int(risk_budget / per_share_risk)
            max_allowed_qty = int(max_exposure / price)
            quantity = min(raw_quantity, max_allowed_qty)
        else:
            quantity = int(max_exposure / price)

        return max(1, quantity)

    def check_daily_loss_limit(self) -> bool:
        config = config_manager.get_risk_config()
        return self.daily_pnl <= -config["maxDailyLoss"]

    def should_square_off(self) -> bool:
        config = config_manager.get_risk_config()
        now = datetime.datetime.now().time()

        # Check max daily loss first, as this should trigger regardless of time
        max_loss_hit = self.check_daily_loss_limit()

        time_to_square_off = False
        if config.get("autoSquareOff", True):
            try:
                square_off_time = datetime.datetime.strptime(
                    config.get("squareOffTime", "15:15"), "%H:%M"
                ).time()
                time_to_square_off = now >= square_off_time and now <= datetime.time(
                    15, 30
                )
            except ValueError:
                pass  # Fallback if invalid time string

        # Only square off if we have positions AND we hit max loss or time
        if self.open_positions > 0:
            return time_to_square_off or max_loss_hit

        return False

    def update_trailing_sl(
        self,
        trade: Dict[str, Any],
        ltp: float,
        atr: float,
        multiplier: float = 2.0,
        cushion_r: float = 1.0,
    ) -> Optional[float]:
        """
        Compute a new ATR trailing stop-loss if the market has moved in our favour.

        Harmonized with 1:2 R:R lifecycle:
        1. Only activates once price moves >= cushion_r * 1R (default: +1.0R) into profit.
        2. Once activated, ratchets SL to at least breakeven (entry_price).
        3. Trails multiplier * ATR (default: 2.0x ATR) behind high/low water mark.

        Parameters
        ----------
        trade       : active trade dict (must have keys: direction, sl, entry_price)
        ltp         : latest traded price
        atr         : current ATR value
        multiplier  : how many ATRs to trail behind high-water mark (default: 2.0)
        cushion_r   : minimum 1R profit threshold before trailing activates (default: 1.0)

        Returns
        -------
        float  — the new SL value if it improved (moved toward position)
        None   — if the SL should not change
        """
        if atr <= 0:
            return None

        direction = trade.get("direction", "BUY")
        current_sl = float(trade.get("sl", 0))
        entry_price = float(trade.get("entry_price", trade.get("price", ltp)))
        initial_sl = float(trade.get("initial_sl", current_sl))

        trade_risk = (
            abs(entry_price - initial_sl) if initial_sl > 0 else (entry_price * 0.012)
        )
        effective_cushion = float(trade.get("cushion_r", cushion_r))
        profit_threshold = (
            trade_risk * effective_cushion if effective_cushion > 0 else 0.0
        )
        distance = atr * multiplier

        if direction == "BUY":
            hwm = max(float(trade.get("high_water_mark", ltp)), ltp)
            trade["high_water_mark"] = hwm
            # Only activate trailing SL once trade advances at least threshold into profit
            if (hwm - entry_price) >= profit_threshold:
                # Ratchet to at least breakeven (entry_price) or hwm - distance
                new_sl = round(max(current_sl, entry_price, hwm - distance), 2)
                if new_sl > current_sl:
                    return new_sl
        else:  # SELL
            lwm = min(float(trade.get("low_water_mark", ltp)), ltp)
            trade["low_water_mark"] = lwm
            # Only activate trailing SL once trade drops at least threshold into profit
            if (entry_price - lwm) >= profit_threshold:
                # Ratchet to at least breakeven (entry_price) or lwm + distance
                new_sl = round(min(current_sl, entry_price, lwm + distance), 2)
                if new_sl < current_sl:
                    return new_sl

        return None

    def update_pnl(self, pnl: float):
        self.daily_pnl += pnl
        if pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1

    def set_open_positions(self, count: int):
        self.open_positions = count

    def set_market_ker(self, ker: float) -> None:
        """Update the latest symbol-level Kaufman Efficiency Ratio for midday chop gating.

        Called by the scanner before each confluence evaluation so that can_trade()
        uses the stock's own KER (not a global market-wide value) to decide whether
        the 11:15–13:15 midday block should apply.
        """
        self.current_market_ker = float(ker) if ker is not None else 0.0

    def get_risk_status(self) -> Dict[str, Any]:
        return {
            "daily_pnl": self.daily_pnl,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "open_positions": self.open_positions,
            "can_trade": self.can_trade()[0],
        }


risk_manager = RiskManager()
