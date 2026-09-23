from __future__ import annotations

import datetime
import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .fno_universe import get_fno_universe
from .nifty_universe import NIFTY_50
from .smartapi_client import smart_api_client

logger = logging.getLogger(__name__)


# ── Dynamic Intraday Universe ───────────────────────────────────────────────
# Static symbol blacklists are disabled. The system now utilizes the dynamic
# Microstructural Quality Gate (RVOL >= 1.2x, KER >= 0.30, Rejection Wick <= 25%,
# Midday Lull Protection) to dynamically reject false-breakout traps on any symbol.
DEFAULT_BLACKLIST: set[str] = set()



def calculate_kaufman_efficiency_ratio(
    series: pd.Series | np.ndarray | list[float],
    period: int = 20,
) -> float:
    """Calculate Kaufman Efficiency Ratio (KER / ER) over lookback period N.

    Mathematical Definition:
        Direction  = |Close_t - Close_{t-N}|
        Volatility = Sum_{i=0}^{N-1} |Close_{t-i} - Close_{t-i-1}|
        KER = Direction / Volatility (if Volatility > 0 else 0.0)

    Parameters
    ----------
    series : Price series (typically daily close prices).
    period : Lookback window N (default: 20).

    Returns
    -------
    float : Efficiency ratio clamped in [0.0, 1.0].
            1.0 = Pure straight-line trend.
            <0.25 = Choppy, noisy, mean-reverting regime.
    """
    if series is None:
        return 0.0

    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    clean = series.dropna()
    if len(clean) < period + 1:
        return 0.0

    window = clean.iloc[-(period + 1) :]
    direction = abs(float(window.iloc[-1]) - float(window.iloc[0]))
    volatility = float(window.diff().abs().iloc[1:].sum())

    if volatility <= 1e-12 or np.isnan(volatility) or np.isnan(direction):
        return 0.0

    ker = direction / volatility
    return float(np.clip(ker, 0.0, 1.0))


def evaluate_universe_candidate(
    symbol: str,
    daily_df: Optional[pd.DataFrame] = None,
    ltp: Optional[float] = None,
    rvol: Optional[float] = None,
    current_time: Optional[datetime.time] = None,
    min_price: float = 150.0,
    min_turnover_cr: float = 40.0,
    min_atr_pct: float = 1.5,
    min_ker: float = 0.35,
    min_rvol: float = 1.8,
) -> tuple[bool, str, Dict[str, Any]]:
    """Macro daily regime screening pipeline for universe candidates.

    Quantitative Filter Gates:
    1. Price Floor: LTP >= min_price (default: ₹150)
    2. 20-Day Average Daily Turnover: >= min_turnover_cr (default: ₹40 Cr)
    3. Daily ATR%: >= min_atr_pct (default: 1.5%)
    4. Kaufman Efficiency Ratio (KER 20D): >= min_ker (default: 0.35)
    5. Morning RVOL (at or after 09:45 IST): >= min_rvol (default: 1.8)

    Returns
    -------
    tuple[bool, str, Dict[str, Any]] : (passed, reason, metrics_dict)
    """
    clean_sym = symbol.replace("NSE:", "").replace("-EQ", "").strip().upper()

    if daily_df is not None and len(daily_df) >= 15:
        closes = daily_df["close"]
        highs = daily_df["high"]
        lows = daily_df["low"]
        volumes = daily_df["volume"]

        calc_ltp = float(ltp if ltp is not None else closes.iloc[-1])
        turnover_cr = float((closes.tail(20) * volumes.tail(20)).mean() / 10_000_000.0)

        tr1 = highs - lows
        tr2 = (highs - closes.shift(1)).abs()
        tr3 = (lows - closes.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr14 = float(tr.rolling(window=14, min_periods=7).mean().iloc[-1])
        atr_pct = float((atr14 / calc_ltp) * 100.0) if calc_ltp > 0 else 0.0

        ker = calculate_kaufman_efficiency_ratio(closes, period=20)
    else:
        calc_ltp = float(ltp or 0.0)
        turnover_cr = 50.0  # fallback when daily_df omitted
        atr_pct = 2.0
        ker = 0.50

    metrics: Dict[str, Any] = {
        "symbol": clean_sym,
        "ltp": round(calc_ltp, 2),
        "turnover_cr": round(turnover_cr, 2),
        "atr_pct": round(atr_pct, 2),
        "ker": round(ker, 3),
        "rvol": round(rvol or 1.0, 2),
    }

    # 1. Price floor gate
    if calc_ltp < min_price:
        reason = f"LTP ₹{calc_ltp:.1f} < ₹{min_price:.0f} floor"
        logger.debug("[%s] Dropped by Price Floor: %s", clean_sym, reason)
        return False, reason, metrics

    # 2. 20-Day Average Daily Turnover gate
    if turnover_cr < min_turnover_cr:
        reason = f"20D Avg Turnover ₹{turnover_cr:.1f}Cr < ₹{min_turnover_cr:.0f}Cr threshold"
        logger.debug("[%s] Dropped by Turnover Filter: %s", clean_sym, reason)
        return False, reason, metrics

    # 3. Daily ATR% volatility expansion gate
    if atr_pct < min_atr_pct:
        reason = f"Daily ATR% {atr_pct:.2f}% < {min_atr_pct:.1f}% threshold (Insufficient Volatility)"
        logger.debug("[%s] Dropped by ATR% Filter: %s", clean_sym, reason)
        return False, reason, metrics

    # 4. Kaufman Efficiency Ratio (Daily, N=20) trend regime gate
    if ker < min_ker:
        reason = f"KER {ker:.3f} < {min_ker:.2f} threshold (High Chop)"
        logger.info(
            "[%s] Dropped by KER Filter: ER=%.3f < %.2f threshold (High Chop)",
            clean_sym,
            ker,
            min_ker,
        )
        return False, reason, metrics

    # 5. Morning RVOL gate (active at or after 09:45 IST)
    eval_time = current_time or datetime.datetime.now().time()
    if rvol is not None and eval_time >= datetime.time(9, 45):
        if rvol < min_rvol:
            reason = f"Morning RVOL {rvol:.2f} < {min_rvol:.1f} threshold"
            logger.debug("[%s] Dropped by Morning RVOL Filter: %s", clean_sym, reason)
            return False, reason, metrics

    logger.info(
        "[%s] PASSED Universe Evaluation: LTP=₹%.1f, Turnover=₹%.1fCr, ATR%%=%.2f%%, KER=%.3f, RVOL=%.2f",
        clean_sym,
        calc_ltp,
        turnover_cr,
        atr_pct,
        ker,
        metrics["rvol"],
    )
    return True, "PASSED", metrics


class DynamicScreener:
    def __init__(self):
        self.daily_watchlist: List[str] = []
        self.screener_stats: Dict[str, Dict[str, Any]] = {}
        self.last_funnel_stats: Dict[str, Any] = {}
        self.daily_metrics_cache: Dict[str, Dict[str, Any]] = {}
        self._last_macro_eval_date: Optional[datetime.date] = None
        self.last_run_successful: bool = True

    def get_stock_stats(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieve latest calculated screener metrics for a symbol."""
        clean = symbol.replace("NSE:", "").replace("-EQ", "").strip().upper()
        return self.screener_stats.get(clean)

    def _calculate_day_fraction(self) -> float:
        """Calculate the fraction of the regular market day (9:15-15:30) elapsed."""
        now = datetime.datetime.now()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

        if now < market_open:
            minutes_elapsed = 15.0  # pre-open / early morning baseline
        elif now > market_close:
            minutes_elapsed = 375.0  # full day (375 minutes total)
        else:
            minutes_elapsed = max(10.0, (now - market_open).total_seconds() / 60.0)

        return min(1.0, max(0.05, minutes_elapsed / 375.0))

    def precompute_macro_regimes(
        self,
        universe: Optional[List[str]] = None,
        daily_data_map: Optional[Dict[str, pd.DataFrame]] = None,
        min_price: float = 150.0,
        min_turnover_cr: float = 40.0,
        min_atr_pct: float = 1.5,
        min_ker: float = 0.35,
    ) -> Dict[str, Dict[str, Any]]:
        """Pre-market (before 09:15 IST) macro regime evaluation across candidate universe.

        Filters out noisy, mean-reverting stocks using Daily Kaufman Efficiency Ratio (N=20)
        and caches results for subsequent daytime screening runs.
        """
        if universe is None:
            fno = get_fno_universe()
            universe = [s for s in NIFTY_50 if s in fno] + [
                s for s in fno if s not in NIFTY_50
            ]

        today = datetime.date.today()
        passed_cache: Dict[str, Dict[str, Any]] = {}

        for sym in universe:
            clean_sym = sym.replace("NSE:", "").replace("-EQ", "").strip().upper()
            if clean_sym in DEFAULT_BLACKLIST:
                continue

            daily_df = daily_data_map.get(clean_sym) if daily_data_map else None

            passed, _reason, metrics = evaluate_universe_candidate(
                symbol=clean_sym,
                daily_df=daily_df,
                min_price=min_price,
                min_turnover_cr=min_turnover_cr,
                min_atr_pct=min_atr_pct,
                min_ker=min_ker,
            )

            if passed:
                passed_cache[clean_sym] = metrics

        self.daily_metrics_cache = passed_cache
        self._last_macro_eval_date = today
        logger.info(
            "Precomputed Macro Regimes: %d/%d candidates passed KER >= %.2f and liquidity gates.",
            len(passed_cache),
            len(universe),
            min_ker,
        )
        return passed_cache

    def generate_daily_watchlist(
        self,
        universe: Optional[List[str]] = None,
        limit: int = 25,  # reduced from 35: higher quality, lower fee drag
        min_price: float = 50.0,
        max_price: float = 100_000.0,
        daily_data_map: Optional[Dict[str, pd.DataFrame]] = None,
        min_ker: float = 0.35,
    ) -> List[str]:
        """AI/Algorithmic screener that selects the top high-momentum F&O stocks to trade today.

        Ranks stocks using:
        1. Macro Regime Gate: Kaufman Efficiency Ratio (KER >= 0.35 on Daily bars).
        2. Intraday Momentum & Directional Velocity (open-to-LTP, close-to-LTP, range expansion).
        3. Relative Volume (RVOL) vs cross-universe pace and time-of-day expected run-rate.
        4. High Institutional Participation (turnover in Crores and absorption near day extremes).
        5. Quality Filter (excludes penny stocks and blacklisted structural traps).
        """
        if universe is None:
            # Order F&O universe by high-liquidity NIFTY 50 first so fallback is high-quality
            fno = get_fno_universe()
            universe = [s for s in NIFTY_50 if s in fno] + [
                s for s in fno if s not in NIFTY_50
            ]

        self.last_run_successful = False
        try:
            # Batch instruments into chunks of 50 to respect SmartAPI payload limits
            quotes: dict = {}
            chunk_size = 50
            for i in range(0, len(universe), chunk_size):
                chunk = universe[i : i + chunk_size]
                instruments = [f"NSE:{symbol}" for symbol in chunk]
                batch_res = None
                for attempt in range(3):
                    try:
                        batch_res = smart_api_client.get_quote(instruments)
                        if batch_res:
                            break
                    except Exception as ex:
                        logger.warning(
                            "Attempt %d/3 failed to fetch quotes for chunk (%d symbols): %s",
                            attempt + 1,
                            len(chunk),
                            ex,
                        )
                    time.sleep(1.5)
                if batch_res:
                    quotes.update(batch_res)
                time.sleep(0.5)

            if not quotes:
                logger.warning(
                    "Dynamic screener received empty quotes from SmartAPI; falling back to universe defaults."
                )
                return universe[:limit]

            day_fraction = self._calculate_day_fraction()

            # First pass: parse valid quotes and collect volume & turnover
            parsed_candidates = []
            for symbol, data in quotes.items():
                if "last_price" not in data or "ohlc" not in data:
                    continue

                ltp = float(data.get("last_price") or 0.0)
                ohlc = data.get("ohlc", {})
                open_price = float(ohlc.get("open") or 0.0)
                high_price = float(ohlc.get("high") or 0.0)
                low_price = float(ohlc.get("low") or 0.0)
                prev_close = float(ohlc.get("close") or 0.0)
                volume = float(data.get("volume") or 0.0)

                # Avoid unquoted, flat, or zero-volume stocks
                if prev_close <= 0 or open_price <= 0 or ltp <= 0:
                    continue

                clean_symbol = (
                    symbol.replace("NSE:", "").replace("-EQ", "").strip().upper()
                )
                if clean_symbol in DEFAULT_BLACKLIST:
                    continue

                if ltp < min_price or ltp > max_price:
                    continue

                turnover = ltp * volume

                parsed_candidates.append(
                    {
                        "symbol": clean_symbol,
                        "ltp": ltp,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "prev_close": prev_close,
                        "volume": volume,
                        "turnover": turnover,
                    }
                )

            if not parsed_candidates:
                return universe[:limit]

            # Cross-universe volume and turnover statistics for relative normalization
            all_volumes = [c["volume"] for c in parsed_candidates if c["volume"] > 0]
            median_vol = float(np.median(all_volumes)) if all_volumes else 500_000.0
            median_vol = max(10_000.0, median_vol)

            all_turnovers = [
                c["turnover"] for c in parsed_candidates if c["turnover"] > 0
            ]
            median_turnover = (
                float(np.median(all_turnovers)) if all_turnovers else 10_000_000.0
            )
            median_turnover = max(1_000_000.0, median_turnover)

            scored_stocks = []
            stats_map: Dict[str, Dict[str, Any]] = {}

            for c in parsed_candidates:
                ltp = c["ltp"]
                open_price = c["open"]
                high_price = c["high"]
                low_price = c["low"]
                prev_close = c["prev_close"]
                volume = c["volume"]
                turnover = c["turnover"]
                symbol = c["symbol"]

                # ── 1. Relative Volume (RVOL) ────────────────────────────────
                rvol_universe = volume / median_vol
                expected_tod_vol = max(25_000.0, 1_000_000.0 * day_fraction)
                rvol_tod = volume / expected_tod_vol
                rvol = float(np.clip(0.6 * rvol_universe + 0.4 * rvol_tod, 0.2, 5.0))

                # ── 2. Kaufman Efficiency Ratio Macro Check (if daily data available)
                daily_df = daily_data_map.get(symbol) if daily_data_map else None
                ker_val = 0.50
                if daily_df is not None:
                    ker_val = calculate_kaufman_efficiency_ratio(
                        daily_df["close"], period=20
                    )
                    if ker_val < min_ker:
                        logger.info(
                            "[%s] Dropped by KER Filter: ER=%.3f < %.2f threshold (High Chop)",
                            symbol,
                            ker_val,
                            min_ker,
                        )
                        continue
                elif symbol in self.daily_metrics_cache:
                    ker_val = self.daily_metrics_cache[symbol].get("ker", 0.50)
                    if ker_val < min_ker:
                        logger.info(
                            "[%s] Dropped by KER Filter: ER=%.3f < %.2f threshold (High Chop)",
                            symbol,
                            ker_val,
                            min_ker,
                        )
                        continue

                # ── 3. Momentum & Directional Velocity ───────────────────────
                change_pct = abs(ltp - prev_close) / prev_close * 100.0
                open_to_ltp_pct = abs(ltp - open_price) / open_price * 100.0
                gap_pct = abs(open_price - prev_close) / prev_close * 100.0
                day_range = max(0.0, high_price - low_price)
                range_pct = (day_range / prev_close * 100.0) if prev_close > 0 else 0.0

                # Healthy opening gaps (< 1.8%) contribute moderate momentum,
                # but large exhaustion gaps (>= 1.8%) are penalized because intraday expansion
                # is already spent at market open.
                if gap_pct < 1.8:
                    gap_contribution = gap_pct * 0.6
                else:
                    # Exhaustion penalty for large gaps
                    gap_contribution = max(-2.0, 1.0 - (gap_pct - 1.8) * 1.5)

                raw_momentum = (
                    (change_pct * 1.5) + (open_to_ltp_pct * 2.0) + gap_contribution
                )

                # RVOL multiplier: boosts momentum if active volume, dampens if low liquidity
                rvol_multiplier = 0.5 + (0.5 * min(3.0, rvol))

                # ── 4. High Institutional Participation ──────────────────────
                turnover_cr = turnover / 10_000_000.0
                turnover_score = min(4.0, turnover_cr / 20.0) + min(
                    2.0, (turnover / median_turnover) * 0.5
                )

                if day_range > 0:
                    pos_in_range = (ltp - low_price) / day_range
                    absorption = abs(pos_in_range - 0.5) * 2.0
                else:
                    absorption = 0.0

                expansion_score = min(4.0, range_pct * 1.2)
                inst_participation = (
                    (turnover_score * 1.2) + (absorption * 2.0) + expansion_score
                )

                # ── 5. Relative Strength Score (multi-day momentum vs universe) ───
                # NSE research: top RS rank stocks produce 2.3× better expectancy
                # RS = 5D_return×0.4 + 10D_return×0.3 + 20D_return×0.3 (price momentum rank)
                rs_score = 0.0
                if daily_df is not None and len(daily_df) >= 21:
                    try:
                        close_arr = daily_df["close"].astype(float)
                        ret_5d = float(
                            (close_arr.iloc[-1] - close_arr.iloc[-6]) / close_arr.iloc[-6] * 100.0
                        ) if len(close_arr) >= 6 else 0.0
                        ret_10d = float(
                            (close_arr.iloc[-1] - close_arr.iloc[-11]) / close_arr.iloc[-11] * 100.0
                        ) if len(close_arr) >= 11 else 0.0
                        ret_20d = float(
                            (close_arr.iloc[-1] - close_arr.iloc[-21]) / close_arr.iloc[-21] * 100.0
                        ) if len(close_arr) >= 21 else 0.0
                        rs_score = (
                            (ret_5d * 0.4) + (ret_10d * 0.3) + (ret_20d * 0.3)
                        )
                    except Exception:
                        rs_score = 0.0
                # Normalise RS to a 0-3 additive bonus (cap at +3 to not overwhelm intraday factors)
                rs_bonus = float(np.clip(rs_score * 0.3, -1.5, 3.0))

                # ── 6. Composite In-Play Score (Weighted with KER + RS) ────────────
                ker_boost = 0.8 + (0.4 * ker_val)  # Higher KER smoothly enhances score
                composite_score = (
                    (raw_momentum * rvol_multiplier) + inst_participation + rs_bonus
                ) * ker_boost

                stock_entry = {
                    "symbol": symbol,
                    "score": round(composite_score, 2),
                    "rvol": round(rvol, 2),
                    "ker": round(ker_val, 3),
                    "rs_score": round(rs_score, 2),
                    "volume": volume,
                    "turnover_cr": round(turnover_cr, 2),
                    "change_pct": round(change_pct, 2),
                    "intraday_pct": round(open_to_ltp_pct, 2),
                    "range_pct": round(range_pct, 2),
                    "absorption": round(absorption, 2),
                }
                scored_stocks.append(stock_entry)
                stats_map[symbol] = stock_entry

            scored_stocks.sort(key=lambda x: x["score"], reverse=True)
            top_stocks = [stock["symbol"] for stock in scored_stocks[:limit]]
            self.daily_watchlist = top_stocks
            self.screener_stats = stats_map
            self.last_run_successful = bool(top_stocks)

            passed_ker_count = sum(1 for s in scored_stocks if s.get("ker", 0) >= min_ker)
            passed_rvol_count = sum(1 for s in scored_stocks if s.get("rvol", 0) >= 1.8)
            passed_turnover_count = sum(1 for s in scored_stocks if s.get("turnover_cr", 0) >= 40.0)

            self.last_funnel_stats = {
                "total_universe": len(universe),
                "quotes_received": len(quotes),
                "valid_candidates": len(parsed_candidates),
                "passed_ker": passed_ker_count,
                "passed_rvol": passed_rvol_count,
                "passed_turnover": passed_turnover_count,
                "shortlisted_count": len(top_stocks),
                "top_scored": scored_stocks[:7],
            }

            top_summary = ", ".join(
                f"{s['symbol']}(score={s['score']}, KER={s['ker']}, RS={s.get('rs_score', 0):.1f}%, rvol={s['rvol']}x, to={s['turnover_cr']}Cr)"
                for s in scored_stocks[: min(5, len(scored_stocks))]
            )
            logger.info(
                "Dynamic Screener (KER≥%.2f + RS ranking) selected top %d stocks: %s",
                min_ker,
                len(top_stocks),
                top_summary,
            )
            return top_stocks if top_stocks else universe[:limit]

        except Exception as e:
            logger.error("Failed to generate dynamic F&O watchlist: %s", e)
            self.last_run_successful = False
            return universe[:limit]


screener_engine = DynamicScreener()
