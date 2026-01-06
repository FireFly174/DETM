from __future__ import annotations

import pytest

from detm.runtime.api import digest, reset, step
from detm.runtime.config import DETMConfig
from detm.runtime.symbols import make_symbol


def test_golden_digest_fixed_sequence():
    config = DETMConfig(width=8, height=8, initial_noise=0.0, backend="numpy", device="cpu")
    state = reset(config, seed=1234)

    influences = [
        make_symbol("pulse", amplitude=0.1, region=(4, 4, 2)),
        make_symbol("cooldown", amplitude=-0.05, region=(4, 4, 3), seed=42),
        make_symbol("noise_burst", amplitude=0.02, region=(2, 2, 2)),
    ]

    for influence in influences:
        state, _ = step(state, influence, n_ticks=3, rng=None)

    expected = [
        0.5022819912856047,
        2.2668669926365247e-05,
        0.496869538500805,
        0.5130619026609632,
        0.00013938077076970428,
        3.401156654845479e-08,
        0.9690044939454818,
        3.4920905856335738,
        3.4932493865189906,
    ]

    assert digest(state).vector == pytest.approx(expected, abs=1e-12, rel=0.0)
