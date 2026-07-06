# TDC Developer Guide

Welcome to the TimeDensityCandle (TDC) developer guide! This document outlines the architecture, module layout, and error-handling strategies.

## Table of Contents
1. [Architecture](#architecture)
2. [Module Layout](#module-layout)
3. [Error Handling](#error-handling)
4. [Adding Features](#adding-features)

## Architecture

TDC is designed to be highly modular and configuration-driven.
- **Config**: Pydantic strictly validates all parameters from `tdc.yaml`.
- **Data**: Uses `yfinance` to fetch OHLCV data. Retries are handled via `tenacity`.
- **Simulation**: Uses a Brownian bridge constrained by O/H/L/C to simulate ticks when intraday data is not available.
- **Density**: Uses `numpy` histograms to compute the density profile and `scipy.stats` for distribution moments.
- **Rendering**: Generates Plotly shapes dynamically based on the density matrix.

## Module Layout

```text
tdc-charts/
├── pyproject.toml         # Managed by uv
├── tdc.yaml               # Runtime configuration
└── src/tdc/
    ├── __init__.py
    ├── main.py            # CLI entry and orchestration pipeline
    ├── config.py          # Pydantic models for configuration
    ├── logger.py          # Rich terminal logging
    ├── exceptions.py      # Custom exception hierarchy
    ├── data.py            # yfinance fetching logic
    ├── simulate.py        # Tick simulation algorithm
    ├── density.py         # Profile extraction
    ├── render.py          # Plotly drawing
    └── export.py          # CSV export
```

## Error Handling

We use a custom exception hierarchy defined in `src/tdc/exceptions.py`. 
- Always raise a specific exception (e.g. `DataFetchError`) rather than a generic `ValueError`.
- The `logger.py` module installs `rich.traceback` globally (`show_locals=True`). This means unhandled exceptions will print a beautiful terminal trace that includes the state of local variables at every frame, making debugging effortless.
- Ensure all modules log their progress via `logger.info()` or `logger.debug()`.

## Adding Features

To add a new feature:
1. Update `tdc.yaml` and the corresponding Pydantic models in `config.py`.
2. Implement the logic in the appropriate module (e.g. `density.py`).
3. Update `main.py` if orchestration needs to change.
