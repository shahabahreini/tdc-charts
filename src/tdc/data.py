import os

import pandas as pd
import requests
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import DataConfig
from .exceptions import DataFetchError
from .logger import logger


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def fetch_yf_data(
    ticker: str,
    interval: str,
    period: str,
    *,
    prepost: bool = False,
) -> pd.DataFrame:
    """
    Fetch data from Yahoo Finance with retry logic.
    """
    logger.debug(f"Fetching data for {ticker} (interval: {interval}, period: {period})")
    try:
        t = yf.Ticker(ticker)
        df = t.history(interval=interval, period=period, prepost=prepost)
    except Exception as e:
        raise DataFetchError(f"Network or yfinance error while fetching {ticker}: {e}") from e
    
    if df.empty:
        raise DataFetchError(
            f"Yahoo Finance returned an empty dataframe for {ticker}. Check the ticker symbol.",
        )

    return df


def normalize_yf_ohlcv(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    required_cols = ["Open", "High", "Low", "Close"]
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Missing required column '{col}' in data for {ticker}.")
            raise DataFetchError(f"Missing required column: {col}")

    if df[required_cols].isnull().values.any():
        logger.warning("Data contains missing OHLC values. Dropping incomplete bars.")
        df = df.dropna(subset=required_cols)
        if df.empty:
            raise DataFetchError("Data is empty after dropping incomplete OHLC bars.")

    if "Volume" in df.columns and df["Volume"].isnull().any():
        logger.warning("Volume contains missing values. Leaving affected rows unweighted.")

    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
    )

    if df.index.name in ["Date", "Datetime"]:
        df = df.reset_index()
        df = df.rename(columns={"Date": "timestamp", "Datetime": "timestamp"})

    return df


def _parse_period_to_days(period: str) -> int:
    value = period.strip().lower()
    try:
        if value.endswith("d"):
            return int(value[:-1])
        if value.endswith("wk"):
            return int(value[:-2]) * 7
        if value.endswith("mo"):
            return int(value[:-2]) * 31
        if value.endswith("y"):
            return int(value[:-1]) * 365
    except ValueError as exc:
        raise DataFetchError(f"Invalid period: {period}") from exc
    raise DataFetchError(f"Unsupported period format: {period}")


def _get_api_key() -> str:
    key = os.getenv("ALPHA_VANTAGE_API_KEY") or os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise DataFetchError(
            "Alpha Vantage API key is missing. Please set the ALPHA_VANTAGE_API_KEY "
            "environment variable in your environment or .env file."
        )
    return key


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def fetch_alphavantage_data(
    ticker: str,
    interval: str,
    period: str,
) -> pd.DataFrame:
    """
    Fetch daily data from Alpha Vantage.
    """
    if interval != "1d":
        raise DataFetchError(
            f"Alpha Vantage parent source currently only supports '1d' interval. Got '{interval}'."
        )

    api_key = _get_api_key()
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize=full&apikey={api_key}"

    logger.debug(f"Fetching Alpha Vantage daily data for {ticker}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise DataFetchError(
            f"HTTP request error while fetching {ticker} from Alpha Vantage: {e}"
        ) from e

    # Check for error or note in JSON
    if "Error Message" in data:
        raise DataFetchError(f"Alpha Vantage API error: {data['Error Message']}")
    if "Note" in data:
        raise DataFetchError(f"Alpha Vantage rate limit: {data['Note']}")

    data_key = "Time Series (Daily)"
    if data_key not in data:
        raise DataFetchError(
            f"Alpha Vantage response missing expected data key. Keys: {list(data.keys())}"
        )

    time_series = data[data_key]
    df_data = []
    for date_str, ohlcv in time_series.items():
        df_data.append({
            "Date": date_str,
            "Open": float(ohlcv["1. open"]),
            "High": float(ohlcv["2. high"]),
            "Low": float(ohlcv["3. low"]),
            "Close": float(ohlcv["4. close"]),
            "Volume": float(ohlcv["5. volume"])
        })

    df = pd.DataFrame(df_data)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    # Apply period filter
    try:
        days = _parse_period_to_days(period)
        start_date = pd.Timestamp.now() - pd.Timedelta(days=days)
        df = df[df.index >= start_date]
    except Exception as e:
        logger.warning(
            f"Could not filter Alpha Vantage daily data by period '{period}': {e}. "
            "Returning full history."
        )

    if df.empty:
        raise DataFetchError(
            f"Alpha Vantage returned no daily data for {ticker} in the period {period}"
        )

    return df


def get_data(config: DataConfig, enable_volume_weighting: bool = False) -> pd.DataFrame:
    """
    Orchestrates fetching and cleaning of data.
    """
    try:
        if config.source == "alphavantage":
            df = fetch_alphavantage_data(config.ticker, config.interval, config.period)
        else:
            df = fetch_yf_data(config.ticker, config.interval, config.period)
    except DataFetchError:
        logger.error(f"Failed to retrieve data for {config.ticker}")
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve data for {config.ticker}: {e}")
        raise DataFetchError(f"Failed to retrieve data for ticker '{config.ticker}': {e}") from e

    if enable_volume_weighting and "Volume" not in df.columns:
        logger.warning(
            f"'Volume' column missing for {config.ticker}. Falling back to unweighted density.",
        )

    df = normalize_yf_ohlcv(df, config.ticker)

    logger.info(f"Successfully fetched {len(df)} bars for {config.ticker}")
    return df
