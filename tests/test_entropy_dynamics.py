import math

from core.entropy import DynamicsParameters, compute_entropy, evolve, step
from core.fields import FieldState, Lattice, ScalarField


def test_energy_conserved_without_clamp():
    lattice = Lattice(2, 1)
    energy = ScalarField(lattice, [0.8, 0.2])
    params = DynamicsParameters(energy_bounds=None, activation_threshold=1.0)

    entropy = compute_entropy(energy, params)
    internal_time = ScalarField.constant(lattice, 1.0)
    state = FieldState(energy=energy, entropy=entropy, internal_time=internal_time)

    next_state = step(state, params)

    assert math.isclose(sum(state.energy.values), sum(next_state.energy.values))


def test_step_is_deterministic():
    lattice = Lattice(3, 1)
    energy = ScalarField(lattice, [0.7, 0.5, 0.3])
    params = DynamicsParameters(energy_bounds=None, activation_threshold=0.5)

    entropy = compute_entropy(energy, params)
    internal_time = ScalarField.constant(lattice, 0.75)
    state = FieldState(energy=energy, entropy=entropy, internal_time=internal_time)

    first = step(state.copy(), params)
    second = step(state.copy(), params)

    assert first.energy.values == second.energy.values
    assert first.internal_time.values == second.internal_time.values


def test_evolve_returns_snapshots_including_initial():
    lattice = Lattice(2, 2)
    energy = ScalarField.constant(lattice, 0.4)
    params = DynamicsParameters(energy_bounds=None)

    entropy = compute_entropy(energy, params)
    internal_time = ScalarField.constant(lattice, 0.0)
    state = FieldState(energy=energy, entropy=entropy, internal_time=internal_time)

    history = evolve(state, params, steps=3)

    assert len(history) == 4  # initial + 3 steps
    assert history[0].energy.values == energy.values
