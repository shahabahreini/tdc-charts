# TimeDensityCandle (TDC)

[![Python Support](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Testing: Pytest](https://img.shields.io/badge/tests-Pytest-green.svg)](https://pytest.org/)

TimeDensityCandle (TDC) builds candlestick charts and feature tables with a
price-density profile inside each OHLC bar. The profile can come from real
intrabar prices or from an OHLC-constrained synthetic estimate when intrabar
data is unavailable.

TDC is intended for visual review, research, and feature extraction. Synthetic
profiles are estimates and are exported with confidence metadata and warnings.

![TimeDensityCandle Chart Preview](assets/chart_preview.png)

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Outputs](#outputs)
6. [Accuracy and Confidence](#accuracy-and-confidence)
7. [Development](#development)
8. [Release](#release)
9. [License](#license)

## Features

- Density heatmaps inside candle bodies or across the full high/low range.
- POC marker and POC drift line with tie/ambiguity handling.
- Value Area based on the smallest contiguous density range.
- Real intrabar CSV/Parquet mode using `bar_id` or timestamp windows.
- Synthetic OHLC bridge mode with optional ensemble sampling.
- Exported confidence, warnings, entropy, HHI, drift, gap, and indecision fields.
- Session-gap markers and drift breaks for discontinuous charts.
- CSV and Parquet feature export.

## Installation

```bash
git clone https://github.com/shahabahreini/tdc-charts.git
cd tdc-charts
uv sync --dev
```

## Quick Start

Run with the repository configuration:

```bash
uv run tdc
```

Use a different config file:

```bash
uv run tdc --config custom_config.yaml
```

If `algorithm.mode` is `real`, set `data.intrabar_path` to a CSV or Parquet
file. If you only have Yahoo Finance OHLCV bars, set `algorithm.mode` to
`synthetic`.

## Configuration

The app reads `tdc.yaml` by default.

| Key | Purpose |
|---|---|
| `data.ticker` | Yahoo Finance ticker for parent OHLCV bars. |
| `data.interval` / `data.period` | Yahoo Finance interval and lookback. |
| `data.session_timezone` | Market/session timezone used for documentation and gap context. |
| `data.intrabar_path` | Real intrabar CSV/Parquet file for `mode: real`. |
| `data.intrabar_*_col` | Column names for timestamp, price, volume, and parent `bar_id`. |
| `algorithm.mode` | `synthetic` or `real`. |
| `algorithm.nbins` | Number of density price bins per bar. |
| `algorithm.synthetic_tick_count` | Synthetic ticks per ensemble member. |
| `algorithm.synthetic_ensemble_size` | Number of synthetic paths per bar. |
| `algorithm.value_area_ratio` | Density mass target for Value Area, default `0.68`. |
| `algorithm.poc_tie_policy` | `first`, `midpoint`, `centroid`, or `ambiguous`. |
| `features.indecision_quantile` | Fraction of high indecision-score bars to flag. |
| `features.indecision_min_samples` | Minimum chart rows before automatic flags are emitted. |
| `rendering.full_heatmap` | Draw density over the full low/high range. |
| `rendering.extend_to_tails` | Draw narrow density blocks on wicks/tails. |
| `rendering.align_overlays_to_visible_heatmap` | Hide POC/VA overlays outside the rendered density range. |
| `rendering.show_session_gaps` | Add visual markers for detected time gaps. |
| `rendering.break_poc_drift_on_gaps` | Break drift lines across gaps or ambiguous POCs. |

## Outputs

Feature exports include:

- OHLC and timestamp fields.
- `density_00 ... density_nn`.
- POC fields: `poc_price`, `poc_bin_index`, `poc_tie_count`,
  `poc_mass_share`, `poc_confidence`, `poc_is_ambiguous`.
- Value Area fields: `value_area_low`, `value_area_high`,
  `value_area_width_pct`, `value_area_confidence`, `value_area_is_ambiguous`.
- Shape fields: `skew`, `kurtosis`, `profile_entropy`, `profile_hhi`,
  `concentration_ratio`.
- Drift/gap fields: `poc_delta`, `poc_delta_pct`, `poc_delta_atr`,
  `poc_slope_3`, `gap_from_prev_close`, `session_gap`.
- Confidence fields: `profile_source`, `volume_mode`, `profile_confidence`,
  `confidence_level`, `profile_warning`.
- Indecision fields: `indecision_score`, `indecision_threshold`,
  `indecision_flag`, `indecision_reason`.

## Accuracy and Confidence

Real mode uses the provided intrabar prices and optional trade/subbar volume.
Synthetic mode uses OHLC-constrained bridge paths. Synthetic output is useful
for visualization and research, but it is not evidence of true liquidity or
executed volume distribution.

TDC therefore exports confidence and warning fields. Low-confidence cases
include synthetic-only profiles, tied POCs, ambiguous Value Areas, degenerate
bars, low sample counts, and hidden overlay regions.

## Development

```bash
uv run ruff check .
uv run pytest
uv build
```

Bump versions with:

```bash
uv run bump patch
uv run bump minor
uv run bump major
```

## Release

Ruff runs on pushes and pull requests targeting `main`. Pushing a tag such as
`v1.0.0` on a commit reachable from `main` builds a wheel and attaches it to a
GitHub Release.

## License

MIT. See [LICENSE.md](LICENSE.md).
