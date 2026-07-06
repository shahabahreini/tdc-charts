from tdc.config import FeaturesConfig


def test_legacy_poc_overlay_disables_new_poc_flags() -> None:
    config = FeaturesConfig(enable_poc_overlay=False)

    assert config.enable_poc_marker is False
    assert config.enable_poc_drift_line is False


def test_legacy_concentration_flag_maps_to_indecision() -> None:
    config = FeaturesConfig(concentration_ratio_flagging=False)

    assert config.enable_indecision_flags is False
