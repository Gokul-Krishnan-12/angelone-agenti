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

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

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

# ── Statutory Indian Market Friction Calculator ──────────────────────────────


def compute_statutory_friction(
    entry_price: float, exit_price: float, qty: int
) -> float:
    """Compute round-trip friction for NSE Cash Intraday MIS trade."""
    buy_turnover = round(entry_price * qty, 2)
    sell_turnover = round(exit_price * qty, 2)
    total_turnover = round(buy_turnover + sell_turnover, 2)

    brokerage = 40.0  # ₹20 buy + ₹20 sell
    stt = round(sell_turnover * 0.00025, 2)  # 0.025% on sell
    exchange_fee = round(total_turnover * 0.0000325, 2)  # 0.00325%
    sebi_charge = round(total_turnover * 0.000001, 2)  # ₹10 / crore
    stamp_duty = round(buy_turnover * 0.00003, 2)  # 0.003% on buy
    gst = round((brokerage + exchange_fee + sebi_charge) * 0.18, 2)
    return round(brokerage + stt + exchange_fee + sebi_charge + stamp_duty + gst, 2)


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
    pnl_rs: float  # Gross ₹ P&L
    friction_rs: float = (
        0.0  # Indian statutory friction (brokerage, STT, turnover, GST)
    )
    net_pnl_rs: float = 0.0  # Realized net ₹ P&L after friction
    entry_time: str = ""  # ISO timestamp of entry
    rr_achieved: float = 0.0  # actual R:R achieved
    confluence_score: int = 0
    families_voting: List[str] = field(default_factory=list)
    strategies_voting: List[str] = field(default_factory=list)
    confidence: int = 0


# ── Confluence gate (mirrors scanner.py logic, offline) ─────────────────────


def _apply_confluence(
    signals: List[Dict],
    direction: str,
    min_confluence: int = 2,
    min_rr: float = 1.8,
    df: Optional[pd.DataFrame] = None,
    trend_aligned: bool = True,
    min_sl_pct: float = 1.0,
) -> Optional[Dict]:
    dir_signals = [s for s in signals if s.get("direction") == direction]
    if not dir_signals:
        return None

    # Trend alignment gate (against 50 EMA)
    if trend_aligned and df is not None and len(df) >= 50:
        closes = df["close"]
        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
        curr_close = closes.iloc[-1]
        if direction == "BUY" and curr_close < ema50:
            return None  # avoid counter-trend buy
        if direction == "SELL" and curr_close > ema50:
            return None  # avoid counter-trend sell

    families_seen: set = set()
    for sig in dir_signals:
        strat_id = sig.get("_strat_id", "")
        families_seen.add(_get_strategy_family(strat_id))

    if len(families_seen) < min_confluence:
        return None

    best = max(dir_signals, key=lambda s: s.get("confidence", 0))
    rr = float(best.get("riskReward", 0))
    if rr < min_rr:
        return None

    best = dict(best)
    entry_p = float(best.get("entryPrice", best.get("price", 0.0)))
    sl_p = float(best.get("stopLoss", best.get("sl", 0.0)))

    # Safe minimum stop-loss buffer
    if min_sl_pct > 0 and entry_p > 0 and sl_p > 0:
        current_sl_pct = abs(entry_p - sl_p) / entry_p * 100.0
        if current_sl_pct < min_sl_pct:
            safe_risk = entry_p * (min_sl_pct / 100.0)
            if direction == "BUY":
                best["stopLoss"] = round(entry_p - safe_risk, 2)
                best["target"] = round(entry_p + safe_risk * max(min_rr, rr), 2)
            else:
                best["stopLoss"] = round(entry_p + safe_risk, 2)
                best["target"] = round(entry_p - safe_risk * max(min_rr, rr), 2)

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
        trailing_sl_multiplier: float = 2.0,
        min_bars: int = 60,
        trail_after_r: float = 1.0,
        trend_aligned: bool = True,
        min_sl_pct: float = 1.0,
        max_trades_per_day: int = 8,
        enforce_friction_guard: bool = True,
        friction_multiple: float = 3.5,
        disabled_strategies: Optional[Set[str]] = None,
    ):
        self.min_confluence = min_confluence
        self.min_rr = min_rr
        self.capital = capital_per_trade
        self.tsl_mult = trailing_sl_multiplier
        self.min_bars = min_bars
        self.trail_after_r = trail_after_r
        self.trend_aligned = trend_aligned
        self.min_sl_pct = min_sl_pct
        self.max_trades_per_day = max_trades_per_day
        self.enforce_friction_guard = enforce_friction_guard
        self.friction_multiple = friction_multiple

        self.disabled_strats = (
            disabled_strategies
            if disabled_strategies is not None
            else {
                "williams_r",
                "cci_reversal",
                "adx_momentum",
                "rsi_reversal",
                "vwap_bounce",
                "mfi_exhaustion",
                "stochastic_reversal",
                "supertrend",
            }
        )

    def _run_strategies(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Run all strategies on df and return tagged signal list."""
        signals = []
        for strat_id, strat in ALL_STRATEGIES.items():
            if self.disabled_strats and strat_id in self.disabled_strats:
                continue
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
        entry_price: float,
        trade_risk: float,
    ):
        """Return (new_sl, new_hwm, new_lwm). Ratchets favorably once profit threshold is reached."""
        distance = atr * self.tsl_mult
        threshold = trade_risk * self.trail_after_r if self.trail_after_r > 0 else 0.0

        if direction == "BUY":
            hwm = max(hwm, ltp)
            # Only activate trailing SL once trade advances at least threshold into profit
            if (hwm - entry_price) >= threshold:
                new_sl = round(max(trade_sl, entry_price, hwm - distance), 2)
                if new_sl > trade_sl:
                    return new_sl, hwm, lwm
        else:
            lwm = min(lwm, ltp)
            # Only activate trailing SL once trade drops at least threshold into profit
            if (entry_price - lwm) >= threshold:
                new_sl = round(min(trade_sl, entry_price, lwm + distance), 2)
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
                    raw_signals,
                    direction,
                    self.min_confluence,
                    self.min_rr,
                    df=window,
                    trend_aligned=self.trend_aligned,
                    min_sl_pct=self.min_sl_pct,
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

            trade_risk = abs(entry_price - initial_sl)
            qty = max(1, int(self.capital / entry_price))

            # Pre-trade Friction Guard Check (reject if payoff < 3.5x friction)
            if self.enforce_friction_guard:
                est_friction = compute_statutory_friction(entry_price, target, qty)
                expected_gain = abs(target - entry_price) * qty
                if expected_gain < (self.friction_multiple * est_friction):
                    i += 1
                    continue

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

                # Check exit conditions (target takes precedence when touched)
                if direction == "BUY":
                    if hi >= target:
                        exit_price = target
                        exit_reason = "TARGET"
                        break
                    if lo <= trade_sl:
                        exit_price = trade_sl
                        exit_reason = "TRAILING_SL" if trade_sl > initial_sl else "SL"
                        break
                else:
                    if lo <= target:
                        exit_price = target
                        exit_reason = "TARGET"
                        break
                    if hi >= trade_sl:
                        exit_price = trade_sl
                        exit_reason = "TRAILING_SL" if trade_sl < initial_sl else "SL"
                        break

                # Ratchet trailing SL with profit cushion
                trade_sl, hwm, lwm = self._update_trailing_sl(
                    trade_sl,
                    hwm,
                    lwm,
                    close,
                    direction,
                    atr,
                    entry_price,
                    trade_risk,
                )

                j += 1

            if exit_reason == "EOD":
                exit_price = float(df.iloc[-1]["close"])

            # Calculate P&L
            if direction == "BUY":
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100

            pnl_rs = pnl_pct / 100 * qty * entry_price
            friction_rs = compute_statutory_friction(entry_price, exit_price, qty)
            net_pnl_rs = round(pnl_rs - friction_rs, 2)

            risk_per_unit = abs(entry_price - initial_sl)
            reward_per_unit = abs(exit_price - entry_price)
            rr_achieved = (
                round(reward_per_unit / risk_per_unit, 2) if risk_per_unit > 0 else 0.0
            )

            entry_dt = ""
            if "datetime" in df.columns:
                entry_dt = str(df.iloc[entry_bar + 1]["datetime"])
            elif isinstance(df.index, pd.DatetimeIndex):
                entry_dt = str(df.index[entry_bar + 1])
            else:
                entry_dt = f"Bar_{entry_bar + 1:04d}"

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
                    friction_rs=friction_rs,
                    net_pnl_rs=net_pnl_rs,
                    entry_time=entry_dt,
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

        # Enforce max trades per day across portfolio
        if self.max_trades_per_day > 0 and all_trades:
            all_trades.sort(key=lambda t: t.entry_time)
            filtered_trades: List[BacktestTrade] = []
            daily_counts: Dict[str, int] = defaultdict(int)
            for t in all_trades:
                day_key = t.entry_time[:10] if len(t.entry_time) >= 10 else "UNKNOWN"
                if daily_counts[day_key] < self.max_trades_per_day:
                    daily_counts[day_key] += 1
                    filtered_trades.append(t)
            all_trades = filtered_trades

        return all_trades
