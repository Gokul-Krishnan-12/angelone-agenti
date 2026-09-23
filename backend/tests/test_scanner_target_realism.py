"""Unit tests for Scanner Intraday Target Realism, Structural Target Preservation, and Gap Exhaustion."""

import pandas as pd
import pytest

from backend.config import config_manager
from backend.scanner import Scanner


def test_structural_target_preserved_for_mean_reversion(monkeypatch):
    """Verify that structural targets (POC in FRVP) are NOT overwritten with synthetic 2.0R targets."""
    scanner = Scanner()
    monkeypatch.setattr(
        config_manager,
        "get_risk_config",
        lambda: {"microstructureFilterEnabled": False, "minStopLossPercent": 1.2, "maxStopLossPercent": 2.4},
    )

    timestamps = pd.date_range("2026-09-18 09:30:00", periods=25, freq="5min")
    df = pd.DataFrame({
        "open": [100.0] * 25,
        "high": [101.0] * 25,
        "low": [99.0] * 25,
        "close": [100.0] * 25,
        "volume": [10000.0] * 25,
    }, index=timestamps)

    # Mock signals from 2 distinct families (structure + oscillator) to pass confluence gate
    dir_signals = [
        {
            "_strategy_id": "fixed_range_volume_profile",
            "tradingsymbol": "RELIANCE",
            "direction": "BUY",
            "confidence": 85,
            "entryPrice": 100.0,
            "stopLoss": 98.8,
            "target": 103.5,   # Structural POC at 103.5
            "indicators": {
                "is_structural_target": True,
                "poc": 103.5,
                "atr": 1.0,
            },
        },
        {
            "_strategy_id": "stoc_rsi",
            "tradingsymbol": "RELIANCE",
            "direction": "BUY",
            "confidence": 80,
            "entryPrice": 100.0,
            "stopLoss": 98.8,
            "target": 103.5,
        },
    ]

    best = scanner._apply_confluence_gate(
        dir_signals=dir_signals,
        min_confluence=2,
        min_rr=2.0,
        df=df,
        min_sl_pct=1.2,
        max_sl_pct=2.4,
        trend_aligned=False,
        regime_enabled=False,
    )

    assert best is not None
    # Crucial: Target must be PRESERVED as the structural POC (103.5), NOT overwritten by synthetic trend formula
    assert best["target"] == 103.5
    assert best["riskReward"] >= 1.3


def test_unrealistic_extended_trade_rejected(monkeypatch):
    """Verify that a stock already extended from day open (like MAHABANK) is rejected if realistic runway < min_rr."""
    scanner = Scanner()
    monkeypatch.setattr(
        config_manager,
        "get_risk_config",
        lambda: {"microstructureFilterEnabled": False, "maxDayExpansionPercent": 4.5, "maxIntradayTargetPercent": 3.2},
    )

    # Stock started day at 82.55, currently at 84.66 (+2.55% up from open).
    # 4.5% max expansion from 82.55 is 86.26. Remaining runway is 86.26 - 84.66 = 1.60 pts.
    # Safe risk at 1.8% of 84.66 is 1.52.
    # Remaining RR is 1.60 / 1.52 = 1.05 (< 1.8 min_rr). The trade must be rejected!
    timestamps = pd.date_range("2026-09-18 09:15:00", periods=25, freq="5min")
    opens = [82.55] + [83.0 + i * 0.08 for i in range(24)]
    closes = [82.80] + [83.1 + i * 0.08 for i in range(24)]
    closes[-1] = 84.66
    highs = [c + 0.2 for c in closes]
    lows = [c - 0.2 for c in closes]

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [15000.0] * 25,
    }, index=timestamps)

    dir_signals = [
        {
            "_strategy_id": "bollinger_breakout",
            "tradingsymbol": "MAHABANK",
            "direction": "BUY",
            "confidence": 85,
            "entryPrice": 84.66,
            "stopLoss": 83.14,  # 1.52 risk (1.8%)
            "target": 88.72,   # Unrealistic 8% target
            "indicators": {"atr": 0.8},
        },
        {
            "_strategy_id": "macd_cross",
            "tradingsymbol": "MAHABANK",
            "direction": "BUY",
            "confidence": 80,
            "entryPrice": 84.66,
            "stopLoss": 83.14,
            "target": 88.72,
        },
    ]

    best = scanner._apply_confluence_gate(
        dir_signals=dir_signals,
        min_confluence=2,
        min_rr=1.8,
        df=df,
        min_sl_pct=1.2,
        max_sl_pct=2.4,
        trend_aligned=False,
        regime_enabled=False,
    )

    # Must be rejected because the stock already exhausted its intraday runway!
    assert best is None


def test_realistic_breakout_target_capped_safely(monkeypatch):
    """Verify that a fresh breakout trade gets a realistic target capped within normal day distribution."""
    scanner = Scanner()
    monkeypatch.setattr(
        config_manager,
        "get_risk_config",
        lambda: {"microstructureFilterEnabled": False, "maxDayExpansionPercent": 4.5, "maxIntradayTargetPercent": 3.2},
    )

    timestamps = pd.date_range("2026-09-18 09:15:00", periods=25, freq="5min")
    df = pd.DataFrame({
        "open": [100.0] + [100.1] * 24,
        "high": [100.5] * 25,
        "low": [99.7] * 25,
        "close": [100.2] * 24 + [100.4],
        "volume": [10000.0] * 25,
    }, index=timestamps)

    dir_signals = [
        {
            "_strategy_id": "bollinger_breakout",
            "tradingsymbol": "RELIANCE",
            "direction": "BUY",
            "confidence": 88,
            "entryPrice": 100.4,
            "stopLoss": 99.2,   # safe risk = 1.2 pts (1.19%)
            "target": 108.0,    # Unrealistic 8% raw target
            "indicators": {"atr": 1.8},
        },
        {
            "_strategy_id": "macd_cross",
            "tradingsymbol": "RELIANCE",
            "direction": "BUY",
            "confidence": 82,
            "entryPrice": 100.4,
            "stopLoss": 99.2,
            "target": 108.0,
        },
    ]

    best = scanner._apply_confluence_gate(
        dir_signals=dir_signals,
        min_confluence=2,
        min_rr=1.8,
        df=df,
        min_sl_pct=1.2,
        max_sl_pct=2.4,
        trend_aligned=False,
        regime_enabled=False,
    )

    assert best is not None
    # Target should be capped realistically (around 102.8, approx 2.4% move, never at 108.0)
    assert best["target"] < 104.0
    assert best["targetPercent"] <= 3.2
    assert best["riskReward"] >= 1.8
