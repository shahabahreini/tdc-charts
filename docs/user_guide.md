# TDC User Guide

## Table of Contents

1. [Install](#install)
2. [Run](#run)
3. [Modes](#modes)
4. [Configuration Reference](#configuration-reference)
5. [Chart Features](#chart-features)
6. [Exports](#exports)
7. [Current Limits](#current-limits)

## Install

```bash
uv sync --dev
```

## Run

```bash
uv run tdc
uv run tdc --config tdc.yaml
```

## Modes

`algorithm.mode: synthetic` builds an OHLC-constrained bridge estimate for each
bar. It is useful when only OHLCV data is available, but it is not real
time-at-price evidence.

`algorithm.mode: real` loads intrabar CSV or Parquet data from
`data.intrabar_path`. If the file has a `bar_id` column, TDC maps intrabar rows
by parent bar index. Otherwise, it maps rows by timestamp windows between
parent bars.

Required real-mode columns:

| Column | Default config key | Purpose |
|---|---|---|
| `price` | `data.intrabar_price_col` | Intrabar trade, mid, or subbar price. |
| `timestamp` | `data.intrabar_timestamp_col` | Used when `bar_id` is unavailable. |
| `volume` | `data.intrabar_volume_col` | Optional real volume weights. |
| `bar_id` | `data.intrabar_bar_id_col` | Optional parent bar mapping. |

## Configuration Reference

| Key | Type | Default | Purpose |
|---|---:|---|---|
| `app.debug` | bool | `false` | Enables debug logging. |
| `app.output_dir` | string | `./output` | Directory for charts and feature files. |
| `app.log_level` | string | `INFO` | Console log level. |
| `data.ticker` | string | `AAPL` | Yahoo Finance ticker. |
| `data.interval` | string | `1d` | Yahoo Finance interval. |
| `data.period` | string | `1mo` | Yahoo Finance lookback period. |
| `data.session_timezone` | string | `America/New_York` | Market/session timezone context. |
| `data.intrabar_path` | string/null | `null` | CSV/Parquet source for real mode. |
| `algorithm.mode` | string | `synthetic` | `synthetic` or `real`. |
| `algorithm.nbins` | int | `20` | Number of density bins. |
| `algorithm.volatility_factor` | float | `0.03` | Synthetic bridge noise scale. |
| `algorithm.enable_volume_weighting` | bool | `false` | Uses weights when meaningful volume exists. |
| `algorithm.synthetic_tick_count` | int | `100` | Synthetic ticks per path. |
| `algorithm.synthetic_ensemble_size` | int | `1` | Synthetic paths per bar. |
| `algorithm.random_seed` | int/null | `null` | Base seed for repeatable synthetic output. |
| `algorithm.value_area_ratio` | float | `0.68` | Target density mass for Value Area. |
| `algorithm.poc_tie_policy` | string | `midpoint` | POC tie behavior. |
| `features.export_csv` | bool | `true` | Legacy CSV export switch. |
| `features.export_formats` | list | `["csv"]` | Supports `csv` and `parquet`. |
| `features.enable_poc_marker` | bool | `true` | Shows POC tick markers. |
| `features.enable_poc_drift_line` | bool | `true` | Shows POC drift line. |
| `features.enable_value_area` | bool | `true` | Shows Value Area boxes. |
| `features.enable_indecision_flags` | bool | `true` | Shows indecision markers. |
| `features.indecision_quantile` | float | `0.25` | Top fraction of indecision scores to flag. |
| `features.indecision_min_samples` | int | `20` | Minimum rows needed for automatic flags. |
| `rendering.enable_chart` | bool | `true` | Enables chart generation. |
| `rendering.full_heatmap` | bool | `false` | Shows heatmap over full high/low range. |
| `rendering.extend_to_tails` | bool | `false` | Shows narrow density blocks on wicks. |
| `rendering.align_overlays_to_visible_heatmap` | bool | `true` | Hides overlays outside rendered density. |
| `rendering.show_session_gaps` | bool | `true` | Shows detected time-gap markers. |
| `rendering.break_poc_drift_on_gaps` | bool | `true` | Breaks drift through gaps/ambiguous POCs. |
| `rendering.legend.enabled` | bool | `true` | Shows the chart legend. |
| `rendering.legend.position` | string | `top_right` | Legend placement. |

## Chart Features

POC markers show the highest-density price level per candle. Tied profiles are
marked in exported fields and can break the drift line.

Value Area boxes show the smallest contiguous bin range containing the
configured density mass.

Indecision flags come from exported `indecision_flag` values when available.
For manually supplied feature tables, rendering falls back to concentration
ratio only when the window is large enough and not all ratios are equal.

Session gaps are detected from timestamp spacing and shown as dashed vertical
markers. POC drift can break across those gaps.

## Exports

Feature tables include OHLC values, density bins, POC/Value Area fields,
shape metrics, drift metrics, gap metrics, confidence fields, warnings, and
indecision fields.

Important confidence columns:

- `profile_source`: `real` or `synthetic`.
- `volume_mode`: `real`, `synthetic_even`, or `none`.
- `profile_confidence`: numeric score from `0` to `1`.
- `confidence_level`: `low`, `medium`, or `high`.
- `profile_warning`: semicolon-separated warnings.

## Current Limits

Synthetic mode remains an estimate. It uses OHLC-anchored bridge paths and can
use ensembles, but it cannot reconstruct real order flow or true intrabar
liquidity.

Real mode depends on the quality of the supplied intrabar file. Prices outside
the parent OHLC range, invalid weights, and missing intrabar rows fail fast
instead of silently producing misleading profiles.
