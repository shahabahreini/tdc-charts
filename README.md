# TimeDensityCandle (TDC)

TimeDensityCandle (TDC) converts OHLCV bars into candles whose bodies show time-at-price density. It fetches Yahoo Finance data, creates synthetic intrabar paths, computes density features, exports feature tables, and renders Plotly charts.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Plot Features](#plot-features)
5. [Outputs](#outputs)
6. [Development](#development)
7. [Release Process](#release-process)

## Installation

```bash
git clone https://github.com/shahabahreini/tdc-charts.git
cd tdc-charts
uv sync --dev
```

## Quick Start

```bash
uv run tdc
```

Use a custom config file:

```bash
uv run tdc --config custom_config.yaml
```

## Configuration

TDC reads `tdc.yaml` by default. The main keys are:

| Key | Type | Default | Purpose |
|---|---:|---|---|
| `app.debug` | bool | `false` | Enables debug logging. |
| `app.output_dir` | string | `./output` | Directory for generated files. |
| `app.log_level` | string | `INFO` | Console log level. |
| `data.ticker` | string | `AAPL` | Yahoo Finance ticker. |
| `data.interval` | string | `1d` | Yahoo Finance interval. |
| `data.period` | string | `1mo` | Yahoo Finance period. |
| `algorithm.mode` | string | `synthetic` | `synthetic` is supported. `real` fails fast until intrabar input support is added. |
| `algorithm.nbins` | int | `20` | Density bin count. |
| `algorithm.volatility_factor` | float | `0.03` | Synthetic path noise scale. |
| `algorithm.synthetic_tick_count` | int | `100` | Tick count per synthetic candle. |
| `algorithm.random_seed` | int/null | `42` | Base seed for deterministic synthetic paths. |
| `algorithm.enable_volume_weighting` | bool | `false` | Uses available bar volume as synthetic per-tick weights. |
| `features.export_formats` | list | `["csv"]` | Feature export formats: `csv`, `parquet`. |
| `features.enable_poc_marker` | bool | `true` | Shows gold POC tick per candle. |
| `features.enable_poc_drift_line` | bool | `true` | Shows dashed gold POC drift line. |
| `features.enable_value_area` | bool | `true` | Shows dotted blue Value Area boxes. |
| `features.enable_indecision_flags` | bool | `true` | Shows purple indecision triangles. |
| `features.indecision_quantile` | float | `0.25` | Flags candles at or below this concentration-ratio quantile. |
| `rendering.legend.enabled` | bool | `true` | Shows or hides the Plotly legend. |
| `rendering.legend.position` | string | `top_right` | Legend position. |

## Plot Features

- POC marker: gold horizontal tick at the highest-density price level for each candle.
- POC drift: dashed gold line connecting POC prices across bars.
- Value Area: dotted blue rectangle around the contiguous density zone containing about 68% of mass.
- Indecision flags: purple triangle markers above candles with bottom-quartile `concentration_ratio`.
- Legend: controlled by `rendering.legend.enabled`.

## Outputs

Files are written to `app.output_dir`:

- `[TICKER]_features.csv`
- `[TICKER]_features.parquet` when enabled
- `[TICKER]_chart.html`
- `[TICKER]_chart.png`

## Development

```bash
uv run ruff check .
uv run pytest
uv build
```

Bump the package version:

```bash
uv version --bump patch
uv version --bump minor
uv version --bump major
```

## Release Process

Ruff runs in GitHub Actions for pushes and pull requests targeting `main`. Pushing a tag like `v1.0.0` from `main` builds a wheel and attaches it to a GitHub Release.

See [docs/user_guide.md](docs/user_guide.md), [docs/developer_guide.md](docs/developer_guide.md), and [docs/TDC_project_plan.md](docs/TDC_project_plan.md) for more detail.
