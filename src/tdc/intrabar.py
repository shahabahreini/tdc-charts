from pathlib import Path

import numpy as np
import pandas as pd

from .config import DataConfig
from .exceptions import AlgorithmError, DataFetchError


def load_intrabar_data(config: DataConfig) -> pd.DataFrame:
    if config.intrabar_path is None:
        raise DataFetchError("algorithm.mode='real' requires data.intrabar_path")

    path = Path(config.intrabar_path)
    if not path.exists():
        raise DataFetchError(f"Intrabar file does not exist: {path}")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(path)
    else:
        raise DataFetchError("Intrabar input must be a CSV or Parquet file")

    if config.intrabar_price_col not in df.columns:
        raise DataFetchError(f"Missing intrabar price column: {config.intrabar_price_col}")

    df = df.copy()
    df[config.intrabar_price_col] = pd.to_numeric(df[config.intrabar_price_col], errors="coerce")
    df = df.dropna(subset=[config.intrabar_price_col])
    if df.empty:
        raise DataFetchError("Intrabar file has no valid price rows")

    if config.intrabar_timestamp_col in df.columns:
        df[config.intrabar_timestamp_col] = pd.to_datetime(
            df[config.intrabar_timestamp_col],
            errors="coerce",
        )

    if config.intrabar_volume_col in df.columns:
        df[config.intrabar_volume_col] = pd.to_numeric(
            df[config.intrabar_volume_col],
            errors="coerce",
        )

    return df


def get_intrabar_slice(
    intrabar_df: pd.DataFrame,
    config: DataConfig,
    bar: pd.Series,
    bar_number: int,
    next_timestamp: pd.Timestamp | None,
) -> pd.DataFrame:
    bar_id_col = config.intrabar_bar_id_col
    if bar_id_col in intrabar_df.columns:
        parent_id = bar.get(bar_id_col, bar_number)
        return intrabar_df[intrabar_df[bar_id_col] == parent_id]

    timestamp_col = config.intrabar_timestamp_col
    if timestamp_col not in intrabar_df.columns or "timestamp" not in bar:
        raise AlgorithmError(
            "Real intrabar mode needs either a bar_id column or timestamp columns "
            "on both bar and intrabar data.",
        )

    start = pd.to_datetime(bar["timestamp"])
    timestamps = intrabar_df[timestamp_col]
    if next_timestamp is None:
        mask = timestamps >= start
    else:
        mask = (timestamps >= start) & (timestamps < next_timestamp)
    return intrabar_df[mask]


def extract_intrabar_arrays(
    intrabar_slice: pd.DataFrame,
    config: DataConfig,
    enable_volume_weighting: bool,
) -> tuple[np.ndarray, np.ndarray | None]:
    if intrabar_slice.empty:
        raise AlgorithmError("No intrabar rows matched the parent bar")

    prices = intrabar_slice[config.intrabar_price_col].to_numpy(dtype=float)
    if not enable_volume_weighting or config.intrabar_volume_col not in intrabar_slice.columns:
        return prices, None

    volume = intrabar_slice[config.intrabar_volume_col].to_numpy(dtype=float)
    if np.isnan(volume).any():
        return prices, None
    return prices, volume
