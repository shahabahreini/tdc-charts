import plotly.graph_objects as go
import pandas as pd
import numpy as np
from .config import RenderingConfig
from .exceptions import RenderError
from .logger import logger

def render_heatmap_candle(fig: go.Figure, x_position, ohlc: dict, density: np.ndarray, bins: np.ndarray, half_width: float, config: RenderingConfig):
    """
    Renders a single TDC candle on the given plotly figure.
    """
    open_p, high_p, low_p, close_p = ohlc['open'], ohlc['high'], ohlc['low'], ohlc['close']
    is_bull = close_p >= open_p
    color_template = config.color_scheme.bull if is_bull else config.color_scheme.bear
    
    # Draw wick
    fig.add_shape(
        type="line",
        x0=x_position, y0=low_p, x1=x_position, y1=high_p,
        line=dict(color="gray", width=1)
    )
    
    # Draw body outline
    fig.add_shape(
        type="rect",
        x0=x_position - half_width, y0=min(open_p, close_p),
        x1=x_position + half_width, y1=max(open_p, close_p),
        line=dict(color="gray", width=1)
    )
    
    # Draw density bins inside body bounds
    body_min = min(open_p, close_p)
    body_max = max(open_p, close_p)
    
    base_alpha = 0.1
    for j in range(len(density)):
        bin_low = bins[j]
        bin_high = bins[j+1]
        
        # Only draw inside the body
        draw_low = max(bin_low, body_min)
        draw_high = min(bin_high, body_max)
        
        if draw_low >= draw_high:
            continue
            
        alpha_j = base_alpha + (1 - base_alpha) * density[j]
        color_j = color_template.format(alpha=alpha_j)
        
        fig.add_shape(
            type="rect",
            x0=x_position - half_width, y0=draw_low,
            x1=x_position + half_width, y1=draw_high,
            fillcolor=color_j,
            line=dict(width=0),
            layer="below"
        )

def build_heatmap_chart(feature_df: pd.DataFrame, rendering_config: RenderingConfig, features_config) -> go.Figure:
    """
    Builds the full Plotly chart from the feature dataframe.
    """
    try:
        fig = go.Figure()
        
        # Add invisible traces to force Plotly to auto-scale the axes for the shapes
        fig.add_trace(go.Scatter(
            x=list(range(len(feature_df))), y=feature_df['high'].tolist(),
            mode='markers', marker=dict(color='rgba(0,0,0,0)'),
            showlegend=False, hoverinfo='none'
        ))
        fig.add_trace(go.Scatter(
            x=list(range(len(feature_df))), y=feature_df['low'].tolist(),
            mode='markers', marker=dict(color='rgba(0,0,0,0)'),
            showlegend=False, hoverinfo='none'
        ))
        
        half_width = 0.4
        for i, row in feature_df.iterrows():
            ohlc = {'open': row['open'], 'high': row['high'], 'low': row['low'], 'close': row['close']}
            
            # Extract density vector based on columns
            density_cols = [c for c in feature_df.columns if c.startswith('density_')]
            density = row[density_cols].values
            
            # Reconstruct bins evenly spaced
            bins = np.linspace(ohlc['low'], ohlc['high'], len(density) + 1)
            
            render_heatmap_candle(fig, i, ohlc, density, bins, half_width, rendering_config)
            
            if features_config.enable_poc_overlay:
                fig.add_shape(
                    type="line",
                    x0=i - half_width, y0=row['poc_price'],
                    x1=i + half_width, y1=row['poc_price'],
                    line=dict(color="blue", width=2)
                )
                
            if features_config.enable_value_area:
                fig.add_shape(
                    type="rect",
                    x0=i - half_width, y0=row['value_area_low'],
                    x1=i + half_width, y1=row['value_area_high'],
                    fillcolor="rgba(255, 255, 0, 0.1)",
                    line=dict(width=0),
                    layer="below"
                )

        fig.update_layout(
            title="TimeDensityCandles (TDC)",
            xaxis_title="Bar Index",
            yaxis_title="Price",
            template="plotly_dark",
            showlegend=False
        )
        return fig
    except Exception as e:
        logger.error(f"Failed to render chart: {e}")
        raise RenderError(f"Rendering failed: {e}") from e
