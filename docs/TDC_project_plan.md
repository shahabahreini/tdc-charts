# TimeDensityCandle (TDC) — Technical Project Plan

## 1. Purpose

**Project name: TimeDensityCandle (TDC)**

Build a Python library/script that transforms OHLC(V) bar data into **TimeDensityCandles (TDC)**: conventional candlesticks (wick + body defined by open/high/low/close) where the body is filled with a horizontal density gradient representing **time-at-price concentration** within the bar. Output must be usable both as a visualization (Plotly PNG) and as structured numeric features for ML model training (e.g., CV/YOLO pipelines, tabular regression/classification).

---

## 2. Scope

| In Scope | Out of Scope |
|---|---|
| Synthetic tick simulation (Brownian-bridge, constrained to O/H/L/C) | Live/real-time streaming data |
| Real intrabar (tick or 1-min) resampling into higher-timeframe candles | Order-flow/bid-ask imbalance modeling |
| Static Plotly chart rendering (single + multi-candle) | Interactive/animated charts |
| Structured feature export (CSV/Parquet) | Broker/exchange execution integration |

---

## 3. Data Model

### 3.1 Input Schema

**Bar-level OHLCV** (required):

| Column | Type | Description |
|---|---|---|
| `timestamp` | datetime | Bar open time |
| `open`, `high`, `low`, `close` | float | Standard OHLC |
| `volume` | float (optional) | Used for volume-weighted density if available |

**Intrabar data** (optional, for `mode='real'`):

| Column | Type | Description |
|---|---|---|
| `timestamp` | datetime | Tick or sub-bar timestamp |
| `price` | float | Trade/mid price |
| `volume` | float (optional) | Trade size, for volume weighting |
| `bar_id` | int | Foreign key mapping tick to parent bar |

### 3.2 Output Schema (per candle, for ML consumption)

| Field | Type | Description |
|---|---|---|
| `open, high, low, close` | float | Standard OHLC |
| `density_00 ... density_(n-1)` | float [0,1] | Normalized time-at-price per bin |
| `poc_price` | float | Price of max density (Point of Control) |
| `value_area_low, value_area_high` | float | Bounds containing ~68% of density mass |
| `skew, kurtosis` | float | Shape of intrabar price distribution |
| `concentration_ratio` | float | max(density) / mean(density); indecision indicator |

---

## 4. Algorithm Specification

### 4.1 Tick Series Generation

```
FUNCTION simulate_intrabar_ticks(open, high, low, close, n_ticks, seed) -> ndarray
    - Initialize path[0] = open
    - For step in 1..n_ticks-2:
        path[step] = clip(path[step-1] + Normal(0, sigma), low, high)
        where sigma = (high - low) * volatility_factor (default 0.025-0.03)
    - path[-1] = close
    - RETURN path
```

Used only when `mode='synthetic'`. When `mode='real'`, tick series is the actual intrabar price array filtered by `bar_id`.

### 4.2 Density Profile Computation

```
FUNCTION compute_density_profile(ticks, low, high, nbins) -> ndarray
    - bins = linspace(low, high, nbins+1)
    - counts = histogram(ticks, bins)
    - IF volume weights available: counts = weighted histogram
    - density = counts / max(counts)
    - RETURN density, bins
```

### 4.3 Profile Statistics

```
FUNCTION compute_profile_stats(ticks, density, bins) -> dict
    - poc_price = bin_center[argmax(density)]
    - skew, kurtosis = scipy.stats.skew/kurtosis(ticks)
    - value_area = smallest contiguous bin range containing 68% of total density mass
    - concentration_ratio = max(density) / mean(density)
    - RETURN {poc_price, skew, kurtosis, value_area_low, value_area_high, concentration_ratio}
```

### 4.4 Rendering

```
FUNCTION render_heatmap_candle(fig, x_position, ohlc, density, bins, half_width, color_scheme):
    - Draw wick: vertical line from low to high at x_position
    - Draw body outline: rectangle bounded by open/close
    - FOR each bin j:
        alpha_j = base_alpha + (1 - base_alpha) * density[j]
        color_j = color_scheme.bull if close >= open else color_scheme.bear, with alpha_j
        Draw filled rectangle [x_position - half_width, x_position + half_width] x [bins[j], bins[j+1]]
    - Overlay POC marker at poc_price (optional, thin horizontal tick)
```

### 4.5 Orchestration

```
FUNCTION build_heatmap_chart(df, intrabar_data=None, nbins=20, mode='synthetic') -> (Figure, DataFrame)
    - FOR each bar i in df:
        ticks = simulate_intrabar_ticks(...) OR real intrabar slice
        density, bins = compute_density_profile(ticks, low_i, high_i, nbins)
        stats = compute_profile_stats(ticks, density, bins)
        render_heatmap_candle(fig, i, ohlc_i, density, bins, half_width, color_scheme)
        append row to feature_df: ohlc_i + density + stats
    - RETURN fig, feature_df
```

---

## 5. Expected Visual Output

- At a glance, the chart resembles a standard candlestick chart (wick + rectangular body, green/red by direction).
- Unlike standard candles, the body is **not** a flat color: it contains horizontal bands whose color intensity increases with time-at-price density.
- The densest band (POC) should be the visually darkest/most saturated strip within each body.
- Across multiple candles, the chart should read left-to-right as a normal time series with **no overlap** between adjacent candle bodies/wicks.
- No visual clutter: axis labels legible, consistent color scale (bull vs. bear), consistent bin width across all candles in the chart.

---

## 6. Validation Checklist

- [ ] Wick spans exactly `[low, high]` with no gaps or truncation.
- [ ] Body rectangle correctly bounded by `min(open,close)` to `max(open,close)`.
- [ ] `density` bins sum to a coherent profile; no values outside `[low, high]`.
- [ ] Color alpha is monotonically increasing with density.
- [ ] No overlapping shapes between consecutive candles (`half_width < spacing/2`).
- [ ] `density_vector` has identical length (`nbins`) for every row, no NaNs.
- [ ] `poc_price` falls within `[low, high]` for every bar.
- [ ] Feature export round-trips correctly (reload CSV/Parquet, shapes match).

---

## 7. Module Layout

```
tdc/
├── simulate.py       # simulate_intrabar_ticks
├── density.py        # compute_density_profile, compute_profile_stats
├── render.py          # render_heatmap_candle, build_heatmap_chart
├── export.py          # feature_df -> CSV/Parquet
└── config.py          # color schemes, default nbins, volatility_factor
```

---

## 8. Future Feature Suggestions

- **Point of Control (POC) overlay**: explicit marker per candle, usable as a regression target.
- **Value Area shading**: highlight ~68% density-mass zone (Market Profile-style) as a lighter overlay.
- **Multi-resolution density channels**: generate `density_vector` at multiple `nbins` (10/20/40) as stacked channels for CNN multi-scale input.
- **Volume-weighted density**: replace tick-count histogram with volume-weighted histogram when volume data exists (true volume profile).
- **POC drift feature**: bar-to-bar POC price change as an auxiliary time series for trend/reversal detection.
- **Concentration ratio flagging**: auto-label candles with high concentration_ratio as "indecision bars" for auxiliary classification.
- **Image-native export**: render fixed-size image tensors per candle/window for direct input into YOLO-style detectors, consistent with existing CV pipeline.
- **Interactive replay mode**: tick-by-tick animated fill of density profile, for QA/debugging of the simulator only.


---

## 9. R&D: Using Price-Time Concentration for Prediction

This section documents how the density/POC/value-area features generated by this pipeline can be applied to predictive modeling. Intended as a research direction reference for future implementation, not a finalized spec.

### 9.1 Point of Control (POC) as a Structural Feature

- POC (densest price level in a bar) often acts as a short-term support/resistance anchor; price frequently reverts to or breaks through prior POC levels.
- **Usage**: include `poc_price` (and `poc_price - close`, distance from current price) as regression features; use POC breakthrough/rejection as a binary classification label for next-bar direction.

### 9.2 POC Drift as a Trend/Momentum Signal

- Tracking POC movement bar-to-bar produces a time-weighted price trend line, smoother and less noisy than raw close-price momentum since it reflects where trading activity concentrated, not just the closing print.
- **Usage**: feed `poc_price` sequences (or their first difference) into sequence models (LSTM/Transformer) alongside price, or use POC slope over N bars as a trend-strength feature.

### 9.3 Value Area Breakout Signal

- When a bar's open/close falls outside the prior bar's value area (~68% density-mass zone), this often signals continuation rather than mean reversion.
- **Usage**: encode `VA_breakout_up` / `VA_breakout_down` as binary features; test as a leading indicator in classification models predicting next N-bar direction.

### 9.4 Concentration Ratio as Indecision/Volatility Proxy

- `concentration_ratio = max(density)/mean(density)`. Low ratio = price spread evenly across the range (indecision); high ratio = price pinned tightly (conviction).
- **Usage**: low-ratio bars preceding a breakout are a known precursor pattern; use as an input feature for breakout-probability classifiers, or as an auxiliary auto-labeling rule for "indecision bar" tagging.

### 9.5 Density Vector as a Learned Spatial Feature (CV Pipeline)

- The full `density_vector` (per-bin normalized density) can be treated as an additional image channel stacked with price/volume, allowing a CNN or YOLO-style detector to learn accumulation/distribution shapes directly, not just price direction.
- **Usage**: export fixed-size image tensors per candle/window (density heatmap + OHLC overlay) as training input; consistent with existing YOLO-based detection workflows, treating "setups" (e.g., accumulation before breakout) as a detectable visual pattern class.

### 9.6 Skew/Kurtosis of Density Profile

- Right-skewed density (heavier upper tail) vs. left-skewed can indicate buying vs. selling pressure exhaustion within the bar.
- **Usage**: include `skew`, `kurtosis` as auxiliary scalar features in tabular models; combine with concentration_ratio for a richer "bar character" feature set.

### 9.7 Recommended Next Step for Validation

- Current density/POC/value-area values are derived from a **synthetic** intrabar simulator (Brownian-bridge constrained to O/H/L/C) since only daily OHLC was available for testing.
- Before using any of the above features for real prediction, re-run the pipeline with **real intraday data** (e.g., 1-minute bars resampled into daily candles) to validate that synthetic density approximates real time-at-price distribution reasonably well; treat all conclusions above as hypotheses pending this validation.
