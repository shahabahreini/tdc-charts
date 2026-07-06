import os
from typing import Literal, Dict
from pydantic import BaseModel, Field, ValidationError
from ruamel.yaml import YAML
from .exceptions import ConfigError
from .logger import logger

class AppConfig(BaseModel):
    debug: bool = Field(default=False, description="Enable debug logging")
    output_dir: str = Field(default="./output", description="Directory for saving charts and CSVs")

class DataConfig(BaseModel):
    ticker: str = Field(..., description="Yahoo Finance ticker symbol (e.g. AAPL)")
    interval: str = Field(default="1d", description="Time interval (e.g. 1d, 1mo)")
    period: str = Field(default="1mo", description="Time period to fetch (e.g. 1mo, 1y)")

class AlgorithmConfig(BaseModel):
    mode: Literal["synthetic", "real"] = Field(default="synthetic")
    nbins: int = Field(default=20, ge=1, description="Number of density bins")
    volatility_factor: float = Field(default=0.03, ge=0.0)
    enable_volume_weighting: bool = Field(default=False)

class FeaturesConfig(BaseModel):
    export_csv: bool = Field(default=True)
    enable_poc_overlay: bool = Field(default=True)
    enable_value_area: bool = Field(default=True)
    concentration_ratio_flagging: bool = Field(default=True)

class ColorScheme(BaseModel):
    bull: str = Field(default="rgba(0, 255, 0, {alpha})")
    bear: str = Field(default="rgba(255, 0, 0, {alpha})")

class RenderingConfig(BaseModel):
    enable_chart: bool = Field(default=True)
    color_scheme: ColorScheme = Field(default_factory=ColorScheme)

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
        
    yaml = YAML(typ='safe')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.load(f) or {}
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
