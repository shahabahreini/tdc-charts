# TDC Developer Guide

## Table of Contents

1. [Architecture](#architecture)
2. [Module Layout](#module-layout)
3. [Feature Pipeline](#feature-pipeline)
4. [Validation Rules](#validation-rules)
5. [Rendering Rules](#rendering-rules)
6. [Quality Checks](#quality-checks)
7. [Release Workflow](#release-workflow)

## Architecture

TDC uses a `src/` package layout. The feature pipeline is intentionally separate
from rendering so exported tables and charts share the same definitions.

- `config.py` validates YAML with Pydantic models.
- `data.py` fetches and cleans parent OHLCV bars.
- `intrabar.py` loads and maps real intrabar CSV/Parquet rows.
- `simulate.py` creates OHLC-constrained synthetic bridge paths.
- `density.py` computes density, POC, Value Area, and profile shape metrics.
- `features.py` builds export-ready feature frames.
- `render.py` builds Plotly charts from feature frames.
- `export.py` writes feature artifacts.
- `main.py` orchestrates CLI execution.
- `versioning.py` provides `uv run bump patch|minor|major`.

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
    ├── features.py
    ├── intrabar.py
    ├── logger.py
    ├── main.py
    ├── render.py
    ├── simulate.py
    └── versioning.py
```

## Feature Pipeline

`build_feature_frame` is the single source of truth for exported indicators.
It validates each OHLC row, obtains either synthetic or real intrabar arrays,
computes the density profile, adds POC/Value Area statistics, then appends
drift, gap, confidence, and indecision fields.

Rendering should consume existing fields such as `indecision_flag`,
`poc_is_ambiguous`, and `session_gap`. It should not redefine those indicators.

## Validation Rules

Density inputs fail fast when:

- OHLC values are non-finite or internally inconsistent.
- Ticks are empty, non-finite, or outside the parent low/high range.
- Volume weights are non-finite, negative, or a different length than ticks.
- Density arrays or bins are malformed.

Flat bars are valid. Their POC and Value Area remain exactly at the flat price
instead of using artificial price extensions.

## Rendering Rules

The renderer hides POC and Value Area overlays that fall outside the visible
heatmap range when `align_overlays_to_visible_heatmap` is enabled. POC drift
breaks across ambiguous POC points, hidden POCs, and session gaps.

Session gaps are visual markers derived from exported `session_gap` values.

## Quality Checks

Run these before committing:

```bash
uv run ruff check .
uv run pytest
uv build
```

Tests cover config compatibility, simulation validation, density invariants,
real intrabar mapping, feature exports, rendering overlays, and export behavior.

## Release Workflow

Use the bump command:

```bash
uv run bump patch
uv run bump minor
uv run bump major
```

Ruff runs in GitHub Actions for changes targeting `main`. Tags matching
`v*.*.*` build a wheel and publish a GitHub Release when the tagged commit is
reachable from `main`.
