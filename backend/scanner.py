"""
Scanner — multi-strategy market scanner with confluence gate and regime filter.

Architecture
------------
Each symbol is processed through the full enabled strategy suite.  Raw signals
are then filtered by a **Confluence Gate** before being forwarded to the
trading engine / UI:

1. Regime Filter   — symbols with ADX < 18 (volatile/choppy) are skipped for
                     new entries.
2. Market Hours    — no new entry signals in the first ``noEntryFirstMins``
                     minutes after market open (default 15 min = 9:15–9:30 IST).
3. Confluence Gate — signals for a given symbol+direction are grouped by
                     *signal family*.  Oscillator-family strategies (6 indicators)
                     count as ONE vote.  A minimum of 2 independent families must
                     agree before a signal is forwarded.
4. R:R Gate        — signals with risk-reward < ``minRiskReward`` (default 1.8)
                     are discarded.

Each forwarded signal is enriched with:
  • confluenceScore  — number of distinct voting families
  • familiesVoting   — list of family names
  • strategyCount    — total number of strategy signals in this direction
  • allStrategies    — names of all strategies that voted

Signal Families
---------------
  trend:     ema_crossover, supertrend, psar_trend, adx_momentum
  momentum:  macd_cross, rsi_reversal, tsi_cross
  oscillator: stochastic_reversal, stoc_rsi, cci_reversal, williams_r,
              awesome_oscillator, mfi_exhaustion   ← counts as 1 family
  breakout:  bollinger_breakout, donchian_breakout, keltner_breakout
  intraday:  vwap_bounce
  volume:    cmf_accumulation
  structure: institutional_absorption, order_block_fvg, volume_delta_divergence
"""

import datetime
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from .config import config_manager
from .smartapi_client import smart_api_client
from .strategies.adx_momentum import ADXMomentumStrategy
from .strategies.awesome_oscillator import AwesomeOscillatorStrategy
from .strategies.bollinger_breakout import BollingerBreakoutStrategy
from .strategies.cci_reversal import CCIReversalStrategy
from .strategies.cmf_accumulation import CMFAccumulationStrategy
from .strategies.donchian_breakout import DonchianBreakoutStrategy
from .strategies.ema_crossover import EMACrossoverStrategy
from .strategies.gap_fill import GapFillStrategy
from .strategies.institutional_absorption import InstitutionalAbsorptionStrategy
from .strategies.keltner_breakout import KeltnerBreakoutStrategy
from .strategies.liquidity_grab_reversal import LiquidityGrabReversalStrategy
from .strategies.macd_cross import MACDCrossStrategy
from .strategies.mfi_exhaustion import MFIExhaustionStrategy
from .strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from .strategies.order_block_fvg import OrderBlockFVGStrategy
from .strategies.psar_trend import PSARTrendStrategy
from .strategies.rsi_reversal import RSIReversalStrategy
from .strategies.stoc_rsi import StochRSIStrategy
from .strategies.stochastic_reversal import StochasticReversalStrategy
from .strategies.supertrend import SupertrendStrategy
from .strategies.tsi_cross import TSICrossStrategy
from .strategies.volume_delta_divergence import VolumeDeltaDivergenceStrategy
from .strategies.vwap_bounce import VWAPBounceStrategy
from .strategies.williams_r import WilliamsRStrategy

# ─── Strategy family definitions ──────────────────────────────────────────────
# Each family counts as exactly ONE vote in the confluence score, regardless of
# how many individual strategies within that family fire.

STRATEGY_FAMILIES: Dict[str, Set[str]] = {
    "trend": {"ema_crossover", "supertrend", "psar_trend", "adx_momentum"},
    "momentum": {"macd_cross", "rsi_reversal", "tsi_cross"},
    "oscillator": {
        "stochastic_reversal",
        "stoc_rsi",
        "cci_reversal",
        "williams_r",
        "awesome_oscillator",
        "mfi_exhaustion",
    },
    "breakout": {"bollinger_breakout", "donchian_breakout", "keltner_breakout"},
    "intraday": {"vwap_bounce", "opening_range_breakout"},
    "volume": {"cmf_accumulation"},
    "structure": {
        "institutional_absorption",
        "order_block_fvg",
        "volume_delta_divergence",
    },
    # High-win-rate reversal strategies form their own family
    "reversal": {"liquidity_grab_reversal", "gap_fill"},
}


def _get_strategy_family(strategy_id: str) -> str:
    """Map a strategy ID to its signal family name."""
    for family, strats in STRATEGY_FAMILIES.items():
        if strategy_id in strats:
            return family
    return "other"


def _is_market_open_phase(no_entry_mins: int) -> bool:
    """
    Return True if the current time is within the no-entry window after
    market open (9:15 IST + no_entry_mins).
    """
    now = datetime.datetime.now()
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    no_entry_end = market_open + datetime.timedelta(minutes=no_entry_mins)
    return market_open <= now < no_entry_end


def _is_entry_window() -> bool:
    """
    Return True if current time falls inside a high-probability entry window.

    Research shows that intraday strategies have substantially higher win rates
    in two windows:
      • 10:00 – 11:30 IST  (post-open volatility settled, strong directional moves)
      • 13:30 – 14:30 IST  (afternoon session, European/US open influence)

    Outside these windows (midday chop and end-of-day squaring off) signal
    quality drops significantly.

    Outside market hours (backtesting / paper mode) always returns True so
    that the scanner can still generate signals during development.
    """
    now = datetime.datetime.now().time()
    market_open_t = datetime.time(9, 15)
    market_close_t = datetime.time(15, 30)

    # Outside market hours → don't gate (backtest / paper trading)
    if now < market_open_t or now > market_close_t:
        return True

    window_1 = datetime.time(10, 0) <= now <= datetime.time(11, 30)
    window_2 = datetime.time(13, 30) <= now <= datetime.time(14, 30)
    return window_1 or window_2


# ─── Scanner ──────────────────────────────────────────────────────────────────


class Scanner:
    def __init__(self):
        self.strategies: Dict[str, Any] = {
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
            # ── High-win-rate strategies (new) ──────────────────────────
            "opening_range_breakout": OpeningRangeBreakoutStrategy(),
            "liquidity_grab_reversal": LiquidityGrabReversalStrategy(),
            "gap_fill": GapFillStrategy(),
        }
        self.candle_cache: Dict[Any, pd.DataFrame] = {}
        self.last_cache_time: Dict[Any, datetime.datetime] = {}

    # ──────────────────────────────────────────────────────────────────
    # Candle fetching
    # ──────────────────────────────────────────────────────────────────

    def _fetch_candles(
        self, instrument_token: Any, tradingsymbol: str
    ) -> Tuple[pd.DataFrame, bool]:
        now = datetime.datetime.now()

        # Use cache if less than 1 minute old
        if (
            instrument_token in self.candle_cache
            and (
                now - self.last_cache_time.get(instrument_token, datetime.datetime.min)
            ).seconds
            < 60
        ):
            return self.candle_cache[instrument_token], True

        from_date = now - datetime.timedelta(days=5)
        to_date = now

        try:
            records = smart_api_client.get_historical_data(
                instrument_token, from_date, to_date, "5minute", exchange="NSE"
            )
            if not records:
                return pd.DataFrame(), False

            df = pd.DataFrame(records)
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            if "volume" in df.columns:
                df["volume"] = df["volume"].astype(float)

            self.candle_cache[instrument_token] = df
            self.last_cache_time[instrument_token] = now
            return df, False
        except Exception as e:
            print(f"Error fetching candles for {tradingsymbol}: {e}")
            return pd.DataFrame(), False

    # ──────────────────────────────────────────────────────────────────
    # Confluence gate
    # ──────────────────────────────────────────────────────────────────

    def _apply_confluence_gate(
        self,
        dir_signals: List[Dict[str, Any]],
        min_confluence: int,
        min_rr: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Apply the confluence and R:R gate to a group of same-direction signals.

        Returns the highest-confidence signal enriched with confluence metadata
        if the group passes, or None if it fails.
        """
        # Compute distinct family votes (oscillator = 1 regardless of count)
        families_seen: Set[str] = set()
        for sig in dir_signals:
            strat_id = sig.get("_strategy_id", "")
            families_seen.add(_get_strategy_family(strat_id))

        confluence_score = len(families_seen)

        if confluence_score < min_confluence:
            return None

        # Take the signal with the highest confidence
        best = max(dir_signals, key=lambda s: s.get("confidence", 0))
        rr = best.get("riskReward", 0)
        if rr < min_rr:
            return None

        # Enrich the chosen signal with confluence metadata
        best = dict(best)
        best["confluenceScore"] = confluence_score
        best["familiesVoting"] = sorted(families_seen)
        best["strategyCount"] = len(dir_signals)
        best["allStrategies"] = [
            s.get("strategy", s.get("_strategy_id", "")) for s in dir_signals
        ]
        best.pop("_strategy_id", None)

        return best

    # ──────────────────────────────────────────────────────────────────
    # Main watchlist scan
    # ──────────────────────────────────────────────────────────────────

    def scan_watchlist(
        self, symbols: List[str], on_signal=None
    ) -> List[Dict[str, Any]]:
        import concurrent.futures

        all_signals: List[Dict[str, Any]] = []
        strategy_config = config_manager.get_strategy_config()
        risk_config = config_manager.get_risk_config()
        min_confluence = int(risk_config.get("minConfluenceScore", 2))
        min_rr = float(risk_config.get("minRiskReward", 1.8))
        no_entry_mins = int(risk_config.get("noEntryFirstMins", 15))

        def process_symbol(symbol: str) -> List[Dict[str, Any]]:
            # ── Market hours gate (first N minutes) ───────────────────
            if _is_market_open_phase(no_entry_mins):
                return []

            # ── Time-window gate (high-probability entry windows only) ─
            if not _is_entry_window():
                return []

            token = smart_api_client.resolve_token(symbol)
            if not token:
                return []

            df, was_cached = self._fetch_candles(token, symbol)
            if df.empty:
                return []

            # ── Regime filter ──────────────────────────────────────────
            from .strategies.utils import compute_regime

            regime = compute_regime(df)
            if regime == "volatile":
                if not was_cached:
                    time.sleep(1.0)
                return []

            # ── Run all enabled strategies ─────────────────────────────
            buy_signals: List[Dict[str, Any]] = []
            sell_signals: List[Dict[str, Any]] = []

            for strat_id, strategy in self.strategies.items():
                cfg = strategy_config.get(strat_id, {})
                if not cfg.get("enabled", False):
                    continue
                try:
                    strat_signals = strategy.calculate_signals(df, symbol)
                    for sig in strat_signals:
                        sig = dict(sig)
                        sig["_strategy_id"] = strat_id
                        if sig.get("direction") == "BUY":
                            buy_signals.append(sig)
                        elif sig.get("direction") == "SELL":
                            sell_signals.append(sig)
                except Exception:
                    pass

            # Respect SmartAPI rate limits (max 3 historical requests/second)
            if not was_cached:
                time.sleep(1.0)

            # ── Confluence gate ────────────────────────────────────────
            validated: List[Dict[str, Any]] = []
            for dir_signals in (buy_signals, sell_signals):
                if not dir_signals:
                    continue
                validated_sig = self._apply_confluence_gate(
                    dir_signals, min_confluence, min_rr
                )
                if validated_sig is not None:
                    validated.append(validated_sig)

            return validated

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_symbol, symbol) for symbol in symbols]
            for future in concurrent.futures.as_completed(futures):
                try:
                    signals = future.result()
                    if signals:
                        if on_signal:
                            for sig in signals:
                                on_signal(sig)
                        all_signals.extend(signals)
                except Exception as e:
                    import sys

                    print(f"Error in parallel processing: {e}", file=sys.stderr)

        all_signals.sort(
            key=lambda x: x.get("confluenceScore", 0) * 100 + x.get("confidence", 0),
            reverse=True,
        )
        return all_signals

    # ──────────────────────────────────────────────────────────────────
    # Position re-evaluation (no confluence gate — used for monitoring)
    # ──────────────────────────────────────────────────────────────────

    def evaluate_position(
        self, tradingsymbol: str, instrument_token: Any
    ) -> Dict[str, Any]:
        """
        Re-evaluate a single symbol against all enabled strategies.
        Returns a directional summary for thesis-invalidation checks.
        Confluence gate is NOT applied here; this is for monitoring, not entry.
        """
        strategy_config = config_manager.get_strategy_config()

        df, _ = self._fetch_candles(instrument_token, tradingsymbol)
        if df.empty:
            return {"buy_signals": 0, "sell_signals": 0, "strategies": []}

        buy_signals = 0
        sell_signals = 0
        triggered_strategies = []

        for strat_id, strategy in self.strategies.items():
            cfg = strategy_config.get(strat_id, {})
            if not cfg.get("enabled", False):
                continue

            try:
                signals = strategy.calculate_signals(df, tradingsymbol)
                for sig in signals:
                    if sig.get("direction") == "BUY":
                        buy_signals += 1
                        triggered_strategies.append(
                            {
                                "strategy": strat_id,
                                "direction": "BUY",
                                "confidence": sig.get("confidence", 0),
                            }
                        )
                    elif sig.get("direction") == "SELL":
                        sell_signals += 1
                        triggered_strategies.append(
                            {
                                "strategy": strat_id,
                                "direction": "SELL",
                                "confidence": sig.get("confidence", 0),
                            }
                        )
            except Exception:
                pass

        return {
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "strategies": triggered_strategies,
        }


scanner = Scanner()
