from __future__ import annotations

import pytest

from detm.runtime.api import digest, reset, step
from detm.core.entropy import DynamicsParameters
from detm.runtime.config import DETMConfig
from detm.runtime.symbols import make_symbol


def test_golden_digest_fixed_sequence():
    config = DETMConfig(
        width=8,
        height=8,
        initial_noise=0.0,
        backend="numpy",
        device="cpu",
        dynamics=DynamicsParameters(alpha=0.3, beta=0.8, gamma=0.1, kappa=0.1, lambda_t=1.0),
    )
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
        3.399692944101423e-05,
        0.4960499769781937,
        0.5162570187976736,
        4.704529640230768e-05,
        4.557045556651192e-09,
        0.9921443350432849,
        3.491638539310525,
        3.4930160797216474,
    ]

    assert digest(state).vector == pytest.approx(expected, abs=1e-12, rel=0.0)
