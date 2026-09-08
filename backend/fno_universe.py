"""
NSE F&O (Futures & Options) Universe Manager.

Provides the comprehensive list of ~210 active liquid derivative stocks eligible
for trading on the National Stock Exchange (NSE). High-momentum intraday strategies
focus on this high-beta universe rather than purely mega-cap index constituents.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Official bundled list of 210 NSE F&O underlying equities
FNO_UNIVERSE: List[str] = [
    "360ONE",
    "ABB",
    "ABCAPITAL",
    "ADANIENSOL",
    "ADANIENT",
    "ADANIGREEN",
    "ADANIPORTS",
    "ADANIPOWER",
    "ALKEM",
    "AMBER",
    "AMBUJACEM",
    "ANGELONE",
    "APLAPOLLO",
    "APOLLOHOSP",
    "ASHOKLEY",
    "ASIANPAINT",
    "ASTRAL",
    "ATHERENERG",
    "AUBANK",
    "AUROPHARMA",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJAJFINSV",
    "BAJAJHLDNG",
    "BAJFINANCE",
    "BANDHANBNK",
    "BANKBARODA",
    "BANKINDIA",
    "BDL",
    "BEL",
    "BHARATFORG",
    "BHARTIARTL",
    "BHEL",
    "BIOCON",
    "BLUESTARCO",
    "BOSCHLTD",
    "BPCL",
    "BRITANNIA",
    "BSE",
    "CAMS",
    "CANBK",
    "CDSL",
    "CGPOWER",
    "CHOLAFIN",
    "CIPLA",
    "COALINDIA",
    "COCHINSHIP",
    "COFORGE",
    "COLPAL",
    "CONCOR",
    "CROMPTON",
    "CUMMINSIND",
    "DABUR",
    "DELHIVERY",
    "DIVISLAB",
    "DIXON",
    "DLF",
    "DMART",
    "DRREDDY",
    "EICHERMOT",
    "ETERNAL",
    "FEDERALBNK",
    "FORCEMOT",
    "FORTIS",
    "GAIL",
    "GLENMARK",
    "GMRAIRPORT",
    "GODFRYPHLP",
    "GODREJCP",
    "GODREJPROP",
    "GRASIM",
    "GVT&D",
    "HAL",
    "HAVELLS",
    "HCLTECH",
    "HDFCAMC",
    "HDFCBANK",
    "HDFCLIFE",
    "HEROMOTOCO",
    "HINDALCO",
    "HINDPETRO",
    "HINDUNILVR",
    "HINDZINC",
    "HYUNDAI",
    "ICICIBANK",
    "ICICIGI",
    "ICICIPRULI",
    "IDEA",
    "IDFCFIRSTB",
    "IEX",
    "INDHOTEL",
    "INDIANB",
    "INDIGO",
    "INDUSINDBK",
    "INDUSTOWER",
    "INFY",
    "INOXWIND",
    "IOC",
    "IREDA",
    "IRFC",
    "ITC",
    "JINDALSTEL",
    "JIOFIN",
    "JSWENERGY",
    "JSWSTEEL",
    "JUBLFOOD",
    "KALYANKJIL",
    "KAYNES",
    "KEI",
    "KFINTECH",
    "KOTAKBANK",
    "KPITTECH",
    "LAURUSLABS",
    "LICHSGFIN",
    "LICI",
    "LODHA",
    "LT",
    "LTF",
    "LTM",
    "LUPIN",
    "M&M",
    "MAHABANK",
    "MANAPPURAM",
    "MANKIND",
    "MARICO",
    "MARUTI",
    "MAXHEALTH",
    "MAZDOCK",
    "MCX",
    "MFSL",
    "MOTHERSON",
    "MOTILALOFS",
    "MPHASIS",
    "MUTHOOTFIN",
    "NAM-INDIA",
    "NATIONALUM",
    "NAUKRI",
    "NBCC",
    "NESTLEIND",
    "NHPC",
    "NMDC",
    "NTPC",
    "NYKAA",
    "OBEROIRLTY",
    "OFSS",
    "OIL",
    "ONGC",
    "PAGEIND",
    "PATANJALI",
    "PAYTM",
    "PERSISTENT",
    "PETRONET",
    "PFC",
    "PGEL",
    "PHOENIXLTD",
    "PIDILITIND",
    "PIIND",
    "PNB",
    "PNBHOUSING",
    "POLICYBZR",
    "POLYCAB",
    "POWERGRID",
    "POWERINDIA",
    "PREMIERENE",
    "PRESTIGE",
    "RADICO",
    "RBLBANK",
    "RECLTD",
    "RELIANCE",
    "RVNL",
    "SAGILITY",
    "SAIL",
    "SBICARD",
    "SBILIFE",
    "SBIN",
    "SHREECEM",
    "SHRIRAMFIN",
    "SIEMENS",
    "SOLARINDS",
    "SONACOMS",
    "SRF",
    "SUNPHARMA",
    "SUPREMEIND",
    "SUZLON",
    "SWIGGY",
    "TATACONSUM",
    "TATAELXSI",
    "TATAPOWER",
    "TATASTEEL",
    "TCS",
    "TECHM",
    "TIINDIA",
    "TITAN",
    "TMPV",
    "TORNTPHARM",
    "TRENT",
    "TVSMOTOR",
    "ULTRACEMCO",
    "UNIONBANK",
    "UNITDSPR",
    "UNOMINDA",
    "UPL",
    "VBL",
    "VEDL",
    "VMM",
    "VOLTAS",
    "WAAREEENER",
    "WIPRO",
    "YESBANK",
    "ZYDUSLIFE",
]

_cached_fno: List[str] | None = None
_cached_on: date | None = None


def _extract_fno_from_scrip_master() -> List[str]:
    """Extract active F&O equities from SmartAPI's local scrip master cache."""
    cache_file = Path.home() / ".smartapi-agentic-trading" / "scrip_master.json"
    if not cache_file.exists():
        return []

    try:
        with open(cache_file, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        fno_symbols = set()
        for item in data:
            if item.get("exch_seg") == "NFO" and item.get("instrumenttype") in (
                "FUTSTK",
                "OPTSTK",
            ):
                name = str(item.get("name", "")).strip().upper()
                if (
                    name
                    and not name.endswith("TEST")
                    and not name.startswith("NIFTY")
                    and not name.startswith("BANKNIFTY")
                    and not name.startswith("FINNIFTY")
                    and not name.startswith("MIDCPNIFTY")
                ):
                    fno_symbols.add(name)

        return sorted(list(fno_symbols))
    except Exception as e:
        logger.warning("Failed to extract F&O universe from scrip master: %s", e)
        return []


def get_fno_universe() -> List[str]:
    """
    Return today's active F&O stock universe.

    Uses SmartAPI cached scrip master if available, falling back to the bundled 210 F&O list.
    """
    global _cached_fno, _cached_on

    today = date.today()
    if _cached_fno is not None and _cached_on == today:
        return list(_cached_fno)

    extracted = _extract_fno_from_scrip_master()
    if len(extracted) >= 150:
        _cached_fno = extracted
        _cached_on = today
        logger.info("Loaded %d F&O stocks from Angel One scrip master", len(extracted))
        return list(_cached_fno)

    _cached_fno = list(FNO_UNIVERSE)
    _cached_on = today
    return list(_cached_fno)
