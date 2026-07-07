import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import DataConfig
from .data import _get_api_key, fetch_yf_data, normalize_yf_ohlcv
from .exceptions import AlgorithmError, DataFetchError
from .logger import logger

_INTRADAY_LIMIT_DAYS = {
    "1m": 7,
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "60m": 60,
    "90m": 60,
    "1h": 60,
}

_REGULAR_SESSION_OPEN = "09:30"
_REGULAR_SESSION_CLOSE = "16:00"


def _period_to_days(period: str) -> int:
    value = period.strip().lower()
    try:
        if value.endswith("d"):
            return int(value[:-1])
        if value.endswith("wk"):
            return int(value[:-2]) * 7
        if value.endswith("mo"):
            return int(value[:-2]) * 31
        if value.endswith("y"):
            return int(value[:-1]) * 366
    except ValueError as exc:
        raise DataFetchError(f"Invalid Yahoo intraday period: {period}") from exc
    raise DataFetchError(
        "Yahoo intraday real mode requires a bounded period such as '7d' or '60d'.",
    )


def validate_yahoo_intraday_request(config: DataConfig) -> None:
    interval = config.intrabar_interval.lower()
    if config.interval != "1d":
        raise DataFetchError("Yahoo real mode currently supports parent interval='1d' only.")
    if interval not in _INTRADAY_LIMIT_DAYS:
        allowed = ", ".join(sorted(_INTRADAY_LIMIT_DAYS))
        raise DataFetchError(
            f"Unsupported Yahoo intraday interval '{interval}'. Use one of: {allowed}.",
        )

    period_days = _period_to_days(config.period)
    max_days = _INTRADAY_LIMIT_DAYS[interval]
    if period_days > max_days:
        raise DataFetchError(
            f"Yahoo intraday interval '{interval}' supports at most {max_days} days. "
            f"Configured data.period is '{config.period}'. Use '{max_days}d' or a shorter period.",
        )


def _localize_timestamps(timestamps: pd.Series, timezone_name: str) -> pd.Series:
    timezone = ZoneInfo(timezone_name)
    parsed = pd.to_datetime(timestamps, errors="coerce")
    if parsed.isna().any():
        raise DataFetchError("Yahoo intraday data contains invalid timestamps.")

    if parsed.dt.tz is None:
        return parsed.dt.tz_localize(timezone)
    return parsed.dt.tz_convert(timezone)


def _prepare_yahoo_intrabar(config: DataConfig, raw_df: pd.DataFrame) -> pd.DataFrame:
    intrabar = normalize_yf_ohlcv(raw_df, config.ticker).copy()
    if "timestamp" not in intrabar.columns:
        raise DataFetchError("Yahoo intraday response has no timestamp index or column.")

    intrabar["timestamp"] = _localize_timestamps(
        intrabar["timestamp"],
        config.session_timezone,
    )
    if not config.include_extended_hours:
        timestamps = intrabar["timestamp"].dt.strftime("%H:%M")
        intrabar = intrabar[
            (timestamps >= _REGULAR_SESSION_OPEN) & (timestamps < _REGULAR_SESSION_CLOSE)
        ]
        if intrabar.empty:
            raise DataFetchError("Yahoo intraday data is empty after regular-session filtering.")

    intrabar["price"] = (intrabar["high"] + intrabar["low"] + intrabar["close"]) / 3
    intrabar["session_date"] = intrabar["timestamp"].dt.date
    return intrabar.sort_values("timestamp").reset_index(drop=True)


def _build_parent_bars_from_intrabar(
    intrabar: pd.DataFrame,
    config: DataConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    aggregation = {
        "timestamp": "first",
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
    }
    if "volume" in intrabar.columns:
        aggregation["volume"] = "sum"

    parent = intrabar.groupby("session_date", sort=True).agg(aggregation).reset_index()
    if parent.empty:
        raise DataFetchError("No parent bars could be built from Yahoo intraday data.")

    timezone = ZoneInfo(config.session_timezone)
    parent["timestamp"] = pd.to_datetime(parent["timestamp"]).dt.normalize().dt.tz_convert(timezone)
    parent["bar_id"] = range(len(parent))

    date_to_bar_id = dict(zip(parent["session_date"], parent["bar_id"], strict=True))
    intrabar["bar_id"] = intrabar["session_date"].map(date_to_bar_id)
    intrabar = intrabar.drop(columns=["session_date"])
    parent = parent.drop(columns=["session_date"])
    return parent.reset_index(drop=True), intrabar.reset_index(drop=True)


def fetch_yahoo_intrabar_bars(config: DataConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    validate_yahoo_intraday_request(config)
    raw_df = fetch_yf_data(
        config.ticker,
        config.intrabar_interval,
        config.period,
        prepost=config.include_extended_hours,
    )
    intrabar = _prepare_yahoo_intrabar(config, raw_df)
    parent, intrabar = _build_parent_bars_from_intrabar(intrabar, config)
    intrabar.attrs["profile_source"] = "real_yahoo_intraday"
    intrabar.attrs["volume_mode"] = "real_subbar"
    intrabar.attrs["profile_warning"] = "subbar_ohlcv_not_tick_data"
    logger.info(
        "Built %s parent bars from %s Yahoo %s intraday rows.",
        len(parent),
        len(intrabar),
        config.intrabar_interval,
    )
    return parent, intrabar


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
    if np.any(volume < 0):
        raise AlgorithmError("Intrabar volume must not be negative")
    return prices, volume


def map_interval_to_av(interval: str) -> str:
    mapping = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "60m": "60min",
        "1h": "60min",
    }
    val = interval.lower().strip()
    if val in mapping:
        return mapping[val]
    if val.endswith("m") and val[:-1].isdigit():
        return f"{val[:-1]}min"
    return val


def get_months_in_period(period: str) -> list[str]:
    try:
        days = _period_to_days(period)
    except Exception:
        days = 30
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.Timedelta(days=days)

    dates = pd.date_range(start=start_date, end=end_date, freq="MS")
    months = [d.strftime("%Y-%m") for d in dates]

    current_month = end_date.strftime("%Y-%m")
    if current_month not in months:
        months.append(current_month)

    start_month = start_date.strftime("%Y-%m")
    if start_month not in months:
        months.insert(0, start_month)

    return sorted(list(set(months)))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def _fetch_single_av_url(url: str) -> pd.DataFrame:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise DataFetchError(f"HTTP request error: {e}") from e

    if "Error Message" in data:
        raise DataFetchError(f"Alpha Vantage API error: {data['Error Message']}")
    if "Note" in data:
        raise DataFetchError(f"Alpha Vantage rate limit: {data['Note']}")

    time_series_key = None
    for k in data.keys():
        if k.startswith("Time Series"):
            time_series_key = k
            break

    if not time_series_key:
        raise DataFetchError(
            "Alpha Vantage response missing expected time series data. "
            f"Keys: {list(data.keys())}"
        )

    time_series = data[time_series_key]
    df_data = []
    for datetime_str, ohlcv in time_series.items():
        df_data.append({
            "Datetime": datetime_str,
            "Open": float(ohlcv["1. open"]),
            "High": float(ohlcv["2. high"]),
            "Low": float(ohlcv["3. low"]),
            "Close": float(ohlcv["4. close"]),
            "Volume": float(ohlcv["5. volume"])
        })
    df = pd.DataFrame(df_data)
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    df = df.set_index("Datetime").sort_index()
    return df


def fetch_alphavantage_intraday_data(
    ticker: str,
    interval: str,
    period: str,
) -> pd.DataFrame:
    """
    Fetch intraday data from Alpha Vantage.
    Supports long time series using month-by-month historical data if period is long.
    """
    api_key = _get_api_key()
    av_interval = map_interval_to_av(interval)

    try:
        period_days = _period_to_days(period)
    except Exception as e:
        logger.warning(f"Could not parse period '{period}': {e}. Defaulting to compact 30d fetch.")
        period_days = 30

    if period_days <= 30:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval={av_interval}&outputsize=full&apikey={api_key}"
        logger.debug(f"Fetching Alpha Vantage active intraday data: {ticker} ({interval})")
        df = _fetch_single_av_url(url)
    else:
        months = get_months_in_period(period)
        logger.info(
            f"Fetching Alpha Vantage long intraday series for {ticker} ({interval}) "
            f"across {len(months)} months: {months}"
        )

        dfs = []
        for i, month in enumerate(months):
            if i > 0:
                logger.info("Sleeping 12 seconds to respect Alpha Vantage rate limits...")
                time.sleep(12)

            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval={av_interval}&month={month}&outputsize=full&apikey={api_key}"
            logger.debug(f"Fetching Alpha Vantage intraday for month {month}")
            try:
                m_df = _fetch_single_av_url(url)
                dfs.append(m_df)
            except DataFetchError as e:
                logger.warning(f"Failed to fetch intraday for month {month}: {e}")

        if not dfs:
            raise DataFetchError(
                f"Failed to fetch any intraday data for {ticker} in period {period}"
            )

        df = pd.concat(dfs).sort_index()
        df = df[~df.index.duplicated(keep="first")]

    start_date = pd.Timestamp.now() - pd.Timedelta(days=period_days)
    df = df[df.index >= start_date]
    return df


def _prepare_alphavantage_intrabar(config: DataConfig, raw_df: pd.DataFrame) -> pd.DataFrame:
    intrabar = normalize_yf_ohlcv(raw_df, config.ticker).copy()
    if "timestamp" not in intrabar.columns:
        raise DataFetchError("Alpha Vantage intraday response has no timestamp index or column.")

    intrabar["timestamp"] = _localize_timestamps(
        intrabar["timestamp"],
        config.session_timezone,
    )
    if not config.include_extended_hours:
        timestamps = intrabar["timestamp"].dt.strftime("%H:%M")
        intrabar = intrabar[
            (timestamps >= _REGULAR_SESSION_OPEN) & (timestamps < _REGULAR_SESSION_CLOSE)
        ]
        if intrabar.empty:
            raise DataFetchError(
                "Alpha Vantage intraday data is empty after regular-session filtering."
            )

    intrabar["price"] = (intrabar["high"] + intrabar["low"] + intrabar["close"]) / 3
    intrabar["session_date"] = intrabar["timestamp"].dt.date
    return intrabar.sort_values("timestamp").reset_index(drop=True)


def fetch_alphavantage_intrabar_bars(config: DataConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_df = fetch_alphavantage_intraday_data(
        config.ticker,
        config.intrabar_interval,
        config.period,
    )
    intrabar = _prepare_alphavantage_intrabar(config, raw_df)
    parent, intrabar = _build_parent_bars_from_intrabar(intrabar, config)
    intrabar.attrs["profile_source"] = "real_alphavantage_intraday"
    intrabar.attrs["volume_mode"] = "real_subbar"
    intrabar.attrs["profile_warning"] = "subbar_ohlcv_not_tick_data"
    logger.info(
        "Built %s parent bars from %s Alpha Vantage %s intraday rows.",
        len(parent),
        len(intrabar),
        config.intrabar_interval,
    )
    return parent, intrabar
