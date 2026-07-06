from pathlib import Path

import pandas as pd

from .exceptions import ExportError
from .logger import logger


def save_features(
    df: pd.DataFrame,
    output_dir: str,
    ticker: str,
    formats: list[str] | None = None,
) -> list[Path]:
    """
    Save extracted features to the configured artifact formats.
    """
    export_formats = formats or ["csv"]
    saved_paths: list[Path] = []

    try:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)

        if "csv" in export_formats:
            csv_path = path / f"{ticker}_features.csv"
            df.to_csv(csv_path, index=False)
            saved_paths.append(csv_path)
            logger.info(f"Features exported to CSV: {csv_path}")

        if "parquet" in export_formats:
            parquet_path = path / f"{ticker}_features.parquet"
            df.to_parquet(parquet_path, index=False)
            saved_paths.append(parquet_path)
            logger.info(f"Features exported to Parquet: {parquet_path}")

        return saved_paths
    except PermissionError as e:
        logger.error(f"Permission denied when writing features to '{output_dir}'.")
        raise ExportError(f"Permission error saving features to '{output_dir}': {e}") from e
    except ImportError as e:
        logger.error("Parquet export requires an installed parquet engine such as pyarrow.")
        raise ExportError(
            "Parquet export requires pyarrow. Install it or remove parquet from export_formats.",
        ) from e
    except Exception as e:
        logger.error(f"Failed to export features for {ticker}: {e}")
        raise ExportError(f"Failed to export features for ticker '{ticker}': {e}") from e
