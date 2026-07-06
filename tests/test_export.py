import pandas as pd

from tdc.export import save_features


def test_save_features_writes_csv(tmp_path) -> None:
    df = pd.DataFrame({"open": [1.0], "close": [2.0]})

    saved = save_features(df, str(tmp_path), "AAPL", ["csv"])

    assert saved == [tmp_path / "AAPL_features.csv"]
    assert (tmp_path / "AAPL_features.csv").exists()
