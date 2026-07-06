import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .config import FeaturesConfig, RenderingConfig
from .exceptions import RenderError
from .logger import logger


def render_heatmap_candle(
    fig: go.Figure,
    x_position: int,
    ohlc: dict[str, float],
    density: np.ndarray,
    bins: np.ndarray,
    half_width: float,
    config: RenderingConfig,
    heatmap_x: list[float],
    heatmap_y: list[float],
    heatmap_base: list[float],
    heatmap_width: list[float],
    heatmap_colors: list[str],
) -> None:
    """
    Render a single TimeDensityCandle on the provided Plotly figure.
    """
    open_p = ohlc["open"]
    high_p = ohlc["high"]
    low_p = ohlc["low"]
    close_p = ohlc["close"]
    color_template = config.color_scheme.bull if close_p >= open_p else config.color_scheme.bear

    body_min = min(open_p, close_p)
    body_max = max(open_p, close_p)

    # 1. Traditional candle wicks/tails (only on the ends, not inside the body)
    # We draw these with layer="above" so they render on top of the heatmap trace
    if low_p < body_min:
        fig.add_shape(
            type="line",
            x0=x_position,
            y0=low_p,
            x1=x_position,
            y1=body_min,
            line={"color": color_template.format(alpha=0.8), "width": 1.5},
            layer="above",
        )
    if body_max < high_p:
        fig.add_shape(
            type="line",
            x0=x_position,
            y0=body_max,
            x1=x_position,
            y1=high_p,
            line={"color": color_template.format(alpha=0.8), "width": 1.5},
            layer="above",
        )

    # 2. Draw the base candle body fill (no border)
    # We draw this with layer="below" so it renders underneath the heatmap trace
    fig.add_shape(
        type="rect",
        x0=x_position - half_width,
        y0=body_min,
        x1=x_position + half_width,
        y1=body_max,
        fillcolor=color_template.format(alpha=0.15),
        line={"width": 0},
        layer="below",
    )

    # 3. Collect the density profile (heatmap) blocks (split into lower tail, body, and upper tail)
    for j, density_value in enumerate(density):
        bin_low = bins[j]
        bin_high = bins[j + 1]
        
        parts = [] # list of tuples: (draw_low, draw_high, width)

        # Lower tail part
        lt_low = bin_low
        lt_high = min(bin_high, body_min)
        if lt_low < lt_high:
            if config.full_heatmap:
                parts.append((lt_low, lt_high, half_width * 2))
            elif config.extend_to_tails:
                parts.append((lt_low, lt_high, 0.08))

        # Body part
        b_low = max(bin_low, body_min)
        b_high = min(bin_high, body_max)
        if b_low < b_high:
            parts.append((b_low, b_high, half_width * 2))

        # Upper tail part
        ut_low = max(bin_low, body_max)
        ut_high = bin_high
        if ut_low < ut_high:
            if config.full_heatmap:
                parts.append((ut_low, ut_high, half_width * 2))
            elif config.extend_to_tails:
                parts.append((ut_low, ut_high, 0.08))

        for draw_low, draw_high, w in parts:
            alpha_j = float(density_value) * 0.45
            
            heatmap_x.append(float(x_position))
            heatmap_y.append(float(draw_high - draw_low))
            heatmap_base.append(float(draw_low))
            heatmap_width.append(float(w))
            heatmap_colors.append(color_template.format(alpha=alpha_j))

    # 4. Draw the traditional candle body border outline (no fill) on top of density blocks
    # We draw this with layer="above" so it renders on top of the heatmap trace
    fig.add_shape(
        type="rect",
        x0=x_position - half_width,
        y0=body_min,
        x1=x_position + half_width,
        y1=body_max,
        line={"color": color_template.format(alpha=0.8), "width": 1.5},
        layer="above",
    )


def _legend_position(position: str) -> dict[str, float | str]:
    positions = {
        "top_right": {"x": 1.02, "y": 1.0, "xanchor": "left", "yanchor": "top"},
        "top_left": {"x": 0.0, "y": 1.0, "xanchor": "left", "yanchor": "top"},
        "bottom_right": {"x": 1.02, "y": 0.0, "xanchor": "left", "yanchor": "bottom"},
        "bottom_left": {"x": 0.0, "y": 0.0, "xanchor": "left", "yanchor": "bottom"},
    }
    return positions[position]


# Legend proxy traces are no longer needed as POC marker and Value Area are rendered as interactive Scatter traces.


def _add_poc_drift_trace(
    fig: go.Figure,
    feature_df: pd.DataFrame,
    features_config: FeaturesConfig,
    rendering_config: RenderingConfig,
) -> None:
    if not features_config.enable_poc_drift_line:
        return

    style = rendering_config.overlay_style
    fig.add_trace(
        go.Scatter(
            x=list(range(len(feature_df))),
            y=feature_df["poc_price"],
            mode="lines",
            line={"color": style.poc_color, "width": 2, "dash": style.poc_drift_dash},
            name="POC drift",
        ),
    )


def _add_indecision_flags(
    fig: go.Figure,
    feature_df: pd.DataFrame,
    features_config: FeaturesConfig,
    rendering_config: RenderingConfig,
) -> None:
    if not features_config.enable_indecision_flags or feature_df.empty:
        return

    threshold = feature_df["concentration_ratio"].quantile(features_config.indecision_quantile)
    flagged = feature_df[feature_df["concentration_ratio"] <= threshold]
    if flagged.empty:
        return

    price_range = max(float(feature_df["high"].max() - feature_df["low"].min()), 1e-9)
    y_offset = price_range * 0.025
    style = rendering_config.overlay_style
    fig.add_trace(
        go.Scatter(
            x=flagged.index.tolist(),
            y=(flagged["high"] + y_offset).tolist(),
            mode="markers",
            marker={
                "symbol": "triangle-up",
                "color": style.indecision_color,
                "size": style.indecision_size,
            },
            name="Indecision",
        ),
    )


def build_heatmap_chart(
    feature_df: pd.DataFrame,
    rendering_config: RenderingConfig,
    features_config: FeaturesConfig,
) -> go.Figure:
    """
    Build a full Plotly chart from extracted TDC features.
    """
    try:
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=list(range(len(feature_df))),
                y=feature_df["high"].tolist(),
                mode="markers",
                marker={"color": "rgba(0,0,0,0)"},
                showlegend=False,
                hoverinfo="none",
            ),
        )
        fig.add_trace(
            go.Scatter(
                x=list(range(len(feature_df))),
                y=feature_df["low"].tolist(),
                mode="markers",
                marker={"color": "rgba(0,0,0,0)"},
                showlegend=False,
                hoverinfo="none",
            ),
        )

        half_width = rendering_config.overlay_style.candle_half_width
        density_cols = [c for c in feature_df.columns if c.startswith("density_")]

        poc_x = []
        poc_y = []
        va_x = []
        va_y = []
        
        heatmap_x = []
        heatmap_y = []
        heatmap_base = []
        heatmap_width = []
        heatmap_colors = []

        for i, row in feature_df.reset_index(drop=True).iterrows():
            ohlc = {
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
            density = row[density_cols].to_numpy(dtype=float)
            bins = np.linspace(ohlc["low"], ohlc["high"], len(density) + 1)

            render_heatmap_candle(
                fig, i, ohlc, density, bins, half_width, rendering_config,
                heatmap_x, heatmap_y, heatmap_base, heatmap_width, heatmap_colors
            )

            if features_config.enable_poc_marker:
                poc_x.extend([i - half_width, i + half_width, None])
                poc_y.extend([row["poc_price"], row["poc_price"], None])

            if features_config.enable_value_area:
                x0 = i - half_width
                x1 = i + half_width
                y0 = row["value_area_low"]
                y1 = row["value_area_high"]
                va_x.extend([x0, x1, x1, x0, x0, None])
                va_y.extend([y0, y0, y1, y1, y0, None])

        # Add the density profile heatmap as a single toggleable Bar trace
        if heatmap_x:
            # 1. The actual heatmap trace (hidden from the legend list directly, linked via legendgroup)
            fig.add_trace(
                go.Bar(
                    x=heatmap_x,
                    y=heatmap_y,
                    base=heatmap_base,
                    width=heatmap_width,
                    marker={
                        "color": heatmap_colors,
                        "line": {"width": 0},
                    },
                    name="Density Heatmap",
                    hoverinfo="none",
                    legendgroup="Density Heatmap",
                    showlegend=False,
                )
            )
            # 2. A dummy Bar trace with a solid color to represent the heatmap in the legend.
            # This prevents the legend icon from inheriting transparency/low opacity from the first data bins.
            fig.add_trace(
                go.Bar(
                    x=[None],
                    y=[None],
                    name="Density Heatmap",
                    marker={
                        "color": rendering_config.color_scheme.bull.format(alpha=0.8),
                        "line": {"width": 0},
                    },
                    legendgroup="Density Heatmap",
                    showlegend=True,
                )
            )

        if features_config.enable_value_area and len(feature_df) > 0:
            fig.add_trace(
                go.Scatter(
                    x=va_x,
                    y=va_y,
                    mode="lines",
                    fill="toself",
                    fillcolor=rendering_config.overlay_style.value_area_fill,
                    line={
                        "color": rendering_config.overlay_style.value_area_color,
                        "width": 2,
                        "dash": rendering_config.overlay_style.value_area_dash,
                    },
                    name="Value Area",
                    hoverinfo="none",
                )
            )

        if features_config.enable_poc_marker and len(feature_df) > 0:
            fig.add_trace(
                go.Scatter(
                    x=poc_x,
                    y=poc_y,
                    mode="lines",
                    line={
                        "color": rendering_config.overlay_style.poc_color,
                        "width": rendering_config.overlay_style.poc_width,
                    },
                    name="POC marker",
                    hoverinfo="none",
                )
            )

        normalized_feature_df = feature_df.reset_index(drop=True)
        _add_poc_drift_trace(fig, normalized_feature_df, features_config, rendering_config)
        _add_indecision_flags(fig, normalized_feature_df, features_config, rendering_config)

        fig.update_layout(
            title="TimeDensityCandles (TDC)",
            xaxis_title="Bar Index",
            yaxis_title="Price",
            template="plotly_dark",
            barmode="overlay", # Prevent horizontal shifting of bars when multiple Bar traces exist
            showlegend=rendering_config.legend.enabled,
            legend=_legend_position(rendering_config.legend.position),
            margin={"r": 140 if rendering_config.legend.position.endswith("right") else 40},
        )
        return fig
    except Exception as e:
        logger.error(f"Failed to render chart: {e}")
        raise RenderError(f"Rendering failed: {e}") from e
