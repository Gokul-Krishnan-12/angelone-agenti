"""
Tests for Settings and FrictionGuard statutory calculation rules.
"""

from trading_system.config.settings import Settings
from trading_system.risk.friction_guard import FrictionGuard


def test_settings_initialization():
    settings = Settings(
        mode="paper",
        portfolio_equity=150_000.0,
        risk_percent=1.0,
        max_daily_loss=2_000.0,
    )
    assert settings.mode == "paper"
    assert settings.portfolio_equity == 150_000.0
    assert settings.risk_percent == 1.0
    assert settings.max_daily_loss == 2_000.0
    assert "RELIANCE" in settings.watchlist


def test_statutory_friction_breakdown():
    settings = Settings()
    guard = FrictionGuard(settings)

    # Entry at 1000, Exit at 1000, Quantity 50
    # Buy turnover = 50,000; Sell turnover = 50,000; Total = 100,000
    breakdown = guard.calculate_round_trip_friction(
        entry_price=1000.0,
        exit_price=1000.0,
        quantity=50,
        orders_count=2,
    )

    assert breakdown.buy_turnover == 50000.0
    assert breakdown.sell_turnover == 50000.0
    assert breakdown.total_turnover == 100000.0
    assert breakdown.brokerage == 40.0
    assert breakdown.stt == 12.50  # 0.025% of 50,000
    assert breakdown.exchange_fee == 3.25  # 0.00325% of 100,000
    assert breakdown.sebi_charge == 0.10  # 0.0001% of 100,000
    assert breakdown.stamp_duty == 1.50  # 0.003% of 50,000

    # GST on (40.0 + 3.25 + 0.10 = 43.35) * 18% = 7.80
    assert breakdown.gst == 7.80
    assert breakdown.total_friction == 65.15
    assert round(breakdown.friction_pct, 3) == 0.065  # ~0.065%


def test_friction_guard_turnover_threshold_rejection():
    settings = Settings(min_turnover_threshold=35_000.0)
    guard = FrictionGuard(settings)

    # 10 shares @ ₹1,000 -> Turnover = 20,000 (< 35,000)
    passed, reason, _ = guard.validate_trade(
        entry_price=1000.0,
        target_price=1050.0,
        quantity=10,
    )
    assert not passed
    assert "Turnover" in reason
    assert "below required" in reason


def test_friction_guard_profit_multiple_rejection():
    settings = Settings(
        min_turnover_threshold=35_000.0, min_profit_friction_multiple=3.0
    )
    guard = FrictionGuard(settings)

    # 50 shares @ ₹1,000, target ₹1,001 (Gain = ₹50, friction ≈ ₹65)
    # Required gain >= 3 * 65 = 195. Should be rejected!
    passed, reason, _ = guard.validate_trade(
        entry_price=1000.0,
        target_price=1001.0,
        quantity=50,
    )
    assert not passed
    assert "less than 3.0x estimated friction" in reason


def test_friction_guard_approval():
    settings = Settings(
        min_turnover_threshold=35_000.0, min_profit_friction_multiple=3.0
    )
    guard = FrictionGuard(settings)

    # 50 shares @ ₹1,000, target ₹1,025 (Gain = ₹1,250, friction ≈ ₹65)
    passed, reason, breakdown = guard.validate_trade(
        entry_price=1000.0,
        target_price=1025.0,
        quantity=50,
    )
    assert passed
    assert "PASSED FrictionGuard" in reason
    assert breakdown.total_turnover >= 35_000.0
