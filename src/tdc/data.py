import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import DataConfig
from .exceptions import DataFetchError
from .logger import logger


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def fetch_yf_data(ticker: str, interval: str, period: str) -> pd.DataFrame:
    """
    Fetch data from Yahoo Finance with retry logic.
    """
    logger.debug(f"Fetching data for {ticker} (interval: {interval}, period: {period})")
    try:
        t = yf.Ticker(ticker)
        df = t.history(interval=interval, period=period)
    except Exception as e:
        raise DataFetchError(f"Network or yfinance error while fetching {ticker}: {e}") from e
    
    if df.empty:
        raise DataFetchError(
            f"Yahoo Finance returned an empty dataframe for {ticker}. Check the ticker symbol.",
        )

    return df


def get_data(config: DataConfig, enable_volume_weighting: bool = False) -> pd.DataFrame:
    """
    Orchestrates fetching and cleaning of data.
    """
    try:
        df = fetch_yf_data(config.ticker, config.interval, config.period)
    except DataFetchError:
        logger.error(f"Failed to retrieve data for {config.ticker}")
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve data for {config.ticker}: {e}")
        raise DataFetchError(f"Failed to retrieve data for ticker '{config.ticker}': {e}") from e

    # Ensure standard OHLC columns exist
    required_cols = ["Open", "High", "Low", "Close"]
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Missing required column '{col}' in data for {config.ticker}.")
            raise DataFetchError(f"Missing required column: {col}")

    if enable_volume_weighting and "Volume" not in df.columns:
        logger.warning(
            f"'Volume' column missing for {config.ticker}. Falling back to unweighted density.",
        )

    # Handle NaNs gracefully
    if df.isnull().values.any():
        logger.warning("Data contains NaN values. Forward filling...")
        df = df.ffill().dropna()
        if df.empty:
            raise DataFetchError("Data is empty after dropping remaining NaNs.")

    # Rename columns to lowercase for consistency with the rest of the project
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
    )

    # Reset index to make timestamp a column if it is the index
    if df.index.name in ["Date", "Datetime"]:
        df = df.reset_index()
        df = df.rename(columns={"Date": "timestamp", "Datetime": "timestamp"})

    logger.info(f"Successfully fetched {len(df)} bars for {config.ticker}")
    return df
