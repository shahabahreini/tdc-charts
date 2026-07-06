import os
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from ruamel.yaml import YAML

from .exceptions import ConfigError
from .logger import logger


class AppConfig(BaseModel):
    debug: bool = Field(default=False, description="Enable debug logging")
    output_dir: str = Field(default="./output", description="Directory for saving charts and CSVs")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Console log level",
    )


class DataConfig(BaseModel):
    ticker: str = Field(..., description="Yahoo Finance ticker symbol (e.g. AAPL)")
    interval: str = Field(default="1d", description="Time interval (e.g. 1d, 1mo)")
    period: str = Field(default="1mo", description="Time period to fetch (e.g. 1mo, 1y)")


class AlgorithmConfig(BaseModel):
    mode: Literal["synthetic", "real"] = Field(default="synthetic")
    nbins: int = Field(default=20, ge=1, description="Number of density bins")
    volatility_factor: float = Field(default=0.03, ge=0.0)
    enable_volume_weighting: bool = Field(default=False)
    synthetic_tick_count: int = Field(default=100, ge=4)
    random_seed: int | None = Field(default=None)


class FeaturesConfig(BaseModel):
    export_csv: bool = Field(default=True)
    export_formats: list[Literal["csv", "parquet"]] = Field(default_factory=lambda: ["csv"])
    enable_poc_overlay: bool | None = Field(default=None, exclude=True)
    enable_poc_marker: bool = Field(default=True)
    enable_poc_drift_line: bool = Field(default=True)
    enable_value_area: bool = Field(default=True)
    concentration_ratio_flagging: bool | None = Field(default=None, exclude=True)
    enable_indecision_flags: bool = Field(default=True)
    indecision_quantile: float = Field(default=0.25, ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def apply_legacy_feature_flags(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if "enable_poc_overlay" in data:
            legacy_poc = data["enable_poc_overlay"]
            data.setdefault("enable_poc_marker", legacy_poc)
            data.setdefault("enable_poc_drift_line", legacy_poc)

        if "concentration_ratio_flagging" in data:
            data.setdefault("enable_indecision_flags", data["concentration_ratio_flagging"])

        return data

    @field_validator("export_formats")
    @classmethod
    def require_export_format(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one export format must be configured")
        return value


class ColorScheme(BaseModel):
    bull: str = Field(default="rgba(38, 166, 154, {alpha})")
    bear: str = Field(default="rgba(239, 83, 80, {alpha})")


class OverlayStyle(BaseModel):
    poc_color: str = Field(default="gold")
    poc_width: int = Field(default=3, ge=1)
    poc_drift_dash: str = Field(default="dash")
    value_area_color: str = Field(default="deepskyblue")
    value_area_fill: str = Field(default="rgba(0, 191, 255, 0.08)")
    value_area_dash: str = Field(default="dot")
    indecision_color: str = Field(default="purple")
    indecision_size: int = Field(default=11, ge=1)
    candle_half_width: float = Field(default=0.4, gt=0.0, lt=0.5)


class LegendConfig(BaseModel):
    enabled: bool = Field(default=True)
    position: Literal["top_right", "top_left", "bottom_right", "bottom_left"] = Field(
        default="top_right",
    )


class RenderingConfig(BaseModel):
    enable_chart: bool = Field(default=True)
    full_heatmap: bool = Field(
        default=False,
        description=(
            "Render density heatmap over the full candle range (low to high) "
            "instead of just inside the body"
        ),
    )
    extend_to_tails: bool = Field(
        default=False,
        description="Extend the density heatmap over the candle tails/wicks with a narrower width",
    )
    color_scheme: ColorScheme = Field(default_factory=ColorScheme)
    overlay_style: OverlayStyle = Field(default_factory=OverlayStyle)
    legend: LegendConfig = Field(default_factory=LegendConfig)


class TDCConfig(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    data: DataConfig
    algorithm: AlgorithmConfig = Field(default_factory=AlgorithmConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    rendering: RenderingConfig = Field(default_factory=RenderingConfig)

def load_config(path: str = "tdc.yaml") -> TDCConfig:
    if not os.path.exists(path):
        logger.error(f"Configuration file not found: {path}")
        raise ConfigError(f"Missing config file: {path}")

    yaml = YAML(typ="safe")
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.load(f) or {}
    except OSError as e:
        logger.error(f"Failed to read YAML file: {path}")
        raise ConfigError(f"Cannot read config file '{path}': {e}") from e
    except Exception as e:
        logger.error(f"Failed to parse YAML file: {path}")
        raise ConfigError(f"YAML parsing error: {e}") from e

    try:
        config = TDCConfig(**data)
        logger.debug("Configuration successfully loaded and validated.")
        return config
    except ValidationError as e:
        logger.error("Configuration validation failed:")
        for error in e.errors():
            loc = " -> ".join([str(x) for x in error["loc"]])
            logger.error(f"  [{loc}]: {error['msg']}")
        raise ConfigError("Invalid configuration parameters") from e
