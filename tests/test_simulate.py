import numpy as np
import pytest

from tdc.exceptions import AlgorithmError
from tdc.simulate import simulate_intrabar_ticks


def test_simulation_is_deterministic_with_seed() -> None:
    first = simulate_intrabar_ticks(10.0, 12.0, 9.0, 11.0, seed=7)
    second = simulate_intrabar_ticks(10.0, 12.0, 9.0, 11.0, seed=7)

    np.testing.assert_array_equal(first, second)


def test_simulation_rejects_too_few_ticks() -> None:
    with pytest.raises(AlgorithmError, match="n_ticks >= 4"):
        simulate_intrabar_ticks(10.0, 12.0, 9.0, 11.0, n_ticks=3)


def test_simulation_rejects_open_close_outside_range() -> None:
    with pytest.raises(AlgorithmError, match="Open"):
        simulate_intrabar_ticks(8.0, 12.0, 9.0, 11.0)

    with pytest.raises(AlgorithmError, match="Close"):
        simulate_intrabar_ticks(10.0, 12.0, 9.0, 13.0)
