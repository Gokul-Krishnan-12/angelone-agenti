import pandas as pd

from backend.main import handle_request
from backend.swing_screener import swing_screener


def test_calculate_indicators_insufficient_data():
    short_df = pd.DataFrame(
        {
            "open": [100.0] * 5,
            "high": [105.0] * 5,
            "low": [95.0] * 5,
            "close": [102.0] * 5,
            "volume": [1000] * 5,
        }
    )
    res = swing_screener._calculate_indicators(short_df)
    assert res == {}


def test_calculate_indicators_breakout_and_accumulation():
    # Build a 40-day synthetic sequence with institutional accumulation and breakout
    n = 45
    closes = [100.0 + i * 0.5 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 2.0 for c in closes]
    opens = [c - 1.5 for c in closes]
    volumes = [500_000.0 + (i * 20_000.0) for i in range(n)]

    df = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )

    indicators = swing_screener._calculate_indicators(df)
    assert indicators != {}
    assert "ltp" in indicators
    assert "buy_price" in indicators
    assert "target_price" in indicators
    assert "stop_loss" in indicators
    assert "risk_reward" in indicators
    assert "status" in indicators
    assert indicators["status"] in ("IN_RANGE", "SETTING_UP", "TRIGGERED")
    assert indicators["target_price"] > indicators["buy_price"]
    assert indicators["stop_loss"] < indicators["buy_price"]
    assert 10 <= indicators["inst_score"] <= 100
    assert indicators["cmf"] > 0
    assert indicators["rsi"] > 0


def test_run_screener_top_15():
    res = swing_screener.run_screener(limit=15)
    assert isinstance(res, dict)
    assert "timestamp" in res
    assert "totalScanned" in res
    assert "topStocks" in res
    assert len(res["topStocks"]) == 15

    top_stock = res["topStocks"][0]
    expected_keys = {
        "tradingsymbol",
        "companyName",
        "sector",
        "marketCapCategory",
        "ltp",
        "changePercent",
        "buyPrice",
        "targetPrice",
        "stopLoss",
        "riskRewardRatio",
        "status",
        "institutionalScore",
        "institutionalActivity",
        "cmf",
        "upDownVolumeRatio",
        "rvol",
        "rsi",
        "pattern",
        "fundamentalRating",
        "fundamentalSummary",
    }
    for key in expected_keys:
        assert key in top_stock, f"Missing key {key} in stock item"

    # Status must be one of the defined statuses
    for stock in res["topStocks"]:
        assert stock["status"] in ("IN_RANGE", "SETTING_UP", "TRIGGERED")
        assert stock["buyPrice"] > 0
        assert stock["targetPrice"] > stock["buyPrice"]
        assert stock["stopLoss"] < stock["buyPrice"]
        assert stock["riskRewardRatio"] > 0

    # Last results caching test
    cached = swing_screener.get_last_results()
    assert cached == res


def test_jsonrpc_swing_scan():
    req = {
        "jsonrpc": "2.0",
        "method": "swing_scan",
        "params": {"limit": 15},
        "id": 88,
    }
    resp = handle_request(req)
    assert resp["id"] == 88
    assert "result" in resp
    assert len(resp["result"]["topStocks"]) == 15

    # Test get_last_swing_scan
    req_last = {
        "jsonrpc": "2.0",
        "method": "get_last_swing_scan",
        "params": {},
        "id": 89,
    }
    resp_last = handle_request(req_last)
    assert resp_last["id"] == 89
    assert resp_last["result"] == resp["result"]
