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


def test_value_area_shapes_use_dotted_blue_style() -> None:
    fig = build_heatmap_chart(_feature_df(), RenderingConfig(), FeaturesConfig())
    value_area_shapes = [
        shape
        for shape in fig.layout.shapes
        if shape.type == "rect" and shape.line.color == "deepskyblue"
    ]

    assert value_area_shapes
    assert all(shape.line.dash == "dot" for shape in value_area_shapes)
