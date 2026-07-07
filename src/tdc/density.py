from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from scipy.stats import kurtosis, skew

PocTiePolicy = Literal["first", "midpoint", "centroid", "ambiguous"]


@dataclass(frozen=True)
class ValueAreaResult:
    low: float
    high: float
    mass_share: float
    confidence: float
    is_ambiguous: bool


@dataclass(frozen=True)
class PocResult:
    price: float
    bin_index: int
    tie_count: int
    mass_share: float
    confidence: float
    is_ambiguous: bool


def _as_1d_float_array(name: str, values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if len(array) == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _price_tolerance(low: float, high: float) -> float:
    return max(abs(high - low), abs(low), abs(high), 1.0) * 1e-9


def _validate_profile_inputs(
    density: np.ndarray,
    bins: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    density_array = _as_1d_float_array("density", density)
    bins_array = _as_1d_float_array("bins", bins)

    if len(bins_array) != len(density_array) + 1:
        raise ValueError("bins must have exactly one more element than density")
    if np.any(density_array < 0):
        raise ValueError("density must not contain negative values")
    if np.any(np.diff(bins_array) < 0):
        raise ValueError("bins must be monotonically increasing")

    return density_array, bins_array


def compute_density_profile(
    ticks: np.ndarray,
    low: float,
    high: float,
    nbins: int,
    volume: np.ndarray | None = None,
    *,
    strict_range: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute a normalized time-at-price density profile.
    """
    if nbins < 1:
        raise ValueError("nbins must be at least 1")
    if not np.isfinite(low) or not np.isfinite(high):
        raise ValueError("low and high must be finite")
    if high < low:
        raise ValueError(f"high ({high}) must be greater than or equal to low ({low})")

    tick_array = _as_1d_float_array("ticks", ticks)
    weights = None
    if volume is not None:
        weights = _as_1d_float_array("volume", volume)
        if len(weights) != len(tick_array):
            raise ValueError("volume must have the same length as ticks")
        if np.any(weights < 0):
            raise ValueError("volume must not contain negative values")

    tolerance = _price_tolerance(low, high)
    outside_range = (tick_array < low - tolerance) | (tick_array > high + tolerance)
    if strict_range and np.any(outside_range):
        raise ValueError("ticks must be inside the low/high range")
    tick_array = np.clip(tick_array, low, high)

    if high == low:
        density = np.ones(nbins, dtype=float)
        if weights is not None and float(np.sum(weights)) == 0.0:
            density = np.zeros(nbins, dtype=float)
        return density, np.full(nbins + 1, low, dtype=float)

    bins = np.linspace(low, high, nbins + 1)
    counts, _ = np.histogram(tick_array, bins=bins, weights=weights)

    max_count = float(np.max(counts))
    density = np.zeros(nbins, dtype=float) if max_count <= 0 else counts / max_count
    return density.astype(float), bins


def _profile_centroid(density: np.ndarray, bins: np.ndarray) -> float:
    centers = (bins[:-1] + bins[1:]) / 2
    total_mass = float(np.sum(density))
    if total_mass <= 0:
        return float((bins[0] + bins[-1]) / 2)
    return float(np.average(centers, weights=density))


def _normalized_entropy(density: np.ndarray) -> float:
    total_mass = float(np.sum(density))
    if total_mass <= 0 or len(density) <= 1:
        return 0.0

    probabilities = density / total_mass
    positive = probabilities[probabilities > 0]
    entropy = -float(np.sum(positive * np.log(positive)))
    return float(entropy / np.log(len(density)))


def _hhi(density: np.ndarray) -> float:
    total_mass = float(np.sum(density))
    if total_mass <= 0:
        return 0.0
    probabilities = density / total_mass
    return float(np.sum(probabilities * probabilities))


def _compute_poc(
    density: np.ndarray,
    bins: np.ndarray,
    tie_policy: PocTiePolicy,
) -> PocResult:
    centers = (bins[:-1] + bins[1:]) / 2
    total_mass = float(np.sum(density))
    price_span = float(bins[-1] - bins[0])

    if price_span == 0:
        return PocResult(
            price=float(bins[0]),
            bin_index=0,
            tie_count=len(density),
            mass_share=1.0 if total_mass > 0 else 0.0,
            confidence=1.0 if total_mass > 0 else 0.0,
            is_ambiguous=False,
        )

    if total_mass <= 0:
        return PocResult(
            price=float((bins[0] + bins[-1]) / 2),
            bin_index=len(density) // 2,
            tie_count=len(density),
            mass_share=0.0,
            confidence=0.0,
            is_ambiguous=True,
        )

    max_density = float(np.max(density))
    tied = np.flatnonzero(np.isclose(density, max_density))
    tie_count = int(len(tied))

    if tie_policy == "first":
        poc_index = int(tied[0])
        price = float(centers[poc_index])
    elif tie_policy == "centroid":
        poc_index = int(tied[len(tied) // 2])
        price = float(np.average(centers[tied], weights=density[tied]))
    else:
        poc_index = int(tied[len(tied) // 2])
        price = float(np.mean(centers[tied]))

    non_tied = np.setdiff1d(np.arange(len(density)), tied, assume_unique=True)
    second_density = (
        0.0
        if tie_count > 1 or len(non_tied) == 0
        else float(np.max(density[non_tied]))
    )
    dominance = 0.0 if max_density <= 0 else (max_density - second_density) / max_density
    mass_share = max_density / total_mass
    confidence = max(0.0, min(1.0, (0.75 * dominance) + (0.25 * mass_share)))
    if tie_count > 1:
        confidence /= tie_count

    return PocResult(
        price=price,
        bin_index=poc_index,
        tie_count=tie_count,
        mass_share=float(mass_share),
        confidence=float(confidence),
        is_ambiguous=tie_count > 1 or tie_policy == "ambiguous",
    )


def _contiguous_value_area(
    density: np.ndarray,
    bins: np.ndarray,
    target_ratio: float = 0.68,
    anchor_price: float | None = None,
) -> ValueAreaResult:
    total_mass = float(np.sum(density))
    price_span = float(bins[-1] - bins[0])
    if total_mass <= 0:
        return ValueAreaResult(float(bins[0]), float(bins[-1]), 0.0, 0.0, True)
    if price_span == 0:
        return ValueAreaResult(float(bins[0]), float(bins[0]), 1.0, 1.0, False)

    target_mass = total_mass * target_ratio
    candidates: list[tuple[int, int, float, float]] = []
    for start in range(len(density)):
        mass = 0.0
        for end in range(start, len(density)):
            mass += float(density[end])
            if mass >= target_mass:
                width = float(bins[end + 1] - bins[start])
                candidates.append((start, end, width, mass))
                break

    if not candidates:
        return ValueAreaResult(float(bins[0]), float(bins[-1]), 1.0, 0.0, True)

    min_width = min(candidate[2] for candidate in candidates)
    width_ties = [item for item in candidates if np.isclose(item[2], min_width)]
    max_mass = max(candidate[3] for candidate in width_ties)
    mass_ties = [item for item in width_ties if np.isclose(item[3], max_mass)]

    anchor = _profile_centroid(density, bins) if anchor_price is None else anchor_price
    distances = [
        abs(((bins[start] + bins[end + 1]) / 2) - anchor)
        for start, end, _, _ in mass_ties
    ]
    min_distance = min(distances)
    final_ties = [
        item
        for item, distance in zip(mass_ties, distances, strict=True)
        if np.isclose(distance, min_distance)
    ]
    start, end, _, mass = final_ties[len(final_ties) // 2]
    width_pct = float((bins[end + 1] - bins[start]) / price_span)
    confidence = max(0.0, min(1.0, 1.0 - width_pct))

    return ValueAreaResult(
        low=float(bins[start]),
        high=float(bins[end + 1]),
        mass_share=float(mass / total_mass),
        confidence=confidence,
        is_ambiguous=len(final_ties) > 1,
    )


def _safe_distribution_moment(value: float) -> float:
    return float(value) if np.isfinite(value) else 0.0


def compute_profile_stats(
    ticks: np.ndarray,
    density: np.ndarray,
    bins: np.ndarray,
    *,
    value_area_ratio: float = 0.68,
    poc_tie_policy: PocTiePolicy = "midpoint",
) -> dict[str, Any]:
    """
    Compute statistical features for a density profile.
    """
    if not 0.0 < value_area_ratio <= 1.0:
        raise ValueError("value_area_ratio must be in the range (0, 1]")

    tick_array = _as_1d_float_array("ticks", ticks)
    density_array, bins_array = _validate_profile_inputs(density, bins)
    poc = _compute_poc(density_array, bins_array, poc_tie_policy)
    val = _contiguous_value_area(
        density_array,
        bins_array,
        target_ratio=value_area_ratio,
        anchor_price=poc.price,
    )

    if len(np.unique(tick_array)) <= 1 or len(tick_array) < 3:
        profile_skew = 0.0
    else:
        profile_skew = _safe_distribution_moment(skew(tick_array, bias=False))

    if len(np.unique(tick_array)) <= 1 or len(tick_array) < 4:
        profile_kurtosis = 0.0
    else:
        profile_kurtosis = _safe_distribution_moment(kurtosis(tick_array, bias=False))

    total_mass = float(np.sum(density_array))
    mean_density = float(np.mean(density_array))
    max_density = float(np.max(density_array)) if len(density_array) else 0.0
    price_span = float(bins_array[-1] - bins_array[0])
    value_area_width = float(val.high - val.low)
    entropy_norm = _normalized_entropy(density_array)
    hhi = _hhi(density_array)

    return {
        "poc_price": poc.price,
        "poc_bin_index": poc.bin_index,
        "poc_tie_count": poc.tie_count,
        "poc_mass_share": poc.mass_share,
        "poc_confidence": poc.confidence,
        "poc_is_ambiguous": poc.is_ambiguous,
        "skew": profile_skew,
        "kurtosis": profile_kurtosis,
        "value_area_low": val.low,
        "value_area_high": val.high,
        "value_area_mass_share": val.mass_share,
        "value_area_width": value_area_width,
        "value_area_width_pct": 0.0 if price_span == 0 else value_area_width / price_span,
        "value_area_confidence": val.confidence,
        "value_area_is_ambiguous": val.is_ambiguous,
        "concentration_ratio": 0.0 if mean_density <= 0 else max_density / mean_density,
        "profile_entropy": entropy_norm,
        "profile_hhi": hhi,
        "density_mass": total_mass,
        "profile_degenerate": price_span == 0,
    }
