import math
from collections.abc import Iterable

import numpy as np
import pandas as pd

from .config import TDCConfig
from .density import compute_density_profile, compute_profile_stats
from .exceptions import AlgorithmError
from .intrabar import extract_intrabar_arrays, get_intrabar_slice, load_intrabar_data
from .simulate import simulate_intrabar_ticks


def _validate_ohlc(row: pd.Series, bar_number: int) -> tuple[float, float, float, float]:
    open_p = float(row["open"])
    high_p = float(row["high"])
    low_p = float(row["low"])
    close_p = float(row["close"])
    prices = [open_p, high_p, low_p, close_p]

    if not all(math.isfinite(price) for price in prices):
        raise AlgorithmError(f"Bar {bar_number} has non-finite OHLC values")
    if high_p < low_p:
        raise AlgorithmError(f"Bar {bar_number} has high below low")
    if not low_p <= open_p <= high_p:
        raise AlgorithmError(f"Bar {bar_number} has open outside low/high")
    if not low_p <= close_p <= high_p:
        raise AlgorithmError(f"Bar {bar_number} has close outside low/high")

    return open_p, high_p, low_p, close_p


def _synthetic_ticks_for_bar(
    open_p: float,
    high_p: float,
    low_p: float,
    close_p: float,
    bar_number: int,
    config: TDCConfig,
) -> np.ndarray:
    paths = []
    base_seed = config.algorithm.random_seed
    for member in range(config.algorithm.synthetic_ensemble_size):
        seed = None
        if base_seed is not None:
            seed = base_seed + (bar_number * 10_000) + member
        paths.append(
            simulate_intrabar_ticks(
                open_p,
                high_p,
                low_p,
                close_p,
                n_ticks=config.algorithm.synthetic_tick_count,
                volatility_factor=config.algorithm.volatility_factor,
                seed=seed,
            ),
        )
    return np.concatenate(paths)


def _synthetic_volume_weights(row: pd.Series, tick_count: int) -> np.ndarray | None:
    if "volume" not in row or pd.isna(row["volume"]):
        return None

    volume = float(row["volume"])
    if volume < 0:
        raise AlgorithmError("Volume must not be negative")
    return np.full(tick_count, volume / tick_count)


def _join_warnings(warnings: Iterable[str]) -> str:
    return ";".join(dict.fromkeys(warnings))


def _build_bar_features(
    bar_number: int,
    row: pd.Series,
    config: TDCConfig,
    ticks: np.ndarray,
    volume: np.ndarray | None,
    profile_source: str,
    volume_mode: str,
    warnings: list[str],
) -> dict[str, object]:
    open_p, high_p, low_p, close_p = _validate_ohlc(row, bar_number)
    try:
        density, bins = compute_density_profile(
            ticks,
            low_p,
            high_p,
            config.algorithm.nbins,
            volume,
        )
        stats = compute_profile_stats(
            ticks,
            density,
            bins,
            value_area_ratio=config.algorithm.value_area_ratio,
            poc_tie_policy=config.algorithm.poc_tie_policy,
        )
    except ValueError as exc:
        raise AlgorithmError(f"Bar {bar_number}: {exc}") from exc

    synthetic_model = config.algorithm.synthetic_model if profile_source == "synthetic" else ""
    row_dict: dict[str, object] = {
        "timestamp": row.get("timestamp", bar_number),
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "close": close_p,
        "tick_count": int(len(ticks)),
        "profile_source": profile_source,
        "synthetic_model": synthetic_model,
        "synthetic_ensemble_size": (
            config.algorithm.synthetic_ensemble_size if profile_source == "synthetic" else 0
        ),
        "volume_mode": volume_mode,
        "profile_warning": _join_warnings(warnings),
    }
    for j, density_value in enumerate(density):
        row_dict[f"density_{j:02d}"] = float(density_value)
    row_dict.update(stats)
    return row_dict


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.div(denominator.replace(0.0, np.nan))


def _confidence_level(value: float) -> str:
    if value >= 0.75:
        return "high"
    if value >= 0.5:
        return "medium"
    return "low"


def _add_time_gap_features(feature_df: pd.DataFrame) -> pd.DataFrame:
    feature_df["time_gap_seconds"] = 0.0
    feature_df["session_gap"] = False
    if "timestamp" not in feature_df.columns or len(feature_df) < 3:
        return feature_df

    timestamps = pd.to_datetime(feature_df["timestamp"], errors="coerce")
    if timestamps.isna().any():
        return feature_df

    gaps = timestamps.diff().dt.total_seconds().fillna(0.0)
    positive_gaps = gaps[gaps > 0]
    if positive_gaps.empty:
        return feature_df

    median_gap = float(positive_gaps.median())
    threshold = median_gap * 1.5
    feature_df["time_gap_seconds"] = gaps
    feature_df["session_gap"] = gaps > threshold
    return feature_df


def _add_confidence_features(feature_df: pd.DataFrame, config: TDCConfig) -> pd.DataFrame:
    sample_factor = np.minimum(
        1.0,
        feature_df["tick_count"] / max(config.algorithm.nbins * 5, 1),
    )
    source_base = np.where(feature_df["profile_source"] == "real", 0.9, 0.48)
    shape_confidence = (
        feature_df["poc_confidence"].astype(float)
        + feature_df["value_area_confidence"].astype(float)
    ) / 2
    ambiguity_penalty = np.where(
        feature_df["poc_is_ambiguous"] | feature_df["value_area_is_ambiguous"],
        0.75,
        1.0,
    )
    confidence = source_base * (0.5 + (0.5 * sample_factor)) * (0.5 + (0.5 * shape_confidence))
    feature_df["profile_confidence"] = np.clip(confidence * ambiguity_penalty, 0.0, 1.0)
    feature_df["confidence_level"] = feature_df["profile_confidence"].map(_confidence_level)

    low_confidence = feature_df["profile_confidence"] < 0.5
    feature_df.loc[low_confidence, "profile_warning"] = feature_df.loc[
        low_confidence,
        "profile_warning",
    ].map(lambda warning: _join_warnings([warning, "low_confidence"]))
    return feature_df


def _add_derived_features(feature_df: pd.DataFrame, config: TDCConfig) -> pd.DataFrame:
    ranges = feature_df["high"] - feature_df["low"]
    bodies = (feature_df["close"] - feature_df["open"]).abs()
    prev_close = feature_df["close"].shift(1)

    feature_df["range_size"] = ranges
    feature_df["body_size"] = bodies
    feature_df["body_to_range"] = _safe_ratio(bodies, ranges).fillna(0.0).clip(0.0, 1.0)
    feature_df["close_location"] = _safe_ratio(feature_df["close"] - feature_df["low"], ranges)
    feature_df["close_location"] = feature_df["close_location"].fillna(0.5).clip(0.0, 1.0)
    feature_df["gap_from_prev_close"] = (feature_df["open"] - prev_close).fillna(0.0)
    feature_df["gap_pct"] = _safe_ratio(feature_df["gap_from_prev_close"], prev_close).fillna(0.0)

    true_range = pd.concat(
        [
            ranges,
            (feature_df["high"] - prev_close).abs(),
            (feature_df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    feature_df["true_range"] = true_range.fillna(ranges)
    feature_df["atr_14"] = feature_df["true_range"].rolling(14, min_periods=1).mean()

    feature_df["poc_delta"] = feature_df["poc_price"].diff()
    feature_df["poc_delta_pct"] = _safe_ratio(
        feature_df["poc_delta"],
        feature_df["poc_price"].shift(1),
    )
    feature_df["poc_delta_atr"] = _safe_ratio(feature_df["poc_delta"], feature_df["atr_14"])
    feature_df["poc_slope_3"] = feature_df["poc_price"].diff(3) / 3

    feature_df = _add_time_gap_features(feature_df)
    feature_df = _add_confidence_features(feature_df, config)
    return _add_indecision_features(feature_df, config)


def _add_indecision_features(feature_df: pd.DataFrame, config: TDCConfig) -> pd.DataFrame:
    nbins = max(config.algorithm.nbins, 1)
    concentration_scaled = (feature_df["concentration_ratio"] - 1.0) / max(nbins - 1, 1)
    low_concentration = 1.0 - concentration_scaled.clip(0.0, 1.0)
    neutral_body = 1.0 - feature_df["body_to_range"].clip(0.0, 1.0)
    centered_close = 1.0 - ((feature_df["close_location"] - 0.5).abs() * 2.0)

    score = (
        (feature_df["profile_entropy"].clip(0.0, 1.0) * 0.35)
        + (low_concentration * 0.25)
        + (neutral_body * 0.20)
        + (centered_close.clip(0.0, 1.0) * 0.10)
        + (feature_df["value_area_width_pct"].clip(0.0, 1.0) * 0.10)
    )
    score = score.mask(feature_df["profile_degenerate"], 0.0)
    feature_df["indecision_score"] = score
    feature_df["indecision_threshold"] = np.nan
    feature_df["indecision_flag"] = False
    feature_df["indecision_reason"] = ""

    if not config.features.enable_indecision_flags:
        return feature_df
    if len(feature_df) < config.features.indecision_min_samples:
        return feature_df
    if feature_df["indecision_score"].nunique(dropna=True) <= 1:
        return feature_df

    threshold = float(
        feature_df["indecision_score"].quantile(
            1.0 - config.features.indecision_quantile,
        ),
    )
    flags = (feature_df["indecision_score"] >= threshold) & ~feature_df["profile_degenerate"]
    feature_df["indecision_threshold"] = threshold
    feature_df["indecision_flag"] = flags
    feature_df.loc[flags, "indecision_reason"] = "high_entropy_low_concentration_neutral_body"
    return feature_df


def build_feature_frame(df: pd.DataFrame, config: TDCConfig) -> pd.DataFrame:
    intrabar_df = load_intrabar_data(config.data) if config.algorithm.mode == "real" else None
    feature_rows: list[dict[str, object]] = []
    timestamps = pd.to_datetime(df.get("timestamp"), errors="coerce") if "timestamp" in df else None

    for bar_number, (_, row) in enumerate(df.iterrows()):
        open_p, high_p, low_p, close_p = _validate_ohlc(row, bar_number)
        warnings: list[str] = []

        if config.algorithm.mode == "synthetic":
            ticks = _synthetic_ticks_for_bar(open_p, high_p, low_p, close_p, bar_number, config)
            warnings.append("synthetic_estimate")
            volume = None
            volume_mode = "none"
            if config.algorithm.enable_volume_weighting:
                volume = _synthetic_volume_weights(row, len(ticks))
                volume_mode = "synthetic_even" if volume is not None else "none"
                warnings.append("synthetic_even_volume_weights")
            profile_source = "synthetic"
        else:
            if intrabar_df is None:
                raise AlgorithmError("Real intrabar mode was selected without intrabar data")
            next_timestamp = None
            if timestamps is not None and bar_number + 1 < len(timestamps):
                next_timestamp = pd.Timestamp(timestamps.iloc[bar_number + 1])
            intrabar_slice = get_intrabar_slice(
                intrabar_df,
                config.data,
                row,
                bar_number,
                next_timestamp,
            )
            ticks, volume = extract_intrabar_arrays(
                intrabar_slice,
                config.data,
                config.algorithm.enable_volume_weighting,
            )
            volume_mode = "real" if volume is not None else "none"
            profile_source = "real"

        feature_rows.append(
            _build_bar_features(
                bar_number,
                row,
                config,
                ticks,
                volume,
                profile_source,
                volume_mode,
                warnings,
            ),
        )

    feature_df = pd.DataFrame(feature_rows)
    if feature_df.empty:
        return feature_df
    return _add_derived_features(feature_df, config)
