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
) -> None:
    """
    Render a single TimeDensityCandle on the provided Plotly figure.
    """
    open_p = ohlc["open"]
    high_p = ohlc["high"]
    low_p = ohlc["low"]
    close_p = ohlc["close"]
    color_template = config.color_scheme.bull if close_p >= open_p else config.color_scheme.bear

    fig.add_shape(
        type="line",
        x0=x_position,
        y0=low_p,
        x1=x_position,
        y1=high_p,
        line={"color": "gray", "width": 1},
    )

    body_min = min(open_p, close_p)
    body_max = max(open_p, close_p)
    fig.add_shape(
        type="rect",
        x0=x_position - half_width,
        y0=body_min,
        x1=x_position + half_width,
        y1=body_max,
        line={"color": "gray", "width": 1},
    )

    base_alpha = 0.1
    for j, density_value in enumerate(density):
        draw_low = max(bins[j], body_min)
        draw_high = min(bins[j + 1], body_max)

        if draw_low >= draw_high:
            continue

        alpha_j = base_alpha + (1 - base_alpha) * float(density_value)
        fig.add_shape(
            type="rect",
            x0=x_position - half_width,
            y0=draw_low,
            x1=x_position + half_width,
            y1=draw_high,
            fillcolor=color_template.format(alpha=alpha_j),
            line={"width": 0},
            layer="below",
        )


def _legend_position(position: str) -> dict[str, float | str]:
    positions = {
        "top_right": {"x": 1.02, "y": 1.0, "xanchor": "left", "yanchor": "top"},
        "top_left": {"x": 0.0, "y": 1.0, "xanchor": "left", "yanchor": "top"},
        "bottom_right": {"x": 1.02, "y": 0.0, "xanchor": "left", "yanchor": "bottom"},
        "bottom_left": {"x": 0.0, "y": 0.0, "xanchor": "left", "yanchor": "bottom"},
    }
    return positions[position]


def _add_legend_proxy_traces(
    fig: go.Figure,
    features_config: FeaturesConfig,
    rendering_config: RenderingConfig,
) -> None:
    style = rendering_config.overlay_style
    if features_config.enable_poc_marker:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line={"color": style.poc_color, "width": style.poc_width},
                name="POC marker",
            ),
        )
    if features_config.enable_value_area:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line={"color": style.value_area_color, "width": 2, "dash": style.value_area_dash},
                name="Value Area",
            ),
        )


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

        for i, row in feature_df.reset_index(drop=True).iterrows():
            ohlc = {
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
            density = row[density_cols].to_numpy(dtype=float)
            bins = np.linspace(ohlc["low"], ohlc["high"], len(density) + 1)

            render_heatmap_candle(fig, i, ohlc, density, bins, half_width, rendering_config)

            if features_config.enable_poc_marker:
                fig.add_shape(
                    type="line",
                    x0=i - half_width,
                    y0=row["poc_price"],
                    x1=i + half_width,
                    y1=row["poc_price"],
                    line={
                        "color": rendering_config.overlay_style.poc_color,
                        "width": rendering_config.overlay_style.poc_width,
                    },
                    layer="above",
                )

            if features_config.enable_value_area:
                fig.add_shape(
                    type="rect",
                    x0=i - half_width,
                    y0=row["value_area_low"],
                    x1=i + half_width,
                    y1=row["value_area_high"],
                    fillcolor=rendering_config.overlay_style.value_area_fill,
                    line={
                        "color": rendering_config.overlay_style.value_area_color,
                        "width": 2,
                        "dash": rendering_config.overlay_style.value_area_dash,
                    },
                    layer="above",
                )

        _add_legend_proxy_traces(fig, features_config, rendering_config)
        normalized_feature_df = feature_df.reset_index(drop=True)
        _add_poc_drift_trace(fig, normalized_feature_df, features_config, rendering_config)
        _add_indecision_flags(fig, normalized_feature_df, features_config, rendering_config)

        fig.update_layout(
            title="TimeDensityCandles (TDC)",
            xaxis_title="Bar Index",
            yaxis_title="Price",
            template="plotly_dark",
            showlegend=rendering_config.legend.enabled,
            legend=_legend_position(rendering_config.legend.position),
            margin={"r": 140 if rendering_config.legend.position.endswith("right") else 40},
        )
        return fig
    except Exception as e:
        logger.error(f"Failed to render chart: {e}")
        raise RenderError(f"Rendering failed: {e}") from e
