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
