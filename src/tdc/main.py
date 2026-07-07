import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import load_config
from .data import get_data
from .exceptions import TDCBaseError
from .export import save_features
from .features import build_feature_frame
from .intrabar import fetch_alphavantage_intrabar_bars, fetch_yahoo_intrabar_bars
from .logger import configure_logger, logger
from .render import build_heatmap_chart

load_dotenv()


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


def main(config_path: str) -> None:
    """
    Run the TDC data, feature, export, and render pipeline.
    """
    config = load_config(config_path)
    configure_logger(debug=config.app.debug, level_name=config.app.log_level)

    intrabar_df = None
    if config.algorithm.mode == "real" and config.data.intrabar_source == "yahoo":
        df, intrabar_df = fetch_yahoo_intrabar_bars(config.data)
    elif config.algorithm.mode == "real" and config.data.intrabar_source == "alphavantage":
        df, intrabar_df = fetch_alphavantage_intrabar_bars(config.data)
    else:
        df = get_data(config.data, enable_volume_weighting=config.algorithm.enable_volume_weighting)

    logger.info("Processing bars to generate TimeDensityCandles...")
    feature_df = build_feature_frame(df, config, intrabar_df)

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
