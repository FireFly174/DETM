from __future__ import annotations

import numpy as np

from runtime.api import digest, reset, step
from runtime.config import DETMConfig
from runtime.influence import DETMInfluence
from runtime.serialization import deserialize_state, serialize_state
from runtime.symbols import make_symbol


def test_seed_determinism_matches_signature():
    config = DETMConfig(width=8, height=8, initial_noise=0.01)
    influence = make_symbol("pulse", amplitude=0.1, region=(4, 4, 2))

    state_a = reset(config, seed=123)
    state_b = reset(config, seed=123)

    state_a, obs_a = step(state_a, influence, n_ticks=3, rng=state_a.restore_rng())
    state_b, obs_b = step(state_b, influence, n_ticks=3, rng=state_b.restore_rng())

    assert obs_a.signature.vector == obs_b.signature.vector
    assert digest(state_a).vector == digest(state_b).vector


def test_serialize_roundtrip_preserves_digest():
    config = DETMConfig(width=6, height=6, initial_noise=0.02)
    influence = DETMInfluence(symbol_id="test", amplitude=0.05, region=(3, 3, 1))

    state = reset(config, seed=7)
    state, _ = step(state, influence, n_ticks=2, rng=np.random.default_rng(7))

    blob = serialize_state(state)
    restored = deserialize_state(blob)

    assert digest(state).vector == digest(restored).vector
