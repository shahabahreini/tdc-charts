import pandas as pd

from tdc.config import FeaturesConfig, RenderingConfig
from tdc.render import build_heatmap_chart


def _feature_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10.0, 11.0, 10.5, 10.2],
            "high": [12.0, 12.5, 11.5, 11.0],
            "low": [9.0, 10.0, 9.5, 9.8],
            "close": [11.0, 10.5, 10.2, 10.8],
            "density_00": [0.2, 0.5, 1.0, 0.1],
            "density_01": [1.0, 0.5, 0.2, 0.1],
            "poc_price": [10.5, 11.5, 10.0, 10.4],
            "value_area_low": [10.0, 10.8, 9.8, 10.0],
            "value_area_high": [11.0, 11.8, 10.8, 10.6],
            "concentration_ratio": [1.8, 1.1, 2.2, 0.8],
        },
    )


def test_render_adds_visible_feature_legend_entries() -> None:
    fig = build_heatmap_chart(_feature_df(), RenderingConfig(), FeaturesConfig())
    names = {trace.name for trace in fig.data}

    assert fig.layout.showlegend is True
    assert {"POC marker", "POC drift", "Value Area", "Indecision"}.issubset(names)


def test_render_can_disable_legend_and_poc_drift() -> None:
    rendering = RenderingConfig(legend={"enabled": False})
    features = FeaturesConfig(enable_poc_drift_line=False)

    fig = build_heatmap_chart(_feature_df(), rendering, features)
    names = {trace.name for trace in fig.data}

    assert fig.layout.showlegend is False
    assert "POC drift" not in names


def test_value_area_trace_uses_dotted_blue_style() -> None:
    fig = build_heatmap_chart(_feature_df(), RenderingConfig(), FeaturesConfig())
    value_area_traces = [
        trace
        for trace in fig.data
        if trace.name == "Value Area"
    ]

    assert value_area_traces
    assert len(value_area_traces) == 1
    trace = value_area_traces[0]
    assert trace.line.color == "deepskyblue"
    assert trace.line.dash == "dot"
    assert trace.fill == "toself"


def test_heatmap_full_range_rendering() -> None:
    # 1. Test standard/clamped heatmap (default)
    rendering_default = RenderingConfig(full_heatmap=False)
    fig_default = build_heatmap_chart(_feature_df(), rendering_default, FeaturesConfig())
    heatmap_default = [t for t in fig_default.data if t.name == "Density Heatmap"][0]
    
    # First candle has indices where x == 0
    candle_0_indices = [i for i, x in enumerate(heatmap_default.x) if x == 0]
    total_height_0_default = sum(heatmap_default.y[i] for i in candle_0_indices)
    assert abs(total_height_0_default - 1.0) < 1e-5  # Open to Close body height = 11.0 - 10.0 = 1.0

    # 2. Test full heatmap
    rendering_full = RenderingConfig(full_heatmap=True)
    fig_full = build_heatmap_chart(_feature_df(), rendering_full, FeaturesConfig())
    heatmap_full = [t for t in fig_full.data if t.name == "Density Heatmap"][0]
    
    candle_0_indices_full = [i for i, x in enumerate(heatmap_full.x) if x == 0]
    total_height_0_full = sum(heatmap_full.y[i] for i in candle_0_indices_full)
    assert abs(total_height_0_full - 3.0) < 1e-5  # High to Low height = 12.0 - 9.0 = 3.0


def test_heatmap_extend_to_tails_rendering() -> None:
    # 1. Test extend_to_tails=True
    rendering_tails = RenderingConfig(extend_to_tails=True)
    fig_tails = build_heatmap_chart(_feature_df(), rendering_tails, FeaturesConfig())
    heatmap_tails = [t for t in fig_tails.data if t.name == "Density Heatmap"][0]
    
    # First candle indices where x == 0
    candle_0_indices = [i for i, x in enumerate(heatmap_tails.x) if x == 0]
    
    # The total height of all parts should sum to 3.0 (from 9.0 to 12.0)
    total_height_0 = sum(heatmap_tails.y[i] for i in candle_0_indices)
    assert abs(total_height_0 - 3.0) < 1e-5
    
    body_widths = [
        heatmap_tails.width[i]
        for i in candle_0_indices
        if heatmap_tails.width[i] == 0.8
    ]
    tail_widths = [
        heatmap_tails.width[i]
        for i in candle_0_indices
        if heatmap_tails.width[i] == 0.08
    ]
    
    # Check that both tail and body widths are present
    assert len(body_widths) > 0
    assert len(tail_widths) > 0
