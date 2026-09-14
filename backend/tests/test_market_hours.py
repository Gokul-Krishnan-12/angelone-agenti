import datetime
from unittest.mock import patch

from backend.market_hours import (
    get_market_status,
    is_trading_holiday,
    is_weekend,
)


def test_is_weekend():
    # Saturday
    sat = datetime.date(2026, 9, 12)
    assert is_weekend(sat) is True

    # Sunday
    sun = datetime.date(2026, 9, 13)
    assert is_weekend(sun) is True

    # Monday
    mon = datetime.date(2026, 9, 14)
    assert is_weekend(mon) is False


def test_is_trading_holiday():
    with patch(
        "backend.market_hours.fetch_market_holidays_from_api",
        return_value={"2026-09-14": "Ganesh Chaturthi"},
    ):
        is_hol, name = is_trading_holiday(datetime.date(2026, 9, 14))
        assert is_hol is True
        assert name == "Ganesh Chaturthi"

        is_hol2, name2 = is_trading_holiday(datetime.date(2026, 9, 15))
        assert is_hol2 is False
        assert name2 is None


def test_get_market_status_holiday():
    with patch(
        "backend.market_hours.fetch_market_holidays_from_api",
        return_value={"2026-09-14": "Ganesh Chaturthi"},
    ):
        target_dt = datetime.datetime(2026, 9, 14, 10, 30, 0)
        status = get_market_status(target_dt)
        assert status["is_open"] is False
        assert status["status"] == "CLOSED"
        assert status["reason"] == "HOLIDAY"
        assert status["holiday_name"] == "Ganesh Chaturthi"
        assert "Ganesh Chaturthi" in status["display_text"]


def test_get_market_status_regular_trading_hours():
    with patch(
        "backend.market_hours.fetch_market_holidays_from_api",
        return_value={"2026-09-14": "Ganesh Chaturthi"},
    ):
        # Tuesday at 10:30 AM
        target_dt = datetime.datetime(2026, 9, 15, 10, 30, 0)
        status = get_market_status(target_dt)
        assert status["is_open"] is True
        assert status["status"] == "OPEN"
        assert status["reason"] == "LIVE"
        assert status["display_text"] == "OPEN (Live)"


def test_get_market_status_pre_and_post_market():
    with patch(
        "backend.market_hours.fetch_market_holidays_from_api",
        return_value={},
    ):
        # Tuesday 08:30 AM (Pre-Market)
        target_dt = datetime.datetime(2026, 9, 15, 8, 30, 0)
        status = get_market_status(target_dt)
        assert status["is_open"] is False
        assert status["reason"] == "PRE_MARKET"

        # Tuesday 16:00 PM (After-Hours)
        target_dt2 = datetime.datetime(2026, 9, 15, 16, 0, 0)
        status2 = get_market_status(target_dt2)
        assert status2["is_open"] is False
        assert status2["reason"] == "AFTER_HOURS"
