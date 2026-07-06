import os
from pathlib import Path
import pandas as pd
from .exceptions import ExportError
from .logger import logger

def save_features(df: pd.DataFrame, output_dir: str, ticker: str):
    """
    Saves the extracted features to a CSV file.
    """
    try:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        
        file_path = path / f"{ticker}_features.csv"
        df.to_csv(file_path, index=False)
        logger.info(f"Features successfully exported to: {file_path}")
    except PermissionError as e:
        logger.error(f"Permission denied when writing to {file_path}. Is the file open?")
        raise ExportError(f"Permission error saving features: {e}") from e
    except Exception as e:
        logger.error(f"Failed to export features: {e}")
        raise ExportError(f"Failed to export features: {e}") from e
