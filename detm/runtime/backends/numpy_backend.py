"""NumPy backend (CPU reference).

This backend keeps the state as NumPy arrays and performs deterministic updates
without converting the state into other representations.
"""

from __future__ import annotations

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.runtime.backends.base import BackendConfig
from detm.runtime.state import DETMFieldState


class NumpyBackend:
    def __init__(self) -> None:
        self.config = BackendConfig(name="numpy", device="cpu")

    def supports(self, _lattice: Lattice) -> bool:
        return True

    @staticmethod
    def _compute_entropy(energy: np.ndarray, params: DynamicsParameters, boundary: str) -> np.ndarray:
        e0 = float(params.equilibrium_energy)
        local_delta = energy - e0

        if boundary == "periodic":
            neighbourhood = (
                (np.roll(energy, shift=1, axis=1) - e0) ** 2
                + (np.roll(energy, shift=-1, axis=1) - e0) ** 2
                + (np.roll(energy, shift=1, axis=0) - e0) ** 2
                + (np.roll(energy, shift=-1, axis=0) - e0) ** 2
            )
        elif boundary == "open":
            neighbourhood = np.zeros_like(energy)
            neighbourhood[:, 1:] += (energy[:, :-1] - e0) ** 2
            neighbourhood[:, :-1] += (energy[:, 1:] - e0) ** 2
            neighbourhood[1:, :] += (energy[:-1, :] - e0) ** 2
            neighbourhood[:-1, :] += (energy[1:, :] - e0) ** 2
        else:
            raise ValueError(f"Unsupported boundary: {boundary}")

        return float(params.beta) * (local_delta**2) + float(params.gamma) * neighbourhood

    def step(self, state: DETMFieldState, params: DynamicsParameters, n_ticks: int) -> DETMFieldState:
        state.ensure_alignment()
        lattice = state.lattice
        boundary = lattice.boundary

        energy = np.asarray(state.energy, dtype=float)
        tau = np.asarray(state.internal_time, dtype=float)

        e0 = float(params.equilibrium_energy)
        beta = float(params.beta)
        kappa = float(params.kappa)
        alpha = float(params.alpha)
        lambda_t = float(params.lambda_t)
        activation_threshold = float(params.activation_threshold)

        for _ in range(max(0, n_ticks)):
            entropy = self._compute_entropy(energy, params, boundary=boundary)

            mu = 2.0 * beta * (energy - e0)
            mu_eff = mu - mu.mean()

            sigma = 1.0 / (1.0 + alpha * entropy)
            v = 1.0 / (1.0 + lambda_t * entropy)

            tau_next = tau + v
            active = tau_next >= activation_threshold
            tau_next = np.where(active, tau_next - activation_threshold, tau_next)

            active_f = active.astype(float)

            if boundary == "periodic":
                mu_r = np.roll(mu_eff, shift=-1, axis=1)
                mu_d = np.roll(mu_eff, shift=-1, axis=0)

                flux_r = kappa * sigma * (mu_eff - mu_r) * active_f
                flux_d = kappa * sigma * (mu_eff - mu_d) * active_f

                delta = -(flux_r + flux_d)
                delta = delta + np.roll(flux_r, shift=1, axis=1) + np.roll(flux_d, shift=1, axis=0)
            else:
                flux_r = np.zeros_like(energy)
                flux_d = np.zeros_like(energy)

                flux_r[:, :-1] = kappa * sigma[:, :-1] * (mu_eff[:, :-1] - mu_eff[:, 1:]) * active_f[:, :-1]
                flux_d[:-1, :] = kappa * sigma[:-1, :] * (mu_eff[:-1, :] - mu_eff[1:, :]) * active_f[:-1, :]

                delta = -(flux_r + flux_d)
                delta[:, 1:] += flux_r[:, :-1]
                delta[1:, :] += flux_d[:-1, :]

            energy = energy + delta
            if params.energy_bounds is not None:
                lo, hi = params.energy_bounds
                energy = np.clip(energy, float(lo), float(hi))

            tau = tau_next

        entropy = self._compute_entropy(energy, params, boundary=boundary)
        return DETMFieldState(lattice=lattice, energy=energy, entropy=entropy, internal_time=tau)
