from __future__ import annotations

import logging
from typing import List, Optional

from .fno_universe import get_fno_universe
from .smartapi_client import smart_api_client

logger = logging.getLogger(__name__)


class DynamicScreener:
    def __init__(self):
        self.daily_watchlist: List[str] = []

    def generate_daily_watchlist(
        self, universe: Optional[List[str]] = None, limit: int = 20
    ) -> List[str]:
        """
        AI/Algorithmic screener that selects the top high-momentum F&O stocks to trade today.

        Evaluates intraday directional velocity, trend expansion from open, gap percentage,
        and day's range across the F&O universe using batched market data.
        """
        if universe is None:
            universe = get_fno_universe()

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

            scored_stocks = []

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

                # Avoid flat, unquoted, or illiquid stocks
                if prev_close <= 0 or open_price <= 0 or ltp <= 0:
                    continue

                # 1. Total intraday change from previous close (Directional momentum)
                change_pct = abs(ltp - prev_close) / prev_close * 100.0

                # 2. Intraday expansion from open (Active trend velocity)
                open_to_ltp_pct = abs(ltp - open_price) / open_price * 100.0

                # 3. Overnight gap
                gap_pct = abs(open_price - prev_close) / prev_close * 100.0

                # 4. Day's range / expansion
                range_pct = (
                    abs(high_price - low_price) / prev_close * 100.0
                    if high_price >= low_price
                    else 0.0
                )

                # Composite momentum score: high intraday velocity, expansion, and range
                score = (
                    (change_pct * 1.5)
                    + (open_to_ltp_pct * 1.5)
                    + (gap_pct * 0.8)
                    + (range_pct * 1.0)
                )

                clean_symbol = (
                    symbol.replace("NSE:", "").replace("-EQ", "").strip().upper()
                )

                scored_stocks.append(
                    {
                        "symbol": clean_symbol,
                        "score": score,
                        "volume": volume,
                        "change_pct": change_pct,
                        "intraday_pct": open_to_ltp_pct,
                    }
                )

            scored_stocks.sort(key=lambda x: x["score"], reverse=True)
            top_stocks = [stock["symbol"] for stock in scored_stocks[:limit]]
            self.daily_watchlist = top_stocks

            logger.info(
                "Dynamic Screener selected top %d high-momentum F&O stocks: %s",
                len(top_stocks),
                top_stocks,
            )
            return top_stocks if top_stocks else universe[:limit]

        except Exception as e:
            logger.error("Failed to generate dynamic F&O watchlist: %s", e)
            return universe[:limit]


screener_engine = DynamicScreener()
