"""
Tests for 1R Volatility Parity Position Sizing Engine.
"""

from trading_system.config.settings import Settings
from trading_system.risk.position_sizer import PositionSizer


def test_1r_volatility_parity_calculation():
    settings = Settings(
        portfolio_equity=100_000.0,
        risk_percent=1.0,  # 1% = ₹1,000 risk budget
        max_capital_per_trade=60_000.0,
        min_turnover_threshold=35_000.0,
    )
    sizer = PositionSizer(settings)

    # Entry = ₹1,000, SL = ₹980 -> Per-share risk = ₹20
    # Qty = floor(1,000 / 20) = 50
    # Turnover = 50 * 1,000 * 2 = ₹100,000 (>= 35,000)
    qty, res = sizer.calculate_size(entry_price=1000.0, stop_loss=980.0)

    assert res.is_valid
    assert qty == 50
    assert res.risk_budget == 1000.0
    assert res.per_share_risk == 20.0
    assert res.notional_allocation == 50000.0
    assert res.round_trip_turnover == 100000.0


def test_position_sizer_max_capital_clamping():
    settings = Settings(
        portfolio_equity=100_000.0,
        risk_percent=1.0,  # ₹1,000 risk budget
        max_capital_per_trade=40_000.0,  # Cap at ₹40,000
        min_turnover_threshold=35_000.0,
    )
    sizer = PositionSizer(settings)

    # Entry = ₹1,000, SL = ₹995 -> Per-share risk = ₹5
    # Raw Qty = floor(1,000 / 5) = 200 shares (Notional = ₹200,000 > ₹40,000)
    # Clamped Qty = floor(40,000 / 1,000) = 40 shares
    # Turnover = 40 * 1,000 * 2 = ₹80,000 (>= 35,000)
    qty, res = sizer.calculate_size(entry_price=1000.0, stop_loss=995.0)

    assert res.is_valid
    assert qty == 40
    assert res.notional_allocation == 40000.0


def test_position_sizer_turnover_floor_rejection():
    settings = Settings(
        portfolio_equity=100_000.0,
        risk_percent=1.0,
        max_capital_per_trade=50_000.0,
        min_turnover_threshold=35_000.0,
    )
    sizer = PositionSizer(settings)

    # Entry = ₹1,000, SL = ₹800 -> Per-share risk = ₹200 (20% SL width)
    # Raw Qty = floor(1,000 / 200) = 5 shares
    # Turnover = 5 * 1,000 * 2 = ₹10,000 (< ₹35,000)
    # Must reject and drop signal to 0 (never force 1)
    qty, res = sizer.calculate_size(entry_price=1000.0, stop_loss=800.0)

    assert not res.is_valid
    assert qty == 0
    assert "below statutory threshold" in res.rejection_reason


def test_position_sizer_invalid_parameters():
    sizer = PositionSizer()
    qty, res = sizer.calculate_size(entry_price=0.0, stop_loss=100.0)
    assert qty == 0
    assert not res.is_valid

    qty, res = sizer.calculate_size(entry_price=100.0, stop_loss=100.0)
    assert qty == 0
    assert not res.is_valid
