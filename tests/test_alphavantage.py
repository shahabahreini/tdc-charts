import pandas as pd
import pytest

from tdc.config import DataConfig
from tdc.data import _get_api_key, fetch_alphavantage_data
from tdc.exceptions import DataFetchError
from tdc.intrabar import (
    fetch_alphavantage_intrabar_bars,
    fetch_alphavantage_intraday_data,
    get_months_in_period,
    map_interval_to_av,
)


def test_map_interval_to_av() -> None:
    assert map_interval_to_av("1m") == "1min"
    assert map_interval_to_av("5m") == "5min"
    assert map_interval_to_av("15m") == "15min"
    assert map_interval_to_av("30m") == "30min"
    assert map_interval_to_av("60m") == "60min"
    assert map_interval_to_av("1h") == "60min"
    assert map_interval_to_av("2min") == "2min"


def test_get_months_in_period() -> None:
    months = get_months_in_period("60d")
    assert len(months) >= 2
    for m in months:
        assert len(m) == 7  # YYYY-MM format
        assert m[4] == "-"


def test_get_api_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
    with pytest.raises(DataFetchError, match="API key is missing"):
        _get_api_key()


def test_get_api_key_present(monkeypatch) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "TEST_KEY")
    assert _get_api_key() == "TEST_KEY"


def test_fetch_alphavantage_data_success(monkeypatch) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "TEST_KEY")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "Time Series (Daily)": {
                    "2026-07-06": {
                        "1. open": "100.0",
                        "2. high": "110.0",
                        "3. low": "95.0",
                        "4. close": "105.0",
                        "5. volume": "1000.0"
                    },
                    "2026-07-05": {
                        "1. open": "90.0",
                        "2. high": "100.0",
                        "3. low": "85.0",
                        "4. close": "95.0",
                        "5. volume": "500.0"
                    }
                }
            }

    def mock_get(url, timeout=15):
        assert "TIME_SERIES_DAILY" in url
        assert "symbol=AAPL" in url
        assert "outputsize=full" in url
        assert "apikey=TEST_KEY" in url
        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)

    df = fetch_alphavantage_data("AAPL", "1d", "5d")
    assert not df.empty
    assert len(df) == 2
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert df.loc["2026-07-06", "Close"] == 105.0


def test_fetch_alphavantage_data_api_error(monkeypatch) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "TEST_KEY")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"Error Message": "Invalid API key"}

    monkeypatch.setattr("requests.get", lambda url, timeout=15: MockResponse())

    with pytest.raises(DataFetchError, match="Alpha Vantage API error: Invalid API key"):
        fetch_alphavantage_data("AAPL", "1d", "5d")


def test_fetch_alphavantage_data_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "TEST_KEY")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"Note": "Rate limit exceeded"}

    monkeypatch.setattr("requests.get", lambda url, timeout=15: MockResponse())

    # We expect tenacity retry to fail after 3 attempts, raising the last DataFetchError
    with pytest.raises(DataFetchError, match="Alpha Vantage rate limit: Rate limit exceeded"):
        fetch_alphavantage_data("AAPL", "1d", "5d")


def test_fetch_alphavantage_intraday_data_short_period(monkeypatch) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "TEST_KEY")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "Time Series (5min)": {
                    "2026-07-06 09:30:00": {
                        "1. open": "100.0",
                        "2. high": "101.0",
                        "3. low": "99.0",
                        "4. close": "100.5",
                        "5. volume": "10"
                    }
                }
            }

    monkeypatch.setattr("requests.get", lambda url, timeout=15: MockResponse())

    df = fetch_alphavantage_intraday_data("AAPL", "5m", "5d")
    assert not df.empty
    assert len(df) == 1
    assert df.index[0] == pd.Timestamp("2026-07-06 09:30:00")
    assert df.iloc[0]["Close"] == 100.5


def test_fetch_alphavantage_intrabar_bars(monkeypatch) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "TEST_KEY")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            # Return regular hours data so it's not filtered out
            return {
                "Time Series (5min)": {
                    "2026-07-06 09:35:00": {
                        "1. open": "100.0",
                        "2. high": "102.0",
                        "3. low": "99.0",
                        "4. close": "101.0",
                        "5. volume": "10"
                    },
                    "2026-07-06 09:40:00": {
                        "1. open": "101.0",
                        "2. high": "103.0",
                        "3. low": "100.0",
                        "4. close": "102.0",
                        "5. volume": "20"
                    }
                }
            }

    monkeypatch.setattr("requests.get", lambda url, timeout=15: MockResponse())

    config = DataConfig(
        ticker="AAPL",
        source="alphavantage",
        interval="1d",
        period="5d",
        intrabar_source="alphavantage",
        intrabar_interval="5m",
        session_timezone="America/New_York",
    )

    parent, intrabar = fetch_alphavantage_intrabar_bars(config)
    assert not parent.empty
    assert not intrabar.empty
    assert len(parent) == 1
    assert parent.iloc[0]["open"] == 100.0
    assert parent.iloc[0]["high"] == 103.0
    assert parent.iloc[0]["low"] == 99.0
    assert parent.iloc[0]["close"] == 102.0
    assert parent.iloc[0]["volume"] == 30

    assert intrabar.attrs["profile_source"] == "real_alphavantage_intraday"
    assert intrabar.attrs["volume_mode"] == "real_subbar"
