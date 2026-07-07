import numpy as np
import pytest

from tdc.density import compute_density_profile, compute_profile_stats


def test_density_profile_supports_volume_weights() -> None:
    ticks = np.array([0.1, 0.2, 0.8])
    weights = np.array([1.0, 1.0, 10.0])

    density, bins = compute_density_profile(ticks, 0.0, 1.0, 2, weights)

    assert bins.tolist() == [0.0, 0.5, 1.0]
    assert density.tolist() == [0.2, 1.0]


def test_density_profile_rejects_empty_ticks() -> None:
    with pytest.raises(ValueError, match="ticks must not be empty"):
        compute_density_profile(np.array([]), 0.0, 1.0, 2)


def test_value_area_is_smallest_contiguous_range() -> None:
    ticks = np.array([0.2, 1.2, 2.2, 3.2, 4.2])
    density = np.array([0.1, 1.0, 1.0, 0.1, 0.1])
    bins = np.arange(6, dtype=float)

    stats = compute_profile_stats(ticks, density, bins)

    assert stats["value_area_low"] == 1.0
    assert stats["value_area_high"] == 3.0


def test_flat_bar_profile_stats_stay_inside_ohlc_range() -> None:
    ticks = np.full(10, 42.0)
    density, bins = compute_density_profile(ticks, 42.0, 42.0, 4)

    stats = compute_profile_stats(ticks, density, bins)

    assert stats["poc_price"] == 42.0
    assert stats["value_area_low"] == 42.0
    assert stats["value_area_high"] == 42.0
    assert stats["profile_degenerate"] is True


def test_density_profile_rejects_mismatched_volume_weights() -> None:
    with pytest.raises(ValueError, match="same length"):
        compute_density_profile(
            np.array([0.1, 0.8]),
            0.0,
            1.0,
            2,
            np.array([1.0]),
        )


def test_density_profile_rejects_out_of_range_ticks() -> None:
    with pytest.raises(ValueError, match="inside the low/high range"):
        compute_density_profile(np.array([-0.1, 0.5]), 0.0, 1.0, 2)


def test_uniform_profile_marks_poc_and_value_area_ambiguous() -> None:
    ticks = np.array([0.5, 1.5, 2.5, 3.5])
    density, bins = compute_density_profile(ticks, 0.0, 4.0, 4)

    stats = compute_profile_stats(ticks, density, bins)

    assert stats["poc_price"] == 2.0
    assert stats["poc_is_ambiguous"] is True
    assert stats["value_area_is_ambiguous"] is True
