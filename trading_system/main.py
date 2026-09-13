"""
Master Event Loop & Execution Orchestrator.
Decouples WebSocket data ingestion, real-time bar synthesis, strategy evaluation,
statutory friction checks, and two-legged native exchange execution.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Dict, List

import pandas as pd
from loguru import logger

from .config.settings import Settings, get_settings
from .core.auth import AuthManager
from .core.bar_aggregator import BarAggregator, Candle
from .core.websocket_manager import WebSocketManager
from .execution.order_router import ActiveTrade, OrderRouter
from .execution.ratchet_manager import RatchetManager
from .risk.circuit_breaker import CircuitBreaker
from .risk.friction_guard import FrictionGuard
from .risk.position_sizer import PositionSizer
from .strategies.base import ConfluenceGate
from .strategies.bollinger_expansion import BollingerExpansionStrategy
from .strategies.breakout_engine import BreakoutEngine
from .strategies.institutional_absorption import InstitutionalAbsorptionStrategy
from .strategies.institutional_fvg import InstitutionalFVGStrategy

# Configure loguru format
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)


class TradingSystemEngine:
    """
    Master event-driven orchestrator coordinating:
    WebSocket Ingestion ──► In-Memory Bar Aggregator ──► Vectorized Strategies
    ──► Confluence Gate ──► 1R Position Sizer ──► Friction Guard ──► Two-Legged Order Router
    """

    # Static token mapping for default high-liquidity F&O scrips
    DEFAULT_NSE_TOKENS: Dict[str, str] = {
        "RELIANCE": "2885",
        "TCS": "11536",
        "HDFCBANK": "1333",
        "INFY": "1594",
        "ICICIBANK": "4963",
        "SBIN": "3045",
        "BHARTIARTL": "10604",
        "KOTAKBANK": "1922",
        "LT": "11483",
        "AXISBANK": "5900",
        "ASIANPAINT": "236",
        "MARUTI": "10999",
        "TITAN": "3506",
        "BAJFINANCE": "317",
        "TRENT": "1964",
    }

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.is_running = False

        # 1. Core Services
        self.auth_manager = AuthManager(self.settings)
        self.bar_aggregator = BarAggregator(
            bar_interval_seconds=300,  # 5-minute bars
            max_history=300,
            on_candle_close=self.on_candle_closed,
        )
        self.ws_manager = WebSocketManager(
            on_tick=self.on_tick_received,
            settings=self.settings,
        )

        # 2. Risk Components
        self.circuit_breaker = CircuitBreaker(self.settings)
        self.position_sizer = PositionSizer(self.settings)
        self.friction_guard = FrictionGuard(self.settings)

        # 3. Strategy Suite & Confluence (Top 4 Proven Alpha Engines)
        self.strategies = [
            BreakoutEngine(),
            BollingerExpansionStrategy(),
            InstitutionalAbsorptionStrategy(),
            InstitutionalFVGStrategy(),
        ]
        self.confluence_gate = ConfluenceGate(self.settings)

        # 4. Execution Engines
        self.order_router = OrderRouter(settings=self.settings)
        self.ratchet_manager = RatchetManager(
            order_router=self.order_router,
            settings=self.settings,
            on_trade_closed=self.on_trade_closed,
        )

        # Background async tasks
        self._bg_tasks: List[asyncio.Task] = []

    def on_tick_received(
        self, token: str, symbol: str, ltp: float, day_volume: float, tick_time: float
    ):
        """
        Sub-millisecond synchronous callback invoked on every incoming WebSocket tick.
        Dispatches to:
        1. In-memory candlestick synthesizer (BarAggregator)
        2. Dynamic Trailing Stop-Loss Ratchet / Target Manager (RatchetManager)
        """
        # Feed the bar aggregator
        self.bar_aggregator.process_tick(
            token=token,
            tradingsymbol=symbol,
            ltp=ltp,
            day_volume=day_volume,
            tick_time=tick_time,
        )

        # Update high/low water marks & trailing stop-losses for any open position
        self.ratchet_manager.update_with_tick(token=token, symbol=symbol, ltp=ltp)

    async def on_candle_closed(
        self, token: str, symbol: str, bar: Candle, history_df: pd.DataFrame
    ):
        """
        Asynchronous event triggered the exact millisecond a 5-minute bar closes.
        Zero REST candle polling — alpha evaluates on in-memory synthesized bars.
        """
        if not self.is_running:
            return

        logger.info(
            "BAR CLOSED: %s (O: %.2f, H: %.2f, L: %.2f, C: %.2f, V: %.0f) [History: %d bars]",
            symbol,
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume,
            len(history_df),
        )

        # 1. Circuit Breaker Gate: Can we open a new position?
        can_trade, reason = self.circuit_breaker.can_open_new_trade(
            current_open_positions=len(self.order_router.active_trades)
        )
        if not can_trade:
            logger.debug("Trade entry suppressed: %s", reason)
            return

        # Avoid duplicate trade entry if already in an active position for this stock
        if symbol in self.order_router.active_trades:
            logger.debug("Skipping entry for %s — position already active.", symbol)
            return

        # 2. Strategy Suite Evaluation
        raw_signals = []
        for strat in self.strategies:
            try:
                sigs = strat.evaluate(history_df, symbol)
                raw_signals.extend(sigs)
            except Exception as e:
                logger.error(
                    "Error evaluating strategy %s on %s: %s", strat.name, symbol, e
                )

        if not raw_signals:
            return

        # 3. Multi-Family Confluence Gate
        approved_signal = self.confluence_gate.validate_signals(raw_signals, history_df)
        if not approved_signal:
            return

        # 4. Quantitative 1R Volatility Parity Position Sizing & Friction Guard
        quantity, size_result = self.position_sizer.calculate_size(
            entry_price=approved_signal.entry_price,
            stop_loss=approved_signal.stop_loss,
            target_price=approved_signal.target_price,
            portfolio_equity=self.settings.portfolio_equity,
        )
        if not size_result.is_valid or quantity <= 0:
            logger.warning(
                "Trade rejected by PositionSizer for %s: %s",
                symbol,
                size_result.rejection_reason,
            )
            return

        # 5. Pre-Trade Statutory Friction & Turnover Guard
        passed_friction, friction_msg, breakdown = self.friction_guard.validate_trade(
            entry_price=approved_signal.entry_price,
            target_price=approved_signal.target_price,
            quantity=quantity,
        )
        if not passed_friction:
            logger.warning(
                "Trade rejected by FrictionGuard for %s: %s", symbol, friction_msg
            )
            return

        # 6. Two-Legged Native Exchange Execution
        logger.success(
            "🚀 EXECUTING TRADE: %s %d %s @ ₹%.2f | SL: ₹%.2f | Target: ₹%.2f | Turnover: ₹%s",
            approved_signal.direction,
            quantity,
            symbol,
            approved_signal.entry_price,
            approved_signal.stop_loss,
            approved_signal.target_price,
            f"{breakdown.total_turnover:,.2f}",
        )
        self.order_router.execute_two_legged_trade(
            signal=approved_signal,
            token=token,
            quantity=quantity,
        )

    def on_trade_closed(self, trade: ActiveTrade, pnl: float, exit_reason: str):
        """Callback triggered when a trade is closed via target or stop-loss."""
        self.circuit_breaker.record_trade_completion(pnl=pnl)
        status = self.circuit_breaker.get_status()
        logger.info(
            "Trade Exit: %s (%s) | P&L: ₹%.2f | Session Total P&L: ₹%.2f | Trades Completed: %d/%d",
            trade.tradingsymbol,
            exit_reason,
            pnl,
            status["total_pnl"],
            status["completed_trades"],
            status["max_trades_allowed"],
        )

    async def _session_monitoring_loop(self):
        """Asynchronous loop checking circuit breaker kill switches and 15:15 IST square-off."""
        logger.info("Starting session circuit breaker & EOD square-off supervisor...")
        while self.is_running:
            try:
                active_count = len(self.order_router.active_trades)
                must_square_off, reason = self.circuit_breaker.should_square_off(
                    active_count
                )

                if must_square_off:
                    logger.critical("🚨 MANDATORY LIQUIDATION TRIGGERED: %s", reason)
                    self.execute_square_off_all(reason)
                    # If daily loss limit tripped, halt trading loop
                    if self.circuit_breaker.is_circuit_locked:
                        logger.warning(
                            "Circuit breaker locked. Halting automated execution for the day."
                        )
                        break

            except Exception as e:
                logger.error("Error in session supervisor loop: %s", e)

            await asyncio.sleep(5.0)

    def execute_square_off_all(self, reason: str):
        """Liquidate all open positions and cancel open exchange trigger orders."""
        active_copy = dict(self.order_router.active_trades)
        for symbol, trade in active_copy.items():
            # 1. Cancel active exchange trigger order
            if trade.sl_order_id:
                self.order_router.cancel_order(trade.sl_order_id, variety="STOPLOSS")

            # 2. Execute aggressive limit liquidation order
            exit_tx = "SELL" if trade.direction == "BUY" else "BUY"
            self.order_router.emergency_exit_position(
                tradingsymbol=symbol,
                token=trade.token,
                quantity=trade.quantity,
                transaction_type=exit_tx,
            )
            self.order_router.active_trades.pop(symbol, None)
            logger.info("Squared off position in %s (%s)", symbol, reason)

    async def start(self):
        """Start all services and run the primary event loop."""
        logger.info(
            "Initializing Trading System Engine (Mode: %s)...",
            self.settings.mode.upper(),
        )
        self.is_running = True

        # 1. Authenticate with SmartAPI
        session = self.auth_manager.login()
        if self.auth_manager.smart_api:
            self.order_router.set_smart_api(self.auth_manager.smart_api)
            self.ratchet_manager.smart_api = self.auth_manager.smart_api

        # 2. Build token and symbol mapping
        token_mapping = {
            self.DEFAULT_NSE_TOKENS.get(sym, f"99{idx}"): sym
            for idx, sym in enumerate(self.settings.watchlist)
        }
        self.ws_manager.register_symbol_mapping(token_mapping)
        tokens_to_subscribe = list(token_mapping.keys())

        # 3. Start background token renewal supervisor (every 5 hours)
        renewal_task = asyncio.create_task(
            self.auth_manager.start_auto_renewal_task(interval_hours=5.0)
        )
        self._bg_tasks.append(renewal_task)

        # 4. Start session circuit breaker / EOD supervisor
        session_task = asyncio.create_task(self._session_monitoring_loop())
        self._bg_tasks.append(session_task)

        # 5. Connect WebSocket tick stream
        self.ws_manager.start(
            api_key=self.settings.api_key,
            jwt_token=session.jwt_token,
            client_code=session.client_code,
            feed_token=session.feed_token,
            initial_tokens=tokens_to_subscribe,
        )

        logger.success(
            "Trading System Engine LIVE! Monitoring %d symbols on 5-minute synthesized bars.",
            len(tokens_to_subscribe),
        )

        # Keep master event loop running
        while self.is_running:
            await asyncio.sleep(1.0)

    async def shutdown(self):
        """Gracefully terminate engine, disconnect socket, and clean up tasks."""
        logger.warning("Initiating graceful shutdown of Trading System Engine...")
        self.is_running = False

        # Cancel background tasks
        for task in self._bg_tasks:
            if not task.done():
                task.cancel()

        # Stop WebSocket
        self.ws_manager.stop()
        self.auth_manager.stop()

        logger.success("Trading System Engine shutdown complete.")


def handle_signals(engine: TradingSystemEngine, loop: asyncio.AbstractEventLoop):
    """Attach OS signals for graceful shutdown."""
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(engine.shutdown()))
        except (NotImplementedError, RuntimeError):
            pass


def main():
    """Main entrypoint for running the automated trading system."""
    engine = TradingSystemEngine()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    handle_signals(engine, loop)

    try:
        loop.run_until_complete(engine.start())
    except (KeyboardInterrupt, SystemExit):
        loop.run_until_complete(engine.shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
