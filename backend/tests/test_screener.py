"""Tests for DynamicScreener ranking top 20 momentum F&O stocks."""

from __future__ import annotations

from unittest.mock import patch

from backend.screener import DynamicScreener


def test_screener_ranks_top_momentum():
    screener = DynamicScreener()

    mock_quotes = {
        "NSE:STAGNANT": {
            "last_price": 100.2,
            "volume": 50000,
            "ohlc": {"open": 100.0, "high": 100.5, "low": 99.8, "close": 100.0},
        },
        "NSE:HIGH_MOVER": {
            "last_price": 540.0,
            "volume": 2000000,
            "ohlc": {"open": 505.0, "high": 545.0, "low": 500.0, "close": 500.0},
        },
        "NSE:MODERATE_MOVER": {
            "last_price": 205.0,
            "volume": 300000,
            "ohlc": {"open": 200.0, "high": 208.0, "low": 199.0, "close": 200.0},
        },
    }

    with patch("backend.screener.smart_api_client.get_quote", return_value=mock_quotes):
        top = screener.generate_daily_watchlist(
            universe=["STAGNANT", "HIGH_MOVER", "MODERATE_MOVER"], limit=2
        )

        assert len(top) == 2
        # HIGH_MOVER should rank #1 due to massive open-to-LTP and close-to-LTP move
        assert top[0] == "HIGH_MOVER"
        assert top[1] == "MODERATE_MOVER"


def test_screener_handles_empty_quotes():
    screener = DynamicScreener()

    with patch("backend.screener.smart_api_client.get_quote", return_value={}):
        fallback = screener.generate_daily_watchlist(
            universe=["RELIANCE", "TCS", "INFY"], limit=2
        )
        assert fallback == ["RELIANCE", "TCS"]
