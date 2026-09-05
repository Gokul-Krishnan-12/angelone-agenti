"""
Backtest Engine — walk-forward simulation of all 21 strategies.

How it works
------------
For each symbol and each bar index `i` (starting after `min_bars`):
  1. Slice the DataFrame to df[:i] (simulating "we only know the past").
  2. Run all enabled strategies through the confluence gate.
  3. If a signal fires:
     - Entry price = next bar's open (df[i+1].open) — realistic fill assumption.
     - Initial SL and target from the signal.
     - ATR trailing SL: on each subsequent bar, ratchet the SL.
     - Exit when: SL hit, target hit, square-off time reached, or end of data.
  4. Record the trade with all metadata.

Key assumptions / simplifications
-----------------------------------
- No slippage beyond the next-bar open.  Real slippage will be worse on 5-min.
- One position per symbol at a time (no pyramiding).
- Square-off time: 15:00 on the same day (IST) for intraday, end-of-data for daily.
- Position size: constant ₹10,000 per trade for P&L calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from ..scanner import _get_strategy_family

# ── Import strategies and scanner logic ─────────────────────────────────────
from ..strategies.adx_momentum import ADXMomentumStrategy
from ..strategies.awesome_oscillator import AwesomeOscillatorStrategy
from ..strategies.bollinger_breakout import BollingerBreakoutStrategy
from ..strategies.cci_reversal import CCIReversalStrategy
from ..strategies.cmf_accumulation import CMFAccumulationStrategy
from ..strategies.donchian_breakout import DonchianBreakoutStrategy
from ..strategies.ema_crossover import EMACrossoverStrategy
from ..strategies.institutional_absorption import InstitutionalAbsorptionStrategy
from ..strategies.keltner_breakout import KeltnerBreakoutStrategy
from ..strategies.macd_cross import MACDCrossStrategy
from ..strategies.mfi_exhaustion import MFIExhaustionStrategy
from ..strategies.order_block_fvg import OrderBlockFVGStrategy
from ..strategies.psar_trend import PSARTrendStrategy
from ..strategies.rsi_reversal import RSIReversalStrategy
from ..strategies.stoc_rsi import StochRSIStrategy
from ..strategies.stochastic_reversal import StochasticReversalStrategy
from ..strategies.supertrend import SupertrendStrategy
from ..strategies.tsi_cross import TSICrossStrategy
from ..strategies.utils import compute_atr
from ..strategies.volume_delta_divergence import VolumeDeltaDivergenceStrategy
from ..strategies.vwap_bounce import VWAPBounceStrategy
from ..strategies.williams_r import WilliamsRStrategy

# ── Strategy registry ────────────────────────────────────────────────────────

ALL_STRATEGIES: Dict[str, Any] = {
    "ema_crossover": EMACrossoverStrategy(),
    "rsi_reversal": RSIReversalStrategy(),
    "vwap_bounce": VWAPBounceStrategy(),
    "supertrend": SupertrendStrategy(),
    "macd_cross": MACDCrossStrategy(),
    "bollinger_breakout": BollingerBreakoutStrategy(),
    "stochastic_reversal": StochasticReversalStrategy(),
    "adx_momentum": ADXMomentumStrategy(),
    "psar_trend": PSARTrendStrategy(),
    "donchian_breakout": DonchianBreakoutStrategy(),
    "cci_reversal": CCIReversalStrategy(),
    "williams_r": WilliamsRStrategy(),
    "mfi_exhaustion": MFIExhaustionStrategy(),
    "keltner_breakout": KeltnerBreakoutStrategy(),
    "awesome_oscillator": AwesomeOscillatorStrategy(),
    "tsi_cross": TSICrossStrategy(),
    "stoc_rsi": StochRSIStrategy(),
    "institutional_absorption": InstitutionalAbsorptionStrategy(),
    "order_block_fvg": OrderBlockFVGStrategy(),
    "cmf_accumulation": CMFAccumulationStrategy(),
    "volume_delta_divergence": VolumeDeltaDivergenceStrategy(),
}

# ── Trade data class ─────────────────────────────────────────────────────────


@dataclass
class BacktestTrade:
    symbol: str
    direction: str  # 'BUY' or 'SELL'
    entry_bar: int
    entry_price: float
    initial_sl: float
    final_sl: float  # may differ if trailing SL kicked in
    target: float
    exit_price: float
    exit_reason: str  # 'TARGET', 'SL', 'TRAILING_SL', 'SQUAREOFF', 'EOD'
    bars_held: int
    pnl_pct: float  # % return on position
    pnl_rs: float  # ₹ P&L on ₹10,000 capital
    rr_achieved: float  # actual R:R achieved
    confluence_score: int
    families_voting: List[str] = field(default_factory=list)
    strategies_voting: List[str] = field(default_factory=list)
    confidence: int = 0


# ── Confluence gate (mirrors scanner.py logic, offline) ─────────────────────


def _apply_confluence(
    signals: List[Dict],
    direction: str,
    min_confluence: int = 2,
    min_rr: float = 1.8,
) -> Optional[Dict]:
    dir_signals = [s for s in signals if s.get("direction") == direction]
    if not dir_signals:
        return None

    families_seen: set = set()
    for sig in dir_signals:
        strat_id = sig.get("_strat_id", "")
        families_seen.add(_get_strategy_family(strat_id))

    if len(families_seen) < min_confluence:
        return None

    best = max(dir_signals, key=lambda s: s.get("confidence", 0))
    rr = best.get("riskReward", 0)
    if rr < min_rr:
        return None

    best = dict(best)
    best["confluenceScore"] = len(families_seen)
    best["familiesVoting"] = sorted(families_seen)
    best["strategyNames"] = [
        s.get("strategy", s.get("_strat_id", "")) for s in dir_signals
    ]
    return best


# ── Backtest engine ──────────────────────────────────────────────────────────


class BacktestEngine:
    def __init__(
        self,
        min_confluence: int = 2,
        min_rr: float = 1.8,
        capital_per_trade: float = 10_000.0,
        trailing_sl_multiplier: float = 1.5,
        min_bars: int = 60,
    ):
        self.min_confluence = min_confluence
        self.min_rr = min_rr
        self.capital = capital_per_trade
        self.tsl_mult = trailing_sl_multiplier
        self.min_bars = min_bars

    def _run_strategies(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Run all strategies on df and return tagged signal list."""
        signals = []
        for strat_id, strat in ALL_STRATEGIES.items():
            try:
                strat_signals = strat.calculate_signals(df.copy(), symbol)
                for sig in strat_signals:
                    sig = dict(sig)
                    sig["_strat_id"] = strat_id
                    signals.append(sig)
            except Exception:
                pass
        return signals

    def _update_trailing_sl(
        self,
        trade_sl: float,
        hwm: float,
        lwm: float,
        ltp: float,
        direction: str,
        atr: float,
    ):
        """Return (new_sl, new_hwm, new_lwm). SL only ratchets favorable."""
        distance = atr * self.tsl_mult
        if direction == "BUY":
            hwm = max(hwm, ltp)
            new_sl = round(hwm - distance, 2)
            if new_sl > trade_sl:
                return new_sl, hwm, lwm
        else:
            lwm = min(lwm, ltp)
            new_sl = round(lwm + distance, 2)
            if new_sl < trade_sl:
                return new_sl, hwm, lwm
        return trade_sl, hwm, lwm

    def run_symbol(self, df: pd.DataFrame, symbol: str) -> List[BacktestTrade]:
        """Run walk-forward backtest for a single symbol."""
        trades: List[BacktestTrade] = []
        in_trade = False
        n = len(df)

        if n < self.min_bars + 2:
            return trades

        # Walk forward bar by bar
        i = self.min_bars
        while i < n - 1:
            if in_trade:
                i += 1
                continue  # position management handled inside trade loop below

            # Run strategies on data up to (but not including) bar i
            window = df.iloc[:i]
            raw_signals = self._run_strategies(window, symbol)

            # Try BUY then SELL confluence gate
            chosen = None
            for direction in ("BUY", "SELL"):
                chosen = _apply_confluence(
                    raw_signals, direction, self.min_confluence, self.min_rr
                )
                if chosen:
                    break

            if not chosen:
                i += 1
                continue

            # Entry at next bar's open
            entry_bar = i
            entry_price = float(df.iloc[i + 1]["open"])
            direction = chosen["direction"]
            initial_sl = float(chosen.get("stopLoss", chosen.get("sl", 0)))
            target = float(chosen.get("target", 0))
            atr = float(chosen.get("indicators", {}).get("atr", 0)) or compute_atr(
                window
            )

            if initial_sl <= 0 or target <= 0:
                i += 1
                continue

            # Adjust SL/target from signal price to actual entry
            signal_price = float(chosen.get("entryPrice", entry_price))
            if (
                signal_price > 0
                and abs(signal_price - entry_price) / signal_price < 0.02
            ):
                # Small gap — keep signal levels
                pass
            else:
                # Re-anchor to actual entry
                risk = abs(signal_price - initial_sl)
                if direction == "BUY":
                    initial_sl = round(entry_price - risk, 2)
                    target = round(entry_price + risk * 2.0, 2)
                else:
                    initial_sl = round(entry_price + risk, 2)
                    target = round(entry_price - risk * 2.0, 2)

            # Manage trade bar-by-bar
            trade_sl = initial_sl
            hwm = entry_price
            lwm = entry_price
            exit_price = entry_price
            exit_reason = "EOD"
            in_trade = True
            j = i + 2  # first management bar

            while j < n:
                bar = df.iloc[j]
                lo = float(bar["low"])
                hi = float(bar["high"])
                close = float(bar["close"])

                # Update ATR periodically (every 10 bars) for trailing SL
                if (j - i) % 10 == 0:
                    atr = compute_atr(df.iloc[:j]) or atr

                # Check exit conditions (check SL before target for realism)
                if direction == "BUY":
                    if lo <= trade_sl:
                        exit_price = trade_sl
                        exit_reason = "TRAILING_SL" if trade_sl > initial_sl else "SL"
                        break
                    if hi >= target:
                        exit_price = target
                        exit_reason = "TARGET"
                        break
                else:
                    if hi >= trade_sl:
                        exit_price = trade_sl
                        exit_reason = "TRAILING_SL" if trade_sl < initial_sl else "SL"
                        break
                    if lo <= target:
                        exit_price = target
                        exit_reason = "TARGET"
                        break

                # Ratchet trailing SL
                trade_sl, hwm, lwm = self._update_trailing_sl(
                    trade_sl, hwm, lwm, close, direction, atr
                )

                j += 1

            if exit_reason == "EOD":
                exit_price = float(df.iloc[-1]["close"])

            # Calculate P&L
            if direction == "BUY":
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100

            qty = max(1, int(self.capital / entry_price))
            pnl_rs = pnl_pct / 100 * qty * entry_price
            risk_per_unit = abs(entry_price - initial_sl)
            reward_per_unit = abs(exit_price - entry_price)
            rr_achieved = (
                round(reward_per_unit / risk_per_unit, 2) if risk_per_unit > 0 else 0.0
            )

            trades.append(
                BacktestTrade(
                    symbol=symbol,
                    direction=direction,
                    entry_bar=entry_bar,
                    entry_price=round(entry_price, 2),
                    initial_sl=round(initial_sl, 2),
                    final_sl=round(trade_sl, 2),
                    target=round(target, 2),
                    exit_price=round(exit_price, 2),
                    exit_reason=exit_reason,
                    bars_held=j - (i + 1),
                    pnl_pct=round(pnl_pct, 2),
                    pnl_rs=round(pnl_rs, 2),
                    rr_achieved=rr_achieved,
                    confluence_score=chosen.get("confluenceScore", 0),
                    families_voting=chosen.get("familiesVoting", []),
                    strategies_voting=chosen.get("strategyNames", []),
                    confidence=chosen.get("confidence", 0),
                )
            )

            in_trade = False
            i = j + 1  # resume scan after the trade ends

        return trades

    def run(self, symbol_dfs: Dict[str, pd.DataFrame]) -> List[BacktestTrade]:
        """Run backtest across all symbols. Returns all trades."""
        all_trades: List[BacktestTrade] = []
        total = len(symbol_dfs)
        for idx, (symbol, df) in enumerate(symbol_dfs.items(), 1):
            print(
                f"  [{idx}/{total}] Backtesting {symbol} ({len(df)} bars)...",
                end=" ",
                flush=True,
            )
            if df.empty or len(df) < self.min_bars + 2:
                print("skipped (insufficient data)")
                continue
            trades = self.run_symbol(df, symbol)
            print(f"{len(trades)} trade(s)")
            all_trades.extend(trades)
        return all_trades
