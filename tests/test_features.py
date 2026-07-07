import pandas as pd

from tdc.config import TDCConfig
from tdc.features import build_feature_frame


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
