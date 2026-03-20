from __future__ import annotations

import numpy as np
import pytest
from detm.runtime.api import digest, reset, step
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import LevelPolicy
from detm.runtime.serialization import deserialize_state, serialize_state
from detm.runtime.symbols import make_symbol


def test_seed_determinism_matches_signature():
    config = DETMConfig(width=8, height=8, initial_noise=0.01, backend="numpy", device="cpu")
    influence = make_symbol("pulse", amplitude=0.1, region=(4, 4, 2))

    state_a = reset(config, seed=123)
    state_b = reset(config, seed=123)

    state_a, obs_a = step(state_a, influence, n_ticks=3, rng=state_a.restore_rng())
    state_b, obs_b = step(state_b, influence, n_ticks=3, rng=state_b.restore_rng())

    assert obs_a.signature.vector == obs_b.signature.vector
    assert digest(state_a).vector == digest(state_b).vector


def test_serialize_roundtrip_preserves_digest():
    config = DETMConfig(width=6, height=6, initial_noise=0.02, backend="numpy", device="cpu")
    influence = DETMInfluence(symbol_id="test", amplitude=0.05, region=(3, 3, 1))

    state = reset(config, seed=7)
    state, _ = step(state, influence, n_ticks=2, rng=state.restore_rng())

    blob = serialize_state(state)
    restored = deserialize_state(blob)

    assert digest(state).vector == digest(restored).vector


def test_reset_with_nd_shape_preserves_shape_and_digest_roundtrip():
    config = DETMConfig(shape=(2, 6, 6), initial_noise=0.02, backend="numpy", device="cpu")

    state = reset(config, seed=17)
    blob = serialize_state(state)
    restored = deserialize_state(blob)

    assert state.shape == (2, 6, 6)
    assert tuple(np.asarray(state.field_state.energy).shape) == (2, 6, 6)
    assert restored.shape == (2, 6, 6)
    assert digest(state).vector == digest(restored).vector


def test_step_advances_nd_state_under_nd_runtime_contract():
    config = DETMConfig(shape=(2, 6, 6), initial_noise=0.02, backend="numpy", device="cpu")
    state = reset(config, seed=23)

    state_out, observables = step(state, influence=None, n_ticks=1)

    assert state_out.shape == (2, 6, 6)
    assert tuple(np.asarray(state_out.field_state.energy).shape) == (2, 6, 6)
    assert observables.signature.version


def test_step_advances_nd_state_when_refinement_and_influence_are_disabled():
    config = DETMConfig(
        shape=(2, 6, 6),
        initial_noise=0.02,
        backend="numpy",
        device="cpu",
        level_policy=LevelPolicy(allow_refinement=False),
    )
    state = reset(config, seed=29)
    before = np.asarray(state.field_state.energy).copy()

    state_out, observables = step(state, influence=None, n_ticks=2)

    assert state_out.shape == (2, 6, 6)
    assert tuple(np.asarray(state_out.field_state.energy).shape) == (2, 6, 6)
    assert not np.allclose(before, np.asarray(state_out.field_state.energy))
    assert observables.signature.version


def test_step_advances_nd_state_with_influence_when_refinement_is_disabled():
    config = DETMConfig(
        shape=(2, 6, 6),
        initial_noise=0.02,
        backend="numpy",
        device="cpu",
        level_policy=LevelPolicy(allow_refinement=False),
    )
    state = reset(config, seed=31)
    before = np.asarray(state.field_state.energy).copy()

    state_out, observables = step(
        state, influence=DETMInfluence(symbol_id="pulse", amplitude=0.1, region=(3, 3, 1)), n_ticks=1
    )

    assert state_out.shape == (2, 6, 6)
    assert not np.allclose(before, np.asarray(state_out.field_state.energy))
    assert observables.signature.version


def test_step_advances_nd_state_with_plane_wise_refinement():
    config = DETMConfig(
        shape=(2, 6, 6),
        initial_noise=0.0,
        backend="numpy",
        device="cpu",
        level_policy=LevelPolicy(allow_refinement=True),
    )
    state = reset(config, seed=37)
    energy = np.zeros((2, 6, 6), dtype=float)
    energy[0, 3, 3] = 3.0
    energy[1, 2, 2] = 3.0
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(
        energy,
        state.dynamics,
        boundary=state.lattice.boundary,
    )

    state_out, observables = step(state, influence=None, n_ticks=0)

    refinement_events = [event for event in list(observables.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 2
    assert sorted(list(event.get("plane_index", [])) for event in refinement_events) == [[0], [1]]
    assert tuple(np.asarray(state_out.field_state.energy).shape) == (2, 6, 6)


def test_step_reports_nd_costs_from_full_state_not_projected_plane():
    config = DETMConfig(shape=(2, 6, 6), initial_noise=0.02, backend="numpy", device="cpu")
    state = reset(config, seed=41)

    _state_out, observables = step(state, influence=None, n_ticks=5)

    assert float(observables.cost["step_ops_estimate"]) == float(2 * 6 * 6 * 5)
    assert float(observables.cost["memory_bytes_estimate"]) == float(2 * 6 * 6 * 3 * 8)
