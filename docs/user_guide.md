# TDC User Guide

## Table of Contents

1. [Install](#install)
2. [Run](#run)
3. [Configuration Reference](#configuration-reference)
4. [Chart Features](#chart-features)
5. [Outputs](#outputs)
6. [Current Limits](#current-limits)

## Install

```bash
uv sync --dev
```

## Run

```bash
uv run tdc
uv run tdc --config tdc.yaml
```

## Configuration Reference

| Key | Type | Default | Purpose |
|---|---:|---|---|
| `app.debug` | bool | `false` | Enables debug logging. |
| `app.output_dir` | string | `./output` | Directory for charts and feature files. |
| `app.log_level` | string | `INFO` | Console log level. |
| `data.ticker` | string | `AAPL` | Yahoo Finance ticker. |
| `data.interval` | string | `1d` | Yahoo Finance interval. |
| `data.period` | string | `1mo` | Yahoo Finance lookback period. |
| `algorithm.mode` | string | `synthetic` | Uses synthetic intrabar ticks. |
| `algorithm.nbins` | int | `20` | Number of density bins. |
| `algorithm.volatility_factor` | float | `0.03` | Synthetic random-walk volatility scale. |
| `algorithm.enable_volume_weighting` | bool | `false` | Applies available bar volume as even synthetic tick weights. |
| `algorithm.synthetic_tick_count` | int | `100` | Synthetic ticks per bar. |
| `algorithm.random_seed` | int/null | `42` | Base seed for repeatable output. |
| `features.export_csv` | bool | `true` | Legacy CSV export switch. |
| `features.export_formats` | list | `["csv"]` | Export formats. Supports `csv` and `parquet`. |
| `features.enable_poc_marker` | bool | `true` | Shows POC tick markers. |
| `features.enable_poc_drift_line` | bool | `true` | Shows POC drift line. |
| `features.enable_value_area` | bool | `true` | Shows Value Area boxes. |
| `features.enable_indecision_flags` | bool | `true` | Shows indecision markers. |
| `features.indecision_quantile` | float | `0.25` | Bottom quantile for indecision flags. |
| `rendering.enable_chart` | bool | `true` | Enables chart generation. |
| `rendering.color_scheme.bull` | string | `rgba(38, 166, 154, {alpha})` | Bull candle density color template. |
| `rendering.color_scheme.bear` | string | `rgba(239, 83, 80, {alpha})` | Bear candle density color template. |
| `rendering.overlay_style.poc_color` | string | `gold` | POC marker and drift color. |
| `rendering.overlay_style.poc_width` | int | `3` | POC marker width. |
| `rendering.overlay_style.poc_drift_dash` | string | `dash` | POC drift dash style. |
| `rendering.overlay_style.value_area_color` | string | `deepskyblue` | Value Area border color. |
| `rendering.overlay_style.value_area_fill` | string | `rgba(0, 191, 255, 0.08)` | Value Area fill color. |
| `rendering.overlay_style.value_area_dash` | string | `dot` | Value Area border dash. |
| `rendering.overlay_style.indecision_color` | string | `purple` | Indecision marker color. |
| `rendering.overlay_style.indecision_size` | int | `11` | Indecision marker size. |
| `rendering.overlay_style.candle_half_width` | float | `0.4` | Candle half-width on the x-axis. |
| `rendering.full_heatmap` | bool | `false` | Shows heatmap over full high/low range instead of just candle body. |
| `rendering.legend.enabled` | bool | `true` | Shows the chart legend. |
| `rendering.legend.position` | string | `top_right` | Legend placement. |

## Chart Features

POC markers show the highest-density price level per candle. The POC drift line connects those levels across bars.

Value Area boxes show the smallest contiguous bin range that contains about 68% of the candle density mass.

Indecision flags mark candles whose `concentration_ratio` is at or below the configured quantile.

## Outputs

Feature tables include OHLC values, density bins, POC, Value Area, skew, kurtosis, and concentration ratio.

Charts are exported as HTML and PNG when chart rendering is enabled.

## Current Limits

`algorithm.mode: real` is reserved for future intrabar input support and currently fails fast with a clear error. Volume weighting uses available bar volume as even synthetic tick weights until real tick or sub-bar volume is supported.
