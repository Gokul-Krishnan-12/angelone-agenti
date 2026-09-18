"""Tests for SmartAPI authentication token handling and Bearer prefix sanitization."""

from unittest.mock import MagicMock

from backend.config import ConfigManager
from backend.smartapi_client import SmartApiClient


def test_set_session_tokens_strips_bearer():
    client = SmartApiClient()
    client.init("fake_api_key", "A12345")

    # Pass token with Bearer prefix
    client.set_session_tokens("Bearer eyJhbGciOiJIUzUxMiJ9.fake.token")
    assert client.jwt_token == "eyJhbGciOiJIUzUxMiJ9.fake.token"
    assert client.smart_api.access_token == "eyJhbGciOiJIUzUxMiJ9.fake.token"
    assert not client.smart_api.access_token.startswith("Bearer ")


def test_login_strips_bearer_from_session_response(monkeypatch):
    mock_smart_connect = MagicMock()
    mock_smart_connect.generateSession.return_value = {
        "status": True,
        "message": "SUCCESS",
        "data": {
            "jwtToken": "Bearer eyJhbGciOiJIUzUxMiJ9.fake.token",
            "refreshToken": "fake_refresh",
            "feedToken": "fake_feed",
        },
    }
    mock_smart_connect.getProfile.return_value = {
        "status": True,
        "data": {"name": "Test User"},
    }
    monkeypatch.setattr(
        "backend.smartapi_client.SmartConnect",
        lambda *args, **kwargs: mock_smart_connect,
    )

    client = SmartApiClient()
    res = client.login("fake_key", "A12345", "1234", "123456")
    assert res["is_valid"] is True
    assert res["jwt_token"] == "eyJhbGciOiJIUzUxMiJ9.fake.token"
    assert not res["jwt_token"].startswith("Bearer ")
    assert client.jwt_token == "eyJhbGciOiJIUzUxMiJ9.fake.token"
    assert mock_smart_connect.setAccessToken.called
    assert (
        mock_smart_connect.setAccessToken.call_args[0][0]
        == "eyJhbGciOiJIUzUxMiJ9.fake.token"
    )


def test_config_manager_strips_bearer(tmp_path):
    mgr = ConfigManager()
    mgr.save_credentials(
        api_key="my_key",
        client_code="A12345",
        jwt_token="Bearer eyJhbGciOiJIUzUxMiJ9.saved.token",
    )
    creds = mgr.get_credentials()
    assert creds["jwtToken"] == "eyJhbGciOiJIUzUxMiJ9.saved.token"
    assert not creds["jwtToken"].startswith("Bearer ")


def test_renew_access_token_strips_bearer():
    client = SmartApiClient()
    client.init("fake_api_key", "A12345")
    client.refresh_token = "fake_refresh"

    mock_smart_connect = MagicMock()
    mock_smart_connect.renewAccessToken.return_value = {
        "status": True,
        "data": {
            "jwtToken": "Bearer eyJhbGciOiJIUzUxMiJ9.renewed.token",
            "refreshToken": "new_refresh",
        },
    }
    client.smart_api = mock_smart_connect

    success = client.renew_access_token()
    assert success is True
    assert client.jwt_token == "eyJhbGciOiJIUzUxMiJ9.renewed.token"
    assert not client.jwt_token.startswith("Bearer ")


def test_smartapi_client_caching():
    client = SmartApiClient()
    client.clear_cache()

    mock_smart_connect = MagicMock()
    mock_smart_connect.rmsLimit.return_value = {
        "status": True,
        "data": {"net": 5000.0, "availablecash": 5000.0},
    }
    mock_smart_connect.position.return_value = {
        "status": True,
        "data": [],
    }
    client.smart_api = mock_smart_connect

    # First call: hits smart_api.rmsLimit
    m1 = client.get_margins()
    assert m1["equity"]["net"] == 5000.0
    assert mock_smart_connect.rmsLimit.call_count == 1

    # Second call without force: uses in-memory cache, does not hit API
    m2 = client.get_margins()
    assert m2["equity"]["net"] == 5000.0
    assert mock_smart_connect.rmsLimit.call_count == 1

    # Third call with force=True: bypasses cache and hits API
    m3 = client.get_margins(force=True)
    assert m3["equity"]["net"] == 5000.0
    assert mock_smart_connect.rmsLimit.call_count == 2


def test_estimate_charges_client():
    client = SmartApiClient()
    mock_smart_connect = MagicMock()
    mock_smart_connect.estimateCharges.return_value = {
        "status": True,
        "message": "SUCCESS",
        "data": {
            "summary": {
                "total_charges": 45.8,
                "breakup": [{"name": "Angel One Brokerage", "amount": 20.0}],
            }
        },
    }
    client.smart_api = mock_smart_connect
    client.token_map = {"INFY": "1594"}

    res = client.estimate_charges(
        [
            {
                "tradingsymbol": "INFY-EQ",
                "transactionType": "BUY",
                "quantity": 10,
                "price": 1800.0,
            }
        ]
    )
    assert "summary" in res
    assert res["summary"]["total_charges"] == 45.8
    assert mock_smart_connect.estimateCharges.called


def test_execute_with_rate_limit_backoff_and_retry(monkeypatch):
    """Verify that rate limit errors (exceeding access rate) trigger backoff and retry."""
    client = SmartApiClient()
    call_count = 0
    sleeps = []

    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))

    def mock_api_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception(
                "Couldn't parse the JSON response received from the server: b'Access denied because of exceeding access rate'"
            )
        return {"status": True, "data": [{"net": 1}]}

    res = client._execute_with_auth_retry(mock_api_func)
    assert call_count == 2
    assert len(sleeps) == 1
    assert sleeps[0] == 1.5  # 1.5 * attempt
    assert res["status"] is True
    assert res["data"][0]["net"] == 1


def test_candle_rate_pacing(monkeypatch):
    """Verify that get_historical_data paces calls by at least 0.35s."""
    client = SmartApiClient()
    mock_smart_connect = MagicMock()
    mock_smart_connect.getCandleData.return_value = {
        "status": True,
        "data": [["2025-01-01 09:15", 100, 105, 95, 102, 1000]],
    }
    client.smart_api = mock_smart_connect

    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))

    # First call initializes the timestamp
    client.get_historical_data(
        "1594", "2025-01-01 09:15", "2025-01-01 15:30", "5minute"
    )

    # Immediately make second call (elapsed ~ 0s)
    client.get_historical_data(
        "1594", "2025-01-01 09:15", "2025-01-01 15:30", "5minute"
    )

    # Verify that sleep was invoked for pacing
    assert len(sleeps) >= 1
    assert any(s > 0 for s in sleeps)

