import math
from dataclasses import replace

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


def test_step_requires_internal_time_activation():
    lattice = Lattice(2, 1)
    energy = ScalarField(lattice, [1.0, 0.0])
    params = DynamicsParameters(
        equilibrium_energy=0.0,
        gamma=0.0,
        kappa=0.5,
        alpha=0.0,
        lambda_t=3.0,
        activation_threshold=2.0,
        energy_bounds=None,
    )

    entropy = compute_entropy(energy, params)
    internal_time = ScalarField.constant(lattice, 0.0)
    state = FieldState(energy=energy, entropy=entropy, internal_time=internal_time)

    next_state = step(state, params)

    assert next_state.energy.values == energy.values
    assert next_state.internal_time.values != internal_time.values


def test_entropy_suppresses_transport_flux():
    lattice = Lattice(2, 1)
    energy = ScalarField(lattice, [1.0, 0.0])
    base_params = DynamicsParameters(
        equilibrium_energy=0.0,
        gamma=0.0,
        kappa=0.25,
        alpha=0.0,
        lambda_t=0.0,
        activation_threshold=0.5,
        energy_bounds=None,
    )
    suppressed_params = replace(base_params, alpha=5.0)

    entropy = compute_entropy(energy, base_params)
    internal_time = ScalarField.constant(lattice, 1.0)
    base_state = FieldState(energy=energy.copy(), entropy=entropy, internal_time=internal_time)

    base_next = step(base_state, base_params)
    suppressed_next = step(base_state, suppressed_params)

    assert base_next.energy.values[1] > suppressed_next.energy.values[1]
    assert suppressed_next.energy.values[1] > 0.0
