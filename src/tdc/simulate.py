import numpy as np

from .exceptions import AlgorithmError


def _bridge_segment(
    start_price: float,
    end_price: float,
    length: int,
    rng: np.random.Generator,
    sigma: float,
    low_p: float,
    high_p: float,
) -> np.ndarray:
    if length <= 1:
        return np.array([start_price], dtype=float)

    t = np.linspace(0.0, 1.0, length)
    mean_path = start_price + ((end_price - start_price) * t)
    noise = rng.normal(0.0, sigma, length) * np.sin(np.pi * t)
    segment = np.clip(mean_path + noise, low_p, high_p)
    segment[0] = start_price
    segment[-1] = end_price
    return segment


def simulate_intrabar_ticks(
    open_p: float,
    high_p: float,
    low_p: float,
    close_p: float,
    n_ticks: int = 100,
    volatility_factor: float = 0.03,
    seed: int | None = None,
) -> np.ndarray:
    """
    Simulate a synthetic OHLC-anchored intrabar bridge.
    """
    if n_ticks < 4:
        raise AlgorithmError("Synthetic tick simulation requires n_ticks >= 4")

    if high_p < low_p:
        raise AlgorithmError(f"Invalid bar: High ({high_p}) is less than Low ({low_p})")

    if not low_p <= open_p <= high_p:
        raise AlgorithmError(
            f"Invalid bar: Open ({open_p}) must be within Low/High [{low_p}, {high_p}]",
        )

    if not low_p <= close_p <= high_p:
        raise AlgorithmError(
            f"Invalid bar: Close ({close_p}) must be within Low/High [{low_p}, {high_p}]",
        )

    if high_p == low_p:
        return np.full(n_ticks, open_p)

    rng = np.random.default_rng(seed)
    sigma = max((high_p - low_p) * volatility_factor, 1e-12)
    first_extreme, second_extreme = (high_p, low_p)
    if rng.random() < 0.5:
        first_extreme, second_extreme = second_extreme, first_extreme

    idx_first, idx_second = sorted(rng.choice(range(1, n_ticks - 1), 2, replace=False))
    anchors = [
        (0, open_p),
        (int(idx_first), first_extreme),
        (int(idx_second), second_extreme),
        (n_ticks - 1, close_p),
    ]

    path = np.empty(n_ticks, dtype=float)
    for (start_idx, start_price), (end_idx, end_price) in zip(
        anchors[:-1],
        anchors[1:],
        strict=True,
    ):
        segment = _bridge_segment(
            start_price,
            end_price,
            end_idx - start_idx + 1,
            rng,
            sigma,
            low_p,
            high_p,
        )
        path[start_idx : end_idx + 1] = segment

    return path
