"""
Market Hours & Exchange Trading Holiday Manager.

Dynamically detects whether Indian stock markets (NSE / BSE) are currently open,
checking for weekends, official exchange trading holidays (fetched live from public
market holiday APIs with local disk caching), and active intraday session hours
(09:15 to 15:30 IST).
"""

from __future__ import annotations

import datetime
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Persistent cache location in user application directory
CACHE_DIR = Path.home() / ".smartapi-agentic-trading"
CACHE_FILE = CACHE_DIR / "market_holidays_cache.json"

# In-memory cached holiday dictionary: { "YYYY-MM-DD": "Holiday Description" }
_HOLIDAYS_MAP: Dict[str, str] = {}
_LAST_FETCH_TIME: Optional[datetime.datetime] = None
_CACHE_TTL_HOURS = 12


def _get_ist_now() -> datetime.datetime:
    """Return current timestamp in Indian Standard Time (UTC+5:30)."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return utc_now.astimezone(ist_tz)


def _load_cached_holidays() -> Dict[str, str]:
    """Load cached market holidays from disk if available."""
    global _HOLIDAYS_MAP, _LAST_FETCH_TIME
    if _HOLIDAYS_MAP:
        return _HOLIDAYS_MAP

    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                holidays = data.get("holidays", {})
                timestamp_str = data.get("updated_at")
                if timestamp_str:
                    _LAST_FETCH_TIME = datetime.datetime.fromisoformat(timestamp_str)
                if isinstance(holidays, dict) and holidays:
                    _HOLIDAYS_MAP = holidays
                    logger.info(
                        "Loaded %d market holidays from local cache", len(_HOLIDAYS_MAP)
                    )
                    return _HOLIDAYS_MAP
        except Exception as e:
            logger.warning("Failed to load holiday cache from disk: %s", e)

    return _HOLIDAYS_MAP


def _save_cached_holidays(holidays: Dict[str, str]):
    """Persist holidays dictionary to disk cache."""
    global _HOLIDAYS_MAP, _LAST_FETCH_TIME
    _HOLIDAYS_MAP = holidays
    _LAST_FETCH_TIME = datetime.datetime.now()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"updated_at": _LAST_FETCH_TIME.isoformat(), "holidays": _HOLIDAYS_MAP},
                f,
                indent=2,
            )
        logger.info(
            "Saved %d market holidays to disk cache: %s", len(_HOLIDAYS_MAP), CACHE_FILE
        )
    except Exception as e:
        logger.warning("Failed to save holiday cache to disk: %s", e)


def fetch_market_holidays_from_api(force: bool = False) -> Dict[str, str]:
    """
    Fetch official Indian market trading holidays dynamically from public exchange APIs.

    Tries:
    1. Upstox Public Holidays API (returns clean JSON with closed_exchanges: ['NSE', 'BSE', ...])
    2. NSE Official Holiday Master API (fallback)
    """
    global _HOLIDAYS_MAP, _LAST_FETCH_TIME

    # Check existing memory / disk cache if not forced
    if not force:
        cached = _load_cached_holidays()
        if cached and _LAST_FETCH_TIME:
            elapsed = (
                datetime.datetime.now() - _LAST_FETCH_TIME
            ).total_seconds() / 3600
            if elapsed < _CACHE_TTL_HOURS:
                return cached

    fetched_holidays: Dict[str, str] = {}

    # ── Source 1: Upstox Public Market Holidays API ──────────────────────────
    try:
        req = urllib.request.Request(
            "https://api.upstox.com/v2/market/holidays",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("data", []):
                h_date = item.get("date")
                h_desc = item.get("description", "Exchange Holiday")
                closed_exchanges = item.get("closed_exchanges", [])
                h_type = item.get("holiday_type", "")

                # Check if NSE or BSE is closed
                is_equity_closed = any(
                    ex in closed_exchanges for ex in ("NSE", "BSE", "NFO")
                )
                if h_date and (is_equity_closed or h_type == "TRADING_HOLIDAY"):
                    fetched_holidays[h_date] = h_desc

        if fetched_holidays:
            logger.info(
                "Successfully fetched %d market holidays from Upstox API",
                len(fetched_holidays),
            )
            _save_cached_holidays(fetched_holidays)
            return fetched_holidays
    except Exception as e:
        logger.warning("Failed to fetch holidays from Upstox API: %s", e)

    # ── Source 2: NSE Official Holiday Master API ────────────────────────────
    try:
        req = urllib.request.Request(
            "https://www.nseindia.com/api/holiday-master?type=trading",
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # 'CM' = Capital Market (Equities), 'FO' = Futures & Options
            cm_holidays = data.get("CM", []) or data.get("FO", [])
            for item in cm_holidays:
                date_str = item.get("tradingDate")  # Format: "14-Sep-2026"
                desc = item.get("description", "NSE Trading Holiday")
                if date_str:
                    try:
                        parsed_date = datetime.datetime.strptime(
                            date_str, "%d-%b-%Y"
                        ).date()
                        iso_date = parsed_date.strftime("%Y-%m-%d")
                        fetched_holidays[iso_date] = desc
                    except Exception:
                        pass

        if fetched_holidays:
            logger.info(
                "Successfully fetched %d market holidays from NSE API",
                len(fetched_holidays),
            )
            _save_cached_holidays(fetched_holidays)
            return fetched_holidays
    except Exception as e:
        logger.warning("Failed to fetch holidays from NSE API: %s", e)

    # Fallback to existing disk cache if network fails
    if _load_cached_holidays():
        return _HOLIDAYS_MAP

    return {}


def is_weekend(target_date: Optional[datetime.date] = None) -> bool:
    """Return True if the target date is Saturday (5) or Sunday (6)."""
    if target_date is None:
        target_date = _get_ist_now().date()
    return target_date.weekday() in (5, 6)


def is_trading_holiday(
    target_date: Optional[datetime.date] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Check if the given date is an official exchange trading holiday.

    Returns:
        (is_holiday: bool, holiday_name: str or None)
    """
    if target_date is None:
        target_date = _get_ist_now().date()

    iso_date = target_date.strftime("%Y-%m-%d")
    holidays = fetch_market_holidays_from_api()

    if iso_date in holidays:
        return True, holidays[iso_date]

    return False, None


def get_market_status(target_dt: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """
    Comprehensive Indian market status evaluation.

    Returns:
        {
            "is_open": bool,
            "status": "OPEN" | "CLOSED",
            "reason": "LIVE" | "HOLIDAY" | "WEEKEND" | "PRE_MARKET" | "AFTER_HOURS",
            "holiday_name": Optional[str],
            "display_text": str,
            "current_time_ist": str,
            "session": str
        }
    """
    if target_dt is None:
        target_dt = _get_ist_now()

    date_obj = target_dt.date()
    time_obj = target_dt.time()
    iso_date = date_obj.strftime("%Y-%m-%d")
    time_str = time_obj.strftime("%H:%M:%S")

    # 1. Check Weekend
    if is_weekend(date_obj):
        day_name = date_obj.strftime("%A")
        return {
            "is_open": False,
            "status": "CLOSED",
            "reason": "WEEKEND",
            "holiday_name": None,
            "display_text": f"CLOSED (Weekend: {day_name})",
            "current_time_ist": f"{iso_date} {time_str} IST",
            "session": "Closed",
        }

    # 2. Check Exchange Trading Holiday from dynamic API
    is_holiday, holiday_name = is_trading_holiday(date_obj)
    if is_holiday:
        h_name = holiday_name or "Exchange Holiday"
        return {
            "is_open": False,
            "status": "CLOSED",
            "reason": "HOLIDAY",
            "holiday_name": h_name,
            "display_text": f"CLOSED (Holiday: {h_name})",
            "current_time_ist": f"{iso_date} {time_str} IST",
            "session": "Trading Holiday",
        }

    # 3. Check Session Time (09:15 to 15:30 IST)
    market_open = datetime.time(9, 15)
    market_close = datetime.time(15, 30)

    if time_obj < market_open:
        return {
            "is_open": False,
            "status": "CLOSED",
            "reason": "PRE_MARKET",
            "holiday_name": None,
            "display_text": "CLOSED (Pre-Market, Opens 09:15)",
            "current_time_ist": f"{iso_date} {time_str} IST",
            "session": "Pre-Market",
        }
    elif time_obj >= market_close:
        return {
            "is_open": False,
            "status": "CLOSED",
            "reason": "AFTER_HOURS",
            "holiday_name": None,
            "display_text": "CLOSED (After Hours)",
            "current_time_ist": f"{iso_date} {time_str} IST",
            "session": "After Hours",
        }

    return {
        "is_open": True,
        "status": "OPEN",
        "reason": "LIVE",
        "holiday_name": None,
        "display_text": "OPEN (Live)",
        "current_time_ist": f"{iso_date} {time_str} IST",
        "session": "Regular Trading",
    }
