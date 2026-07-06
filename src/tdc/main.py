import argparse
import sys
import pandas as pd
from pathlib import Path

from .config import load_config
from .data import get_data
from .simulate import simulate_intrabar_ticks
from .density import compute_density_profile, compute_profile_stats
from .render import build_heatmap_chart
from .export import save_features
from .exceptions import TDCBaseError
from .logger import logger

def cli():
    """
    Command Line Interface entry point.
    """
    parser = argparse.ArgumentParser(description="TimeDensityCandle (TDC) Generator")
    parser.add_argument("--config", type=str, default="tdc.yaml", help="Path to YAML configuration file")
    args = parser.parse_args()
    
    try:
        main(args.config)
    except TDCBaseError as e:
        # Expected errors, already logged. Stop execution cleanly.
        logger.error(f"Execution failed: {e}")
        sys.exit(1)
    except Exception as e:
        # Unexpected errors (rich traceback will handle printing detailed locals)
        logger.exception("An unexpected error occurred!")
        sys.exit(2)

def main(config_path: str):
    """
    Main orchestration logic.
    """
    # 1. Load config
    config = load_config(config_path)
    
    # 2. Fetch Data
    df = get_data(config.data, enable_volume_weighting=config.algorithm.enable_volume_weighting)
    
    # 3. Process each bar
    logger.info("Processing bars to generate TimeDensityCandles...")
    feature_rows = []
    
    for i, row in df.iterrows():
        open_p = row['open']
        high_p = row['high']
        low_p = row['low']
        close_p = row['close']
        
        # 3.1 Simulate ticks (or use real if mode is real, though real isn't fully implemented yet)
        if config.algorithm.mode == 'synthetic':
            ticks = simulate_intrabar_ticks(
                open_p, high_p, low_p, close_p, 
                n_ticks=100, 
                volatility_factor=config.algorithm.volatility_factor
            )
        else:
            logger.warning("Real mode requested but not fully implemented. Falling back to synthetic.")
            ticks = simulate_intrabar_ticks(open_p, high_p, low_p, close_p, 100, config.algorithm.volatility_factor)
            
        # 3.2 Compute Density
        volume = None
        if config.algorithm.enable_volume_weighting and 'volume' in row:
            # Fake volume spread across ticks just as an example if it was real
            # For synthetic, we just weight them evenly if true volume tick isn't available
            pass
            
        density, bins = compute_density_profile(ticks, low_p, high_p, config.algorithm.nbins, volume)
        
        # 3.3 Compute Stats
        stats = compute_profile_stats(ticks, density, bins)
        
        # 3.4 Build Row
        row_dict = {
            'timestamp': row.get('timestamp', i),
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
        }
        for j in range(len(density)):
            row_dict[f'density_{j:02d}'] = density[j]
        row_dict.update(stats)
        feature_rows.append(row_dict)
        
    feature_df = pd.DataFrame(feature_rows)
    
    # 4. Export Features
    if config.features.export_csv:
        save_features(feature_df, config.app.output_dir, config.data.ticker)
        
    # 5. Render Chart
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
        except ValueError as e:
            if "kaleido" in str(e).lower():
                logger.error("Kaleido is required to export PNG. Install it via `uv add kaleido`.")
            else:
                logger.error(f"Failed to export PNG: {e}")

    logger.info("Pipeline completed successfully!")

if __name__ == "__main__":
    cli()
