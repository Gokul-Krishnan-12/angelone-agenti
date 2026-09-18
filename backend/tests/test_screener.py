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


def test_trading_engine_periodic_dynamic_rescreening():
    """Verify that trading_engine re-screens every 30 minutes and preserves open trades."""
    from backend.trading_engine import TradingEngine

    engine = TradingEngine()
    assert engine.screener_interval == 1800  # 30 minutes default
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
            with patch("backend.ticker.ticker_manager.subscribe"):
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

                        # 2. Immediate second scan: screener should NOT re-run (< 30 min)
                        mock_scan.reset_mock()
                        engine.scan_and_trade()
                        assert call_count == 1
                        assert mock_scan.called

                        # 3. Simulate 1801 seconds (30 minutes + 1 second) passing: screener SHOULD re-run
                        engine._last_screener_time -= 1801
                        mock_scan.reset_mock()
                        engine.scan_and_trade()
                        assert call_count == 2
                        assert "EXISTING_HOLDING" in engine.dynamic_watchlist
                        assert engine.dynamic_watchlist[0] == "STOCK_2_0"
                        assert mock_scan.called


def test_screener_window_strictly_930_to_1430():
    """Verify that screener only runs between 09:30 and 14:30 IST on trading days."""
    import datetime
    from unittest.mock import patch
    from backend.trading_engine import TradingEngine

    engine = TradingEngine()
    engine.dynamic_watchlist = None
    call_count = 0

    def mock_generate_watchlist(universe=None, limit=35):
        nonlocal call_count
        call_count += 1
        return [f"STOCK_{call_count}_{i}" for i in range(limit)]

    # Times: 09:18 AM (before 09:30), 09:30 AM (active window), 14:45 PM (after 14:30)
    fake_0918 = datetime.datetime(2025, 1, 1, 9, 18, 0)
    fake_0930 = datetime.datetime(2025, 1, 1, 9, 30, 5)
    fake_1445 = datetime.datetime(2025, 1, 1, 14, 45, 0)

    with patch("backend.risk_manager.risk_manager.can_trade", return_value=(True, "OK")):
        with patch.object(engine, "_reevaluate_positions"):
            with patch("backend.ticker.ticker_manager.subscribe"):
                with patch("backend.screener.screener_engine.generate_daily_watchlist", side_effect=mock_generate_watchlist):
                    with patch("backend.scanner.scanner.scan_watchlist"):
                        with patch("backend.market_hours.is_trading_day", return_value=True):
                            # 1. Startup at 09:18 AM — must NOT run (< 09:30)
                            with patch("datetime.datetime") as mock_dt:
                                mock_dt.now.return_value = fake_0918
                                mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
                                engine.scan_and_trade()

                            assert call_count == 0
                            assert "09:30" not in engine._screener_slots_completed

                            # 2. Clock reaches 09:30 AM — MUST run
                            with patch("datetime.datetime") as mock_dt:
                                mock_dt.now.return_value = fake_0930
                                mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
                                engine.scan_and_trade()

                            assert call_count == 1
                            assert "09:30" in engine._screener_slots_completed

                            # 3. Clock reaches 14:45 PM — must NOT run (> 14:30)
                            with patch("datetime.datetime") as mock_dt:
                                mock_dt.now.return_value = fake_1445
                                mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
                                engine.scan_and_trade()

                            # Call count remains 1
                            assert call_count == 1


def test_trading_engine_manual_scan_activity_logging():
    """Verify that manual_scan generates activity logs with the shortlisted stocks."""
    from backend.trading_engine import TradingEngine

    engine = TradingEngine()
    engine.active_trades["TATAMOTORS"] = {"sl": 900.0, "target": 950.0}

    logs_emitted = []

    def mock_push_log(msg, level="info"):
        logs_emitted.append((msg, level))

    with patch.object(engine, "_push_log", side_effect=mock_push_log):
        with patch("backend.ticker.ticker_manager.subscribe"):
            with patch(
                "backend.screener.screener_engine.generate_daily_watchlist",
                return_value=["RELIANCE", "INFY", "TCS"],
            ):
                with patch("backend.scanner.scanner.scan_watchlist", return_value=[]):
                    signals = engine.manual_scan()
                    assert signals == []
                # Watchlist should contain screened stocks + existing holdings
                assert "RELIANCE" in engine.dynamic_watchlist
                assert "TATAMOTORS" in engine.dynamic_watchlist
                # Activity log must include the manual scan trigger and the shortlisted stocks
                assert any("Manual Scan requested" in msg for msg, lvl in logs_emitted)
                assert any("Dynamic Watchlist updated [Manual Scan]" in msg for msg, lvl in logs_emitted)
                assert any("RELIANCE, INFY, TCS" in msg for msg, lvl in logs_emitted)
                assert any("Manual scan complete" in msg for msg, lvl in logs_emitted)


def test_clock_screener_single_message_logging():
    """Verify that run_clock_screener generates strictly one clean message at 30-min intervals."""
    from backend.trading_engine import TradingEngine
    from backend.screener import screener_engine

    engine = TradingEngine()
    logs_emitted = []

    def mock_push_log(msg, level="info"):
        logs_emitted.append((msg, level))

    screener_engine.last_funnel_stats = {
        "total_universe": 185,
        "quotes_received": 185,
        "valid_candidates": 180,
        "passed_ker": 45,
        "passed_rvol": 38,
        "passed_turnover": 52,
        "shortlisted_count": 35,
    }
    screener_engine.screener_stats = {
        "RELIANCE": {"ker": 0.48, "rvol": 2.2, "turnover_cr": 150.0, "change_pct": 1.5, "score": 88.5},
        "INFY": {"ker": 0.42, "rvol": 1.9, "turnover_cr": 95.0, "change_pct": -0.8, "score": 82.0},
    }

    with patch.object(engine, "_push_log", side_effect=mock_push_log):
        with patch("backend.ticker.ticker_manager.subscribe"):
            with patch.object(
                screener_engine,
                "generate_daily_watchlist",
                return_value=["RELIANCE", "INFY"],
            ):
                engine.run_clock_screener(force=True, slot_label_override="10:00 IST")

    # Strictly one single log for the 30-min scan
    assert len(logs_emitted) == 1
    msg, lvl = logs_emitted[0]
    assert msg.startswith("⏱️ 30-Min Scan [10:00 IST] complete. Next autonomous scan scheduled at:")
    assert lvl == "info"
    # Verify no multi-line funnel or stock breakdown spam
    assert not any("Funnel" in m for m, _ in logs_emitted)
    assert not any("Breakdown" in m for m, _ in logs_emitted)



def test_kaufman_efficiency_ratio_trending_series():
    """Straight line trending series must yield KER == 1.0."""
    import numpy as np
    import pandas as pd

    from backend.screener import calculate_kaufman_efficiency_ratio

    # 21 consecutive bars increasing by 5.0 each day
    trend_series = pd.Series(np.linspace(100.0, 200.0, 21))
    ker = calculate_kaufman_efficiency_ratio(trend_series, period=20)
    assert abs(ker - 1.0) < 1e-6


def test_kaufman_efficiency_ratio_noisy_mean_reverting():
    """Noisy sinusoidal mean-reverting series must yield KER < 0.25."""
    import numpy as np
    import pandas as pd

    from backend.screener import calculate_kaufman_efficiency_ratio

    np.random.seed(42)
    t = np.linspace(0, 4 * np.pi, 25)
    noisy_series = pd.Series(100.0 + 6.0 * np.sin(t) + np.random.normal(0, 0.4, 25))
    ker = calculate_kaufman_efficiency_ratio(noisy_series, period=20)
    assert ker < 0.25


def test_kaufman_efficiency_ratio_zero_movement():
    """Flat series with zero volatility must return 0.0 without ZeroDivisionError."""
    import pandas as pd

    from backend.screener import calculate_kaufman_efficiency_ratio

    flat_series = pd.Series([150.0] * 30)
    ker = calculate_kaufman_efficiency_ratio(flat_series, period=20)
    assert ker == 0.0


def test_kaufman_efficiency_ratio_edge_cases():
    """Edge cases (None, empty, short history, NaNs) return 0.0 safely."""
    import pandas as pd

    from backend.screener import calculate_kaufman_efficiency_ratio

    assert calculate_kaufman_efficiency_ratio(None, 20) == 0.0
    assert calculate_kaufman_efficiency_ratio(pd.Series([]), 20) == 0.0
    assert calculate_kaufman_efficiency_ratio(pd.Series([100.0, 105.0]), 20) == 0.0


def test_evaluate_universe_candidate_pipeline():
    """Verify all 5 quantitative macro gates in evaluate_universe_candidate."""
    import datetime

    import numpy as np
    import pandas as pd

    from backend.screener import evaluate_universe_candidate

    n = 25
    # 1. High-momentum, high-liquidity valid candidate
    df_valid = pd.DataFrame(
        {
            "close": np.linspace(200.0, 260.0, n),
            "high": np.linspace(205.0, 265.0, n),
            "low": np.linspace(195.0, 255.0, n),
            "volume": [2_000_000.0] * n,  # Turnover = 200 * 2M = 40 Cr
        }
    )
    passed, reason, metrics = evaluate_universe_candidate(
        symbol="PAYTM",
        daily_df=df_valid,
        rvol=2.2,
        current_time=datetime.time(10, 0),
    )
    assert passed
    assert reason == "PASSED"
    assert metrics["ker"] > 0.8
    assert metrics["turnover_cr"] >= 40.0
    assert metrics["atr_pct"] >= 1.5

    # 2. Rejection: Price floor breached (LTP < ₹150)
    df_cheap = df_valid.copy()
    df_cheap["close"] = np.linspace(50.0, 90.0, n)
    passed_cheap, reason_cheap, _ = evaluate_universe_candidate(
        symbol="CHEAP", daily_df=df_cheap, min_price=150.0
    )
    assert not passed_cheap
    assert "floor" in reason_cheap

    # 3. Rejection: Low Turnover (< ₹40 Cr)
    df_illiquid = df_valid.copy()
    df_illiquid["volume"] = [50_000.0] * n  # Low turnover
    passed_illiquid, reason_illiquid, _ = evaluate_universe_candidate(
        symbol="ILLIQUID", daily_df=df_illiquid, min_turnover_cr=40.0
    )
    assert not passed_illiquid
    assert "Turnover" in reason_illiquid

    # 4. Rejection: High Chop (KER < 0.28)
    t = np.linspace(0, 4 * np.pi, n)
    df_choppy = pd.DataFrame(
        {
            "close": 200.0 + 5.0 * np.sin(t),
            "high": 205.0 + 5.0 * np.sin(t),
            "low": 195.0 + 5.0 * np.sin(t),
            "volume": [3_000_000.0] * n,  # High turnover (~60 Cr) so it tests KER gate
        }
    )
    passed_chop, reason_chop, m_chop = evaluate_universe_candidate(
        symbol="ICICIGI", daily_df=df_choppy, min_ker=0.28
    )
    assert not passed_chop
    assert "KER" in reason_chop
    assert m_chop["ker"] < 0.28

    # 5. Rejection: Morning RVOL < 1.8 at 09:45
    passed_rvol, reason_rvol, _ = evaluate_universe_candidate(
        symbol="LAZY",
        daily_df=df_valid,
        rvol=1.2,
        current_time=datetime.time(9, 50),
        min_rvol=1.8,
    )
    assert not passed_rvol
    assert "Morning RVOL" in reason_rvol


def test_screener_drops_low_ker_candidates_with_daily_map():
    """Verify DynamicScreener filters out candidates when daily_data_map has low KER."""
    from unittest.mock import patch

    import numpy as np
    import pandas as pd

    from backend.screener import DynamicScreener

    screener = DynamicScreener()

    n = 25
    # Candidate A: High KER
    df_trend = pd.DataFrame(
        {
            "close": np.linspace(200.0, 260.0, n),
            "high": np.linspace(205.0, 265.0, n),
            "low": np.linspace(195.0, 255.0, n),
            "volume": [2_000_000.0] * n,
        }
    )
    # Candidate B: Low KER (choppy oscillation)
    t = np.linspace(0, 4 * np.pi, n)
    df_chop = pd.DataFrame(
        {
            "close": 200.0 + 5.0 * np.sin(t),
            "high": 205.0 + 5.0 * np.sin(t),
            "low": 195.0 + 5.0 * np.sin(t),
            "volume": [2_000_000.0] * n,
        }
    )

    daily_map = {"TRENDING": df_trend, "CHOPPY": df_chop}
    mock_quotes = {
        "NSE:TRENDING": {
            "last_price": 260.0,
            "volume": 2000000,
            "ohlc": {"open": 255.0, "high": 262.0, "low": 254.0, "close": 255.0},
        },
        "NSE:CHOPPY": {
            "last_price": 200.0,
            "volume": 2000000,
            "ohlc": {"open": 199.0, "high": 202.0, "low": 198.0, "close": 199.0},
        },
    }

    with patch("backend.screener.smart_api_client.get_quote", return_value=mock_quotes):
        watchlist = screener.generate_daily_watchlist(
            universe=["TRENDING", "CHOPPY"],
            daily_data_map=daily_map,
            min_ker=0.28,
        )
        assert "TRENDING" in watchlist
        assert "CHOPPY" not in watchlist
