import pandas as pd
import pytest

from tdc.config import TDCConfig
from tdc.exceptions import DataFetchError
from tdc.features import build_feature_frame
from tdc.intrabar import fetch_yahoo_intrabar_bars, validate_yahoo_intraday_request


def test_synthetic_feature_frame_exports_confidence_and_stable_indecision() -> None:
    bars = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=2, freq="D"),
            "open": [10.0, 10.5],
            "high": [11.0, 11.5],
            "low": [9.5, 10.0],
            "close": [10.8, 10.2],
            "volume": [1_000.0, 1_500.0],
        },
    )
    config = TDCConfig(
        data={"ticker": "TEST"},
        algorithm={
            "mode": "synthetic",
            "nbins": 4,
            "synthetic_tick_count": 20,
            "random_seed": 7,
            "enable_volume_weighting": True,
        },
    )

    features = build_feature_frame(bars, config)

    assert features["profile_source"].tolist() == ["synthetic", "synthetic"]
    assert features["volume_mode"].tolist() == ["synthetic_even", "synthetic_even"]
    assert features["indecision_flag"].tolist() == [False, False]
    assert "poc_delta" in features.columns
    assert features["profile_confidence"].between(0.0, 1.0).all()
    assert features["profile_warning"].str.contains("synthetic_estimate").all()


def test_real_intrabar_mode_uses_bar_id_and_real_volume_weights(tmp_path) -> None:
    intrabar_path = tmp_path / "intrabar.csv"
    pd.DataFrame(
        {
            "bar_id": [0, 0],
            "timestamp": ["2026-01-01 09:31", "2026-01-01 09:32"],
            "price": [0.1, 0.8],
            "volume": [1.0, 10.0],
        },
    ).to_csv(intrabar_path, index=False)
    bars = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2026-01-01 09:30")],
            "open": [0.1],
            "high": [1.0],
            "low": [0.0],
            "close": [0.8],
        },
    )
    config = TDCConfig(
        data={"ticker": "TEST", "intrabar_path": str(intrabar_path)},
        algorithm={"mode": "real", "nbins": 2, "enable_volume_weighting": True},
    )

    features = build_feature_frame(bars, config)

    assert features.loc[0, "profile_source"] == "real"
    assert features.loc[0, "volume_mode"] == "real"
    assert features.loc[0, "density_00"] == 0.1
    assert features.loc[0, "density_01"] == 1.0


def test_yahoo_real_mode_builds_parent_bars_from_regular_session(monkeypatch) -> None:
    timestamps = pd.DatetimeIndex(
        [
            "2026-01-02 08:00",
            "2026-01-02 09:30",
            "2026-01-02 09:35",
            "2026-01-02 16:05",
            "2026-01-05 09:30",
            "2026-01-05 09:35",
        ],
        tz="America/New_York",
        name="Datetime",
    )
    raw_intraday = pd.DataFrame(
        {
            "Open": [50.0, 100.0, 101.0, 300.0, 110.0, 111.0],
            "High": [55.0, 101.0, 102.0, 305.0, 112.0, 113.0],
            "Low": [49.0, 99.0, 100.0, 299.0, 109.0, 110.0],
            "Close": [54.0, 100.5, 101.5, 304.0, 111.0, 112.0],
            "Volume": [1, 10, 20, 1, 30, 40],
        },
        index=timestamps,
    )

    def fake_fetch_yf_data(
        ticker: str,
        interval: str,
        period: str,
        *,
        prepost: bool = False,
    ) -> pd.DataFrame:
        assert ticker == "TEST"
        assert interval == "5m"
        assert period == "60d"
        assert prepost is False
        return raw_intraday

    monkeypatch.setattr("tdc.intrabar.fetch_yf_data", fake_fetch_yf_data)
    config = TDCConfig(
        data={"ticker": "TEST", "period": "60d"},
        algorithm={"mode": "real", "enable_volume_weighting": True, "nbins": 2},
    )

    parent, intrabar = fetch_yahoo_intrabar_bars(config.data)
    features = build_feature_frame(parent, config, intrabar)

    assert len(parent) == 2
    assert parent.loc[0, "open"] == 100.0
    assert parent.loc[0, "high"] == 102.0
    assert parent.loc[0, "low"] == 99.0
    assert parent.loc[0, "close"] == 101.5
    assert parent.loc[0, "volume"] == 30
    assert intrabar["bar_id"].tolist() == [0, 0, 1, 1]
    assert features["profile_source"].tolist() == [
        "real_yahoo_intraday",
        "real_yahoo_intraday",
    ]
    assert features["volume_mode"].tolist() == ["real_subbar", "real_subbar"]
    assert features["profile_warning"].str.contains("subbar_ohlcv_not_tick_data").all()


def test_yahoo_real_mode_rejects_period_beyond_intraday_limit() -> None:
    config = TDCConfig(
        data={"ticker": "TEST", "period": "12mo", "intrabar_interval": "5m"},
        algorithm={"mode": "real"},
    )

    with pytest.raises(DataFetchError, match="at most 60 days"):
        validate_yahoo_intraday_request(config.data)
