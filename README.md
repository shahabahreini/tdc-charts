# TimeDensityCandle (TDC)

TimeDensityCandle (TDC) is a Python library and CLI tool that transforms OHLCV bar data into conventional candlesticks where the body is filled with a horizontal density gradient representing time-at-price concentration.

It fetches data from Yahoo Finance, simulates intrabar ticks, computes density profiles, extracts Market Profile features (POC, Value Area), and renders beautiful Heatmap Candles via Plotly.

## Table of Contents
1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)
4. [Output](#output)
5. [Developer Documentation](#developer-documentation)

## Installation

This project uses `uv` for lightning-fast package management.

```bash
# Clone the repository
git clone https://github.com/shahabahreini/tdc-charts.git
cd tdc-charts

# Install dependencies using uv
uv sync
```

## Configuration

TDC is entirely configuration-driven via a central `tdc.yaml` file located in the root of the project.

```yaml
app:
  debug: false
  output_dir: "./output"

data:
  ticker: "AAPL"
  interval: "1d"
  period: "1mo"

algorithm:
  mode: "synthetic"
  nbins: 20
  volatility_factor: 0.03

features:
  export_csv: true
  enable_poc_overlay: true
  enable_value_area: true

rendering:
  enable_chart: true
```

## Usage

Simply run the tool using `uv`. It will automatically read `tdc.yaml` from the current directory.

```bash
uv run tdc
```

To specify a different configuration file:

```bash
uv run tdc --config custom_config.yaml
```

## Output

Depending on your YAML configuration, the tool will output the following in the `output_dir` (default: `./output`):
- `[TICKER]_features.csv`: A tabular dataset containing the OHLC values, the 20-bin density vector, Point of Control (POC), Value Area (VA), skew, and kurtosis.
- `[TICKER]_chart.html`: An interactive Plotly chart.
- `[TICKER]_chart.png`: A static image render of the chart.

## Developer Documentation

If you wish to contribute to the codebase, please see the [Developer Guide](docs/developer_guide.md) or the [Project Plan](docs/TDC_project_plan.md).
