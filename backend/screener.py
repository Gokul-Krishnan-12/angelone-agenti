from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional

import numpy as np

from .fno_universe import get_fno_universe
from .nifty_universe import NIFTY_50
from .smartapi_client import smart_api_client

logger = logging.getLogger(__name__)


class DynamicScreener:
    def __init__(self):
        self.daily_watchlist: List[str] = []
        self.screener_stats: Dict[str, Dict[str, Any]] = {}

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

    def generate_daily_watchlist(
        self,
        universe: Optional[List[str]] = None,
        limit: int = 35,
        min_price: float = 50.0,
        max_price: float = 4000.0,
    ) -> List[str]:
        """AI/Algorithmic screener that selects the top high-momentum F&O stocks to trade today.

        Ranks stocks using:
        1. Intraday Momentum & Directional Velocity (open-to-LTP, close-to-LTP, range expansion).
        2. Relative Volume (RVOL) vs cross-universe pace and time-of-day expected run-rate.
        3. High Institutional Participation (turnover in Crores and absorption near day extremes).
        4. Quality Filter (excludes sub-₹50 penny stocks and ultra-high denomination stocks).
        """
        if universe is None:
            # Order F&O universe by high-liquidity NIFTY 50 first so fallback is high-quality
            fno = get_fno_universe()
            universe = [s for s in NIFTY_50 if s in fno] + [
                s for s in fno if s not in NIFTY_50
            ]

        try:
            # Batch instruments into chunks of 50 to respect SmartAPI payload limits
            quotes: dict = {}
            chunk_size = 50
            for i in range(0, len(universe), chunk_size):
                chunk = universe[i : i + chunk_size]
                instruments = [f"NSE:{symbol}" for symbol in chunk]
                batch_res = smart_api_client.get_quote(instruments)
                if batch_res:
                    quotes.update(batch_res)

            if not quotes:
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

                # Quality Universe Gate: avoid sub-₹50 penny stocks and ultra-high denomination stocks
                if ltp < min_price or ltp > max_price:
                    continue

                clean_symbol = (
                    symbol.replace("NSE:", "").replace("-EQ", "").strip().upper()
                )
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

                # ── 1. Momentum & Directional Velocity ───────────────────────
                change_pct = abs(ltp - prev_close) / prev_close * 100.0
                open_to_ltp_pct = abs(ltp - open_price) / open_price * 100.0
                gap_pct = abs(open_price - prev_close) / prev_close * 100.0
                day_range = max(0.0, high_price - low_price)
                range_pct = (day_range / prev_close * 100.0) if prev_close > 0 else 0.0

                raw_momentum = (
                    (change_pct * 1.5) + (open_to_ltp_pct * 2.0) + (gap_pct * 0.6)
                )

                # ── 2. Relative Volume (RVOL) ────────────────────────────────
                # Volume relative to universe median at current time
                rvol_universe = volume / median_vol

                # Volume relative to time-of-day expected baseline (1M daily shares baseline)
                expected_tod_vol = max(25_000.0, 1_000_000.0 * day_fraction)
                rvol_tod = volume / expected_tod_vol

                # Combined RVOL metric clamped between 0.2 and 5.0
                rvol = float(np.clip(0.6 * rvol_universe + 0.4 * rvol_tod, 0.2, 5.0))

                # RVOL multiplier: boosts momentum if active volume, dampens if low liquidity
                rvol_multiplier = 0.5 + (0.5 * min(3.0, rvol))

                # ── 3. High Institutional Participation ──────────────────────
                # Turnover in Crores (1 Cr = 10^7 INR)
                turnover_cr = turnover / 10_000_000.0
                turnover_score = min(4.0, turnover_cr / 20.0) + min(
                    2.0, (turnover / median_turnover) * 0.5
                )

                # Institutional Absorption: is price pinned near day high or low?
                if day_range > 0:
                    pos_in_range = (ltp - low_price) / day_range
                    absorption = abs(pos_in_range - 0.5) * 2.0
                else:
                    absorption = 0.0

                # Range expansion score (institutional range driver)
                expansion_score = min(4.0, range_pct * 1.2)

                inst_participation = (
                    (turnover_score * 1.2) + (absorption * 2.0) + expansion_score
                )

                # ── 4. Composite In-Play Score ────────────────────────────────
                composite_score = (raw_momentum * rvol_multiplier) + inst_participation

                stock_entry = {
                    "symbol": symbol,
                    "score": round(composite_score, 2),
                    "rvol": round(rvol, 2),
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

            top_summary = ", ".join(
                f"{s['symbol']}(score={s['score']}, rvol={s['rvol']}x, to={s['turnover_cr']}Cr)"
                for s in scored_stocks[: min(5, len(scored_stocks))]
            )
            logger.info(
                "Dynamic Screener selected top %d high-momentum & institutional in-play stocks: %s",
                len(top_stocks),
                top_summary,
            )
            return top_stocks if top_stocks else universe[:limit]

        except Exception as e:
            logger.error("Failed to generate dynamic F&O watchlist: %s", e)
            return universe[:limit]


screener_engine = DynamicScreener()
