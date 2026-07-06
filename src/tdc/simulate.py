import numpy as np

from .exceptions import AlgorithmError


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
    Simulate a synthetic intrabar tick path constrained to OHLC bounds.
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
        # Zero-range bar, return a flat line of ticks
        return np.full(n_ticks, open_p)

    rng = np.random.default_rng(seed)
    path = np.zeros(n_ticks)
    path[0] = open_p

    sigma = (high_p - low_p) * volatility_factor
    if sigma == 0:
        sigma = 1e-6

    for i in range(1, n_ticks - 1):
        step = rng.normal(0, sigma)
        path[i] = np.clip(path[i - 1] + step, low_p, high_p)

    path[-1] = close_p

    # Ensure high and low are actually hit in the path
    idx_high, idx_low = rng.choice(range(1, n_ticks - 1), 2, replace=False)
    path[idx_high] = high_p
    path[idx_low] = low_p

    return path
