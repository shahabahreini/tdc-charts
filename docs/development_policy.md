# Python Project Development Policy

## Table of Contents

1. [Purpose](#purpose)
2. [Repository Structure](#repository-structure)
3. [Package Management (uv)](#package-management-uv)
4. [Configuration Management (YAML)](#configuration-management-yaml)
5. [Logging & Error Handling](#logging--error-handling)
6. [Terminal Output (rich)](#terminal-output-rich)
7. [Visualization (plotly + scientific libs)](#visualization-plotly--scientific-libs)
8. [Interactive TUI (blessed)](#interactive-tui-blessed)
9. [Feature Toggling](#feature-toggling)
10. [Documentation Standards](#documentation-standards)
11. [Code Quality Checklist](#code-quality-checklist)
12. [Versioning and CI](#versioning-and-ci)

## Purpose

Generic, project-agnostic policy for building maintainable, scalable, and modular Python repositories. Applies to any project (data pipelines, ML training, CLI tools, APIs, etc.).

## Repository Structure

Use a `src/` layout with clear separation of concerns:

```
project_name/
├── pyproject.toml
├── uv.lock
├── README.md
├── configs/
│   └── config.yaml
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── core/
│       ├── io/
│       ├── utils/
│       │   ├── logger.py
│       │   └── config_loader.py
│       └── cli.py
├── tests/
├── docs/
│   ├── developer_guide.md
│   └── user_guide.md
└── .gitignore
```

- One responsibility per module; avoid god-files.
- No hardcoded values in source code — everything configurable lives in YAML.
- Business logic separated from I/O, CLI, and presentation layers.

## Package Management (uv)

- Use `uv` exclusively for environment and dependency management.
- Initialize with `uv init`; declare dependencies in `pyproject.toml`.
- Lock dependencies with `uv lock` and commit `uv.lock` for reproducibility.
- Run scripts via `uv run` instead of activating venvs manually.
- Separate `dependencies` and `dev-dependencies` (lint, test, type-check).

## Configuration Management (YAML)

- All parameters, thresholds, paths, credentials references, and feature flags must live in a single structured `config.yaml` (or split by domain, e.g. `configs/model.yaml`).
- Load config once at startup through a dedicated `config_loader.py` module.
- Validate schema (e.g. with `pydantic` or `dataclasses`) to fail fast on bad configs.
- Never duplicate config values inside code; always reference the loaded object.
- Group config keys logically (e.g. `data`, `model`, `logging`, `features`).

## Logging & Error Handling

- Every function must have:
  - Type hints for all parameters and return values.
  - A docstring describing purpose, args, and returns.
  - Try/except blocks around I/O, network, or external-API calls with specific exceptions caught.
  - Logging at entry/exit for critical operations (debug level) and errors (error level).
- Use Python's `logging` module configured centrally; never use bare `print()`.
- Log levels must be configurable via YAML (e.g. `logging.level: INFO`).
- Raise custom exceptions for domain-specific failures instead of generic `Exception`.

### Edge Case Coverage

- Every function must handle, at minimum:
  - Empty, `None`, or missing input (e.g. empty API response, missing config key).
  - Wrong type or malformed data (e.g. non-numeric price, corrupted YAML field).
  - Boundary values (zero, negative, max/min limits, empty date ranges).
  - External failures: network timeout, rate limiting, API downtime, invalid symbol/ticker.
  - Duplicate, out-of-order, or partially missing time-series data.
- Edge cases must be covered by dedicated unit tests, not just handled inline.

### Meaningful Error Messages

- Error messages must state: what failed, why, and (when possible) how to fix it.
- Include the relevant identifier in the message (e.g. ticker symbol, config key, file path).
- Avoid vague messages like `"Error occurred"` or raw stack traces shown to end users.
- Example: `"Failed to fetch data for ticker 'AAPL': API returned 429 (rate limit). Retry after 60s."`
- User-facing errors (CLI/rich output) must be short and actionable; full technical detail goes to the log file only.

## Terminal Output (rich)

- Use `rich` for all terminal output: tables, progress bars, panels, and tracebacks.
- Combine `rich.logging.RichHandler` with the standard logging module for colored, leveled console logs.
- Enable `rich_tracebacks=True` for clearer error diagnostics during development.

## Visualization (plotly + scientific libs)

- Use `plotly` for all interactive plots (candlestick charts, zoomable time series, dashboards exported to HTML) — default choice for any user-facing visualization.
- Where `plotly` is limited (e.g. complex statistical plots, publication-quality static figures, 3D scientific surfaces, signal-processing visuals), use appropriate scientific libraries instead:
  - `matplotlib` — static, publication-ready figures and fine-grained layout control.
  - `seaborn` — statistical plots (distributions, correlation heatmaps, regression plots).
  - `scipy` / `statsmodels` — companion analysis feeding into any of the above (e.g. trend fits, smoothing, FFT) rather than plotting itself.
- Chart type selection must be config-driven (YAML flag, e.g. `plots.engine: plotly|matplotlib`), not hardcoded, so users can switch rendering backends without code changes.
- All generated charts must be saved as artifacts (HTML for plotly, PNG/SVG for static libs) in a dedicated `output/` or `plots/` directory.

## Interactive TUI (blessed)

- Use `blessed` for any interactive, full-screen, or keyboard-driven Terminal User Interface (menus, live dashboards, toggling features at runtime).
- Keep `rich` for static/streamed console output (logs, tables, reports) and `blessed` for interactive screens (cursor control, keypress handling, live re-rendering) — do not mix their screen-control logic in the same render loop.
- Wrap keyboard input handling in `term.cbreak()` / `term.hidden_cursor()` context managers to ensure the terminal state is restored on exit or error.
- Any TUI screen must degrade gracefully (fallback to plain CLI output) when run in a non-interactive environment (e.g. CI, piped output, SSH without a TTY).

## Feature Toggling

- Every optional or experimental feature must have an `enabled: true/false` flag in YAML.
- Code must check flags at runtime, not via commented-out code or hardcoded booleans.
- Toggling a feature must not require a code change or redeploy — only a config edit.

## Documentation Standards

- Maintain two documents minimum:
  - `docs/developer_guide.md`: architecture, module responsibilities, setup, contribution rules.
  - `docs/user_guide.md`: installation, configuration reference, usage examples.
- Both must open with a Table of Contents.
- Writing style: clear, brief, no filler or overstated claims — one idea per sentence.
- Every config key must be documented with type, default, and purpose.
- `README.md` is the entry point: project summary, quick start, links to detailed docs.

## Code Quality Checklist

- Modular: one class/function does one thing.
- Scalable: new features added via new modules + config keys, not by editing core logic.
- Testable: core logic decoupled from I/O for unit testing.
- Reproducible: pinned dependencies via `uv.lock`, deterministic config-driven behavior.
- Observable: structured logs, rich console output, meaningful error messages.
- Clean: `uv run ruff check .` and `uv run pytest` pass before release.

## Versioning and CI

- Version bumps must work through `uv run bump patch`, `uv run bump minor`, and
  `uv run bump major`.
- GitHub Actions must run Ruff for changes targeting `main`.
- Tags like `v1.0.0` must build a wheel and attach it to a GitHub Release only
  when the tagged commit is reachable from `main`.
