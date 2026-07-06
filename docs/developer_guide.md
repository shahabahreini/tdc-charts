# TDC Developer Guide

## Table of Contents

1. [Architecture](#architecture)
2. [Module Layout](#module-layout)
3. [Configuration Flow](#configuration-flow)
4. [Chart Rendering](#chart-rendering)
5. [Quality Checks](#quality-checks)
6. [Release Workflow](#release-workflow)

## Architecture

TDC uses a `src/` package layout and keeps the pipeline split by responsibility.

- `config.py` validates YAML with Pydantic models.
- `data.py` fetches Yahoo Finance OHLCV data and normalizes columns.
- `simulate.py` creates constrained synthetic intrabar paths.
- `density.py` computes normalized density vectors and profile statistics.
- `render.py` builds Plotly charts and feature overlays.
- `export.py` writes feature artifacts.
- `main.py` orchestrates CLI execution.

## Module Layout

```text
tdc-charts/
├── pyproject.toml
├── uv.lock
├── tdc.yaml
├── docs/
├── tests/
└── src/tdc/
    ├── config.py
    ├── data.py
    ├── density.py
    ├── exceptions.py
    ├── export.py
    ├── logger.py
    ├── main.py
    ├── render.py
    └── simulate.py
```

## Configuration Flow

The CLI loads `tdc.yaml` once at startup, validates it with Pydantic, then applies the configured logging level. Runtime behavior should be driven through config keys instead of hardcoded values.

Legacy feature keys are still accepted:

- `enable_poc_overlay` maps to POC marker and POC drift toggles.
- `concentration_ratio_flagging` maps to indecision flags.

## Chart Rendering

The chart uses Plotly shapes for candle bodies, wicks, POC ticks, and Value Area boxes. It uses Plotly traces for legend entries, POC drift, and indecision markers.

Overlay behavior:

- POC marker: gold horizontal line per candle.
- POC drift: dashed gold line through POC prices.
- Value Area: dotted blue rectangle around the contiguous 68% density zone.
- Indecision: purple triangle above candles in the bottom concentration-ratio quantile.

## Quality Checks

Run these before committing:

```bash
uv run ruff check .
uv run pytest
uv build
```

Tests cover config compatibility, simulation validation, density math, rendering overlays, and export behavior.

## Release Workflow

Use uv to bump versions:

```bash
uv version --bump patch
uv version --bump minor
uv version --bump major
```

Ruff runs in GitHub Actions for changes targeting `main`. Tags matching `v*.*.*` build a wheel and publish a GitHub Release when the tagged commit is on `main`.
