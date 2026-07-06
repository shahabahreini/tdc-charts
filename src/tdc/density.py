from typing import Any

import numpy as np
from scipy.stats import kurtosis, skew


def compute_density_profile(
    ticks: np.ndarray,
    low: float,
    high: float,
    nbins: int,
    volume: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute a normalized time-at-price density profile.
    """
    if nbins < 1:
        raise ValueError("nbins must be at least 1")

    if len(ticks) == 0:
        raise ValueError("ticks must not be empty")

    if high < low:
        raise ValueError(f"high ({high}) must be greater than or equal to low ({low})")

    if high == low:
        return np.ones(nbins), np.linspace(low, low + 1e-5, nbins + 1)

    bins = np.linspace(low, high, nbins + 1)

    if volume is not None and len(volume) == len(ticks):
        counts, _ = np.histogram(ticks, bins=bins, weights=volume)
    else:
        counts, _ = np.histogram(ticks, bins=bins)

    max_count = np.max(counts)
    density = np.zeros(nbins) if max_count == 0 else counts / max_count
    return density, bins


def _contiguous_value_area(
    density: np.ndarray,
    bins: np.ndarray,
    target_ratio: float = 0.68,
) -> tuple[float, float]:
    total_mass = float(np.sum(density))
    if total_mass <= 0:
        return float(bins[0]), float(bins[-1])

    target_mass = total_mass * target_ratio
    best_start = 0
    best_end = len(density) - 1
    best_width = best_end - best_start
    best_mass = -1.0

    for start in range(len(density)):
        mass = 0.0
        for end in range(start, len(density)):
            mass += float(density[end])
            if mass >= target_mass:
                width = end - start
                if width < best_width or (width == best_width and mass > best_mass):
                    best_start = start
                    best_end = end
                    best_width = width
                    best_mass = mass
                break

    return float(bins[best_start]), float(bins[best_end + 1])


def compute_profile_stats(
    ticks: np.ndarray,
    density: np.ndarray,
    bins: np.ndarray,
) -> dict[str, Any]:
    """
    Compute statistical features for a density profile.
    """
    if len(density) == 0:
        raise ValueError("density must not be empty")

    bin_centers = (bins[:-1] + bins[1:]) / 2

    if np.sum(density) == 0:
        poc_price = float(bin_centers[len(bin_centers) // 2])
        concentration_ratio = 0.0
    else:
        poc_price = float(bin_centers[np.argmax(density)])
        concentration_ratio = float(np.max(density) / np.mean(density))

    val, vah = _contiguous_value_area(density, bins)

    if len(np.unique(ticks)) <= 1:
        profile_skew, profile_kurtosis = 0.0, 0.0
    else:
        profile_skew = float(skew(ticks, bias=False))
        profile_kurtosis = float(kurtosis(ticks, bias=False))

    return {
        "poc_price": poc_price,
        "skew": profile_skew,
        "kurtosis": profile_kurtosis,
        "value_area_low": val,
        "value_area_high": vah,
        "concentration_ratio": concentration_ratio,
    }
