"""Deterministic transport and entropy utilities for DETM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Tuple

from .fields import FieldState, Lattice, ScalarField


@dataclass(frozen=True)
class DynamicsParameters:
    """Container for transport and timing constants.

    Parameters
    ----------
    equilibrium_energy:
        Reference level :math:`E_0` used in entropy and chemical potential.
    beta:
        Weight for the local energy deviation component of entropy.
    gamma:
        Weight for neighbour deviation contribution to entropy.
    kappa:
        Conductivity scale for energy transport.
    alpha:
        Entropic suppression factor; larger values lower conductance.
    lambda_t:
        Sensitivity of internal time velocity to entropy.
    activation_threshold:
        Minimal accumulated internal time required to emit flux.
    energy_bounds:
        Optional ``(min, max)`` clamp applied after each step. ``None`` disables
        clamping.
    """

    equilibrium_energy: float = 0.5
    beta: float = 1.0
    gamma: float = 1.0
    kappa: float = 0.1
    alpha: float = 1.0
    lambda_t: float = 1.0
    activation_threshold: float = 1.0
    energy_bounds: Tuple[float, float] | None = (0.0, 1.0)


# ---------------------------------------------------------------------------
# Field construction helpers
# ---------------------------------------------------------------------------
def compute_entropy(energy: ScalarField, params: DynamicsParameters) -> ScalarField:
    """Return entropy field derived from the provided energy values."""

    lattice = energy.lattice
    entropy_values: List[float] = [0.0] * lattice.size

    for coord in lattice.positions():
        idx = energy.index(coord)
        local_delta = energy.values[idx] - params.equilibrium_energy
        neighbourhood_delta = 0.0
        for neighbour in lattice.neighbors(coord):
            n_idx = energy.index(neighbour)
            neighbourhood_delta += (energy.values[n_idx] - params.equilibrium_energy) ** 2

        entropy_values[idx] = params.beta * (local_delta**2) + params.gamma * neighbourhood_delta

    return ScalarField(lattice, entropy_values)


def chemical_potential(energy: ScalarField, params: DynamicsParameters) -> ScalarField:
    """Compute raw chemical potential field."""

    mu_values = [2 * params.beta * (value - params.equilibrium_energy) for value in energy.values]
    return ScalarField(energy.lattice, mu_values)


def effective_potential(mu: ScalarField) -> ScalarField:
    """Return zero-mean effective potential :math:`\\mu - \\langle\\mu\\rangle`."""

    average = sum(mu.values) / len(mu.values)
    return ScalarField(mu.lattice, [value - average for value in mu.values])


def conductance(entropy: ScalarField, params: DynamicsParameters) -> ScalarField:
    """Compute conductance suppressed by entropy."""

    sigma_values = [1.0 / (1.0 + params.alpha * value) for value in entropy.values]
    return ScalarField(entropy.lattice, sigma_values)


def internal_time_velocity(entropy: ScalarField, params: DynamicsParameters) -> ScalarField:
    """Velocity of internal time progression."""

    velocities = [1.0 / (1.0 + params.lambda_t * value) for value in entropy.values]
    return ScalarField(entropy.lattice, velocities)


# ---------------------------------------------------------------------------
# Evolution
# ---------------------------------------------------------------------------
def _forward_neighbours(lattice: Lattice, coord: Tuple[int, int]) -> Iterator[Tuple[int, int]]:
    """Yield deterministic subset of neighbours to avoid double counting edges."""

    x, y = coord
    for offset in [(x + 1, y), (x, y + 1)]:
        normalised = lattice.normalize(offset)
        if normalised is not None and normalised != coord:
            yield normalised


def advance_internal_time(
    internal_time: ScalarField, velocities: ScalarField, activation_threshold: float
) -> tuple[ScalarField, List[bool]]:
    """Advance internal time and return activation mask."""

    internal_time._ensure_same_lattice(velocities)
    updated: List[float] = []
    activated: List[bool] = []

    for tau, velocity in zip(internal_time.values, velocities.values):
        candidate = tau + velocity
        if candidate >= activation_threshold:
            activated.append(True)
            candidate -= activation_threshold
        else:
            activated.append(False)
        updated.append(candidate)

    return ScalarField(internal_time.lattice, updated), activated


def step(state: FieldState, params: DynamicsParameters) -> FieldState:
    """Deterministically advance the simulation by a single global tick."""

    state.ensure_alignment()
    lattice = state.lattice

    entropy = compute_entropy(state.energy, params)
    mu = chemical_potential(state.energy, params)
    mu_eff = effective_potential(mu)
    sigma = conductance(entropy, params)
    velocities = internal_time_velocity(entropy, params)
    next_internal_time, active_mask = advance_internal_time(
        state.internal_time, velocities, params.activation_threshold
    )

    delta = [0.0] * lattice.size

    for coord in lattice.positions():
        idx = state.energy.index(coord)
        if not active_mask[idx]:
            continue

        mu_here = mu_eff.values[idx]
        sigma_here = sigma.values[idx]
        for neighbour in _forward_neighbours(lattice, coord):
            n_idx = state.energy.index(neighbour)
            flux = params.kappa * sigma_here * (mu_here - mu_eff.values[n_idx])
            delta[idx] -= flux
            delta[n_idx] += flux

    updated_energy = [value + delta_value for value, delta_value in zip(state.energy.values, delta)]

    if params.energy_bounds is not None:
        lo, hi = params.energy_bounds
        updated_energy = [min(max(value, lo), hi) for value in updated_energy]

    energy_field = ScalarField(lattice, updated_energy)
    next_entropy = compute_entropy(energy_field, params)

    return FieldState(
        energy=energy_field,
        entropy=next_entropy,
        internal_time=next_internal_time,
    )


def evolve(initial_state: FieldState, params: DynamicsParameters, steps: int) -> List[FieldState]:
    """Run deterministic evolution for ``steps`` ticks and return snapshots."""

    history = [initial_state]
    current = initial_state
    for _ in range(steps):
        current = step(current, params)
        history.append(current)
    return history


__all__ = [
    "DynamicsParameters",
    "advance_internal_time",
    "chemical_potential",
    "conductance",
    "compute_entropy",
    "effective_potential",
    "evolve",
    "internal_time_velocity",
    "step",
]
