import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config
from .data import get_data
from .density import compute_density_profile, compute_profile_stats
from .exceptions import AlgorithmError, TDCBaseError
from .export import save_features
from .logger import configure_logger, logger
from .render import build_heatmap_chart
from .simulate import simulate_intrabar_ticks


def cli() -> None:
    """
    Command-line entry point.
    """
    parser = argparse.ArgumentParser(description="TimeDensityCandle (TDC) Generator")
    parser.add_argument(
        "--config",
        type=str,
        default="tdc.yaml",
        help="Path to YAML configuration file",
    )
    args = parser.parse_args()

    try:
        main(args.config)
    except TDCBaseError as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)
    except Exception:
        logger.exception("An unexpected error occurred.")
        sys.exit(2)


def _synthetic_volume_weights(row: pd.Series, tick_count: int) -> np.ndarray | None:
    if "volume" not in row or pd.isna(row["volume"]):
        return None

    return np.full(tick_count, float(row["volume"]) / tick_count)


def main(config_path: str) -> None:
    """
    Run the TDC data, feature, export, and render pipeline.
    """
    config = load_config(config_path)
    configure_logger(debug=config.app.debug, level_name=config.app.log_level)

    if config.algorithm.mode == "real":
        raise AlgorithmError(
            "mode='real' is not implemented yet. Use mode='synthetic' or add real "
            "intrabar support first.",
        )

    df = get_data(config.data, enable_volume_weighting=config.algorithm.enable_volume_weighting)

    logger.info("Processing bars to generate TimeDensityCandles...")
    feature_rows = []

    for bar_number, (i, row) in enumerate(df.iterrows()):
        open_p = float(row["open"])
        high_p = float(row["high"])
        low_p = float(row["low"])
        close_p = float(row["close"])

        seed = (
            None
            if config.algorithm.random_seed is None
            else config.algorithm.random_seed + bar_number
        )
        ticks = simulate_intrabar_ticks(
            open_p,
            high_p,
            low_p,
            close_p,
            n_ticks=config.algorithm.synthetic_tick_count,
            volatility_factor=config.algorithm.volatility_factor,
            seed=seed,
        )

        volume = None
        if config.algorithm.enable_volume_weighting:
            volume = _synthetic_volume_weights(row, len(ticks))
            if volume is None:
                logger.warning(
                    "Volume weighting requested, but row volume is missing. "
                    "Using unweighted density.",
                )

        density, bins = compute_density_profile(
            ticks,
            low_p,
            high_p,
            config.algorithm.nbins,
            volume,
        )
        stats = compute_profile_stats(ticks, density, bins)

        row_dict = {
            "timestamp": row.get("timestamp", i),
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
        }
        for j, density_value in enumerate(density):
            row_dict[f"density_{j:02d}"] = float(density_value)
        row_dict.update(stats)
        feature_rows.append(row_dict)

    feature_df = pd.DataFrame(feature_rows)

    export_formats = list(config.features.export_formats)
    if not config.features.export_csv and "csv" in export_formats:
        export_formats.remove("csv")

    if export_formats:
        save_features(
            feature_df,
            config.app.output_dir,
            config.data.ticker,
            export_formats,
        )

    if config.rendering.enable_chart:
        logger.info("Rendering heatmap chart...")
        fig = build_heatmap_chart(feature_df, config.rendering, config.features)

        path = Path(config.app.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        html_file = path / f"{config.data.ticker}_chart.html"
        png_file = path / f"{config.data.ticker}_chart.png"

        fig.write_html(str(html_file))
        logger.info(f"Chart saved as HTML: {html_file}")

        try:
            fig.write_image(str(png_file))
            logger.info(f"Chart saved as PNG: {png_file}")
        except Exception as e:
            logger.error(f"Failed to export PNG chart '{png_file}': {e}")

    logger.info("Pipeline completed successfully.")


if __name__ == "__main__":
    cli()
