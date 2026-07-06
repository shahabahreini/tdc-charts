# TimeDensityCandle (TDC)

[![Python Support](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Testing: Pytest](https://img.shields.io/badge/tests-Pytest-green.svg)](https://pytest.org/)

**TimeDensityCandle (TDC)** is an advanced financial charting and feature extraction library that overlays a **time-at-price density profile (heatmap)** directly onto traditional OHLC (Open, High, Low, Close) candlestick charts. It goes beyond standard 4-point price bars to reveal the internal distribution of market activity and liquidity within each bar.

![TimeDensityCandle Chart Preview](assets/chart_preview.png)

---

## Key Features

* **Time-at-Price Density Heatmaps**: Renders intradar density directly inside the candle body, using a smooth opacity gradient to show where the price spent the most time.
* **Dominant Candlestick Aesthetics**: Traditional candle wicks and body outlines remain dominant (using professional, TradingView-inspired dark theme colors), while density overlays act as complementary visual guides.
* **Interactive HTML Legends**: Turn individual chart features (Value Area, POC marker, POC drift, Indecision flags) on and off directly from the Plotly interactive legend.
* **Market Profile Metrics**: Computes and overlays critical order order flow / volume profile concepts:
* **Point of Control (POC)**: The price level with the highest time/volume density in a bar.
* **Value Area (VA)**: The contiguous range representing approximately 68% of the candle's density.
* **Indecision Flags**: Automated detection of bars with a low concentration of activity (high indecision/range expansion).
* **Intrabar Tick Simulation**: High-fidelity synthetic tick paths simulate market microstructure and price paths when raw tick data is unavailable.
* **Multi-Format Feature Export**: Saves computed features (POC, Value Area high/low, skewness, kurtosis, concentration ratio) to CSV or high-performance Apache Parquet formats.

---

## Installation

Ensure you have [Python 3.10+](https://www.python.org/) and [uv](https://github.com/astral-sh/uv) (fast Python package installer/resolver) installed.

```bash
# Clone the repository
git clone https://github.com/shahabahreini/tdc-charts.git
cd tdc-charts

# Sync dependencies and create virtual environment
uv sync --dev
```

---

## Quick Start

### Running the CLI Tool
Generate a default chart (fetching Yahoo Finance data for Apple Inc. `AAPL` and rendering files in `output/`):

```bash
uv run tdc
```

To run with a custom configuration file:

```bash
uv run tdc --config custom_config.yaml
```

### Programmatic Python API Usage
You can integrate TDC feature extraction and rendering into your own trading algorithms or quantitative notebooks:

```python
import numpy as np
import pandas as pd
from tdc.config import RenderingConfig, FeaturesConfig
from tdc.render import build_heatmap_chart

# Create a sample feature DataFrame
data = pd.DataFrame({
    "open": [10.0, 11.0, 10.5],
    "high": [12.0, 12.5, 11.5],
    "low": [9.0, 10.0, 9.5],
    "close": [11.0, 10.5, 10.2],
    "density_00": [0.2, 0.5, 1.0],
    "density_01": [1.0, 0.5, 0.2],
    "poc_price": [10.5, 11.5, 10.0],
    "value_area_low": [10.0, 10.8, 9.8],
    "value_area_high": [11.0, 11.8, 10.8],
    "concentration_ratio": [1.8, 1.1, 2.2],
})

# Initialize configurations
rendering_cfg = RenderingConfig()
features_cfg = FeaturesConfig()

# Generate the Plotly figure
fig = build_heatmap_chart(data, rendering_cfg, features_cfg)

# Save the chart as interactive HTML or PNG
fig.write_html("my_tdc_chart.html")
fig.write_image("my_tdc_chart.png")
```

---

## Configuration Reference

The application reads options from `tdc.yaml` by default. Below is a summary of the configuration parameters:

| Config Path | Type | Default | Description |
| :--- | :---: | :--- | :--- |
| **`app.debug`** | `bool` | `false` | Enables verbose debug logging. |
| **`app.output_dir`** | `str` | `"./output"` | Directory where charts and tables are saved. |
| **`app.log_level`** | `str` | `"INFO"` | Console logger verbosity (`DEBUG`, `INFO`, etc.). |
| **`data.ticker`** | `str` | `"AAPL"` | Yahoo Finance ticker symbol. |
| **`data.interval`** | `str` | `"1d"` | Bar time interval (e.g. `1d`, `1h`, `15m`). |
| **`data.period`** | `str` | `"1mo"` | Lookback period to fetch (e.g. `1mo`, `3mo`, `1y`). |
| **`algorithm.mode`** | `str` | `"synthetic"` | Tick generation mode (`synthetic` supported). |
| **`algorithm.nbins`** | `int` | `20` | Number of density price bins within each bar. |
| **`algorithm.volatility_factor`** | `float` | `0.03` | Noise factor for synthetic tick path simulation. |
| **`algorithm.synthetic_tick_count`** | `int` | `100` | Number of simulated price ticks per bar. |
| **`algorithm.random_seed`** | `int` / `null` | `42` | Base seed for reproducible synthetic tick paths. |
| **`algorithm.enable_volume_weighting`** | `bool` | `false` | Uses bar volume to weight density bins. |
| **`features.export_formats`** | `list` | `["csv"]` | Enabled export formats (`"csv"`, `"parquet"`). |
| **`features.enable_poc_marker`** | `bool` | `true` | Renders a gold horizontal POC tick line. |
| **`features.enable_poc_drift_line`** | `bool` | `true` | Connects POC prices with a dashed gold line. |
| **`features.enable_value_area`** | `bool` | `true` | Renders dotted blue Value Area boxes. |
| **`features.enable_indecision_flags`** | `bool` | `true` | Flags range-expansion / low-concentration bars. |
| **`features.indecision_quantile`** | `float` | `0.25` | Lower threshold quantile for indecision flags. |
| **`rendering.full_heatmap`** | `bool` | `false` | Renders density heatmap over the full candle range (low to high) instead of just inside the body. |
| **`rendering.extend_to_tails`** | `bool` | `false` | Extends the density heatmap over the candle tails/wicks with a narrower width. |
| **`rendering.legend.enabled`** | `bool` | `true` | Toggles rendering of the chart legend. |
| **`rendering.legend.position`** | `str` | `"top_right"` | Legend layout position. |

---

## Chart Elements & Aesthetics

1.  **TradingView-Inspired Palette**: Smooth Emerald (`rgba(38, 166, 154, ...)`) for bullish candles and Coral (`rgba(239, 83, 80, ...)`) for bearish candles.
2. **Dominant Candlestick Shape**: Candle bodies are outlined in their dominant color with a border width of `1.5px` and pre-filled with a low-opacity base color.
3. **Density Heatmap**: Smooth, subtle color blocks showing price-time density. Can be toggled on/off in the legend. Can be configured to cover the full high/low range (`full_heatmap`), or extended over the candle tails with a narrower width (`extend_to_tails`).
4. **Value Area (VA)**: Represented as dotted blue boundary lines enclosing the highest density region (typically ~68% of the candle's price distribution). Can be toggled on/off in the legend.
5. **Point of Control (POC)**: Gold horizontal lines representing the maximum-density level. Can be toggled on/off in the legend.

---

## Development

Run test suite, verify code style, and build local packages:

```bash
# Run style and lint checks
uv run ruff check .

# Execute tests
uv run pytest

# Build wheels & distribution packages
uv build
```

Bumping the package version:
```bash
uv version --bump patch  # 0.1.0 -> 0.1.1
uv version --bump minor  # 0.1.0 -> 0.2.0
uv version --bump major  # 0.1.0 -> 1.0.0
```

### Release Workflow
Pushing a release tag (e.g. `v1.0.0`) from the `main` branch automatically triggers GitHub Actions to run the test suite, lint code with Ruff, compile the wheel, and publish it to a GitHub release.

---

## License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
