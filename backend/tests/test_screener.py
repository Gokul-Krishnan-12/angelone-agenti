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


def test_screener_rvol_and_institutional_participation():
    """Verify that a stock with high RVOL and institutional turnover beats low-volume stock."""
    screener = DynamicScreener()

    # Both stocks move +3%, but HIGH_INST has 5M volume (huge turnover & RVOL),
    # while LOW_VOL has only 5,000 shares (illiquid).
    mock_quotes = {
        "NSE:LOW_VOL": {
            "last_price": 103.0,
            "volume": 5000,
            "ohlc": {"open": 100.0, "high": 103.5, "low": 99.5, "close": 100.0},
        },
        "NSE:HIGH_INST": {
            "last_price": 103.0,
            "volume": 5000000,
            "ohlc": {"open": 100.0, "high": 103.5, "low": 99.5, "close": 100.0},
        },
    }

    with patch("backend.screener.smart_api_client.get_quote", return_value=mock_quotes):
        top = screener.generate_daily_watchlist(
            universe=["LOW_VOL", "HIGH_INST"], limit=2
        )
        assert top[0] == "HIGH_INST"
        assert top[1] == "LOW_VOL"

        stats_inst = screener.get_stock_stats("HIGH_INST")
        stats_low = screener.get_stock_stats("LOW_VOL")

        assert stats_inst is not None
        assert stats_low is not None
        assert stats_inst["rvol"] > stats_low["rvol"]
        assert stats_inst["turnover_cr"] > stats_low["turnover_cr"]
        assert stats_inst["score"] > stats_low["score"]


def test_trading_engine_hourly_dynamic_rescreening():
    """Verify that trading_engine re-screens every 1 hour and preserves open trades."""
    from backend.trading_engine import TradingEngine

    engine = TradingEngine()
    engine.screener_interval = 3600  # 1 hour
    engine.active_trades["EXISTING_HOLDING"] = {"sl": 100.0, "target": 110.0}

    call_count = 0

    def mock_generate_watchlist(universe=None, limit=35):
        nonlocal call_count
        call_count += 1
        return [f"STOCK_{call_count}_{i}" for i in range(limit)]

    with patch(
        "backend.risk_manager.risk_manager.can_trade", return_value=(True, "OK")
    ):
        with patch.object(engine, "_reevaluate_positions"):
            with patch(
                "backend.screener.screener_engine.generate_daily_watchlist",
                side_effect=mock_generate_watchlist,
            ):
                with patch("backend.scanner.scanner.scan_watchlist") as mock_scan:
                    # 1. First scan: screener should run because dynamic_watchlist is empty
                    engine.scan_and_trade()
                    assert call_count == 1
                    assert "EXISTING_HOLDING" in engine.dynamic_watchlist
                    assert engine.dynamic_watchlist[0] == "STOCK_1_0"
                    assert mock_scan.called

                    # 2. Immediate second scan: screener should NOT re-run (< 1 hour)
                    mock_scan.reset_mock()
                    engine.scan_and_trade()
                    assert call_count == 1
                    assert mock_scan.called

                    # 3. Simulate 3601 seconds (1 hour + 1 second) passing: screener SHOULD re-run
                    engine._last_screener_time -= 3601
                    mock_scan.reset_mock()
                    engine.scan_and_trade()
                    assert call_count == 2
                    assert "EXISTING_HOLDING" in engine.dynamic_watchlist
                    assert engine.dynamic_watchlist[0] == "STOCK_2_0"
                    assert mock_scan.called
