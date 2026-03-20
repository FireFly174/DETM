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
        if energy.ndim > 2:
            h, w = int(energy.shape[-2]), int(energy.shape[-1])
            flat_energy = energy.reshape(-1, h, w)
            flat_entropy = np.stack(
                [
                    NumpyBackend._compute_entropy(plane, params, boundary=boundary)
                    for plane in flat_energy
                ],
                axis=0,
            )
            return flat_entropy.reshape(energy.shape)

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
        shape = tuple(int(dim) for dim in energy.shape)

        e0 = float(params.equilibrium_energy)
        beta = float(params.beta)
        kappa = float(params.kappa)
        alpha = float(params.alpha)
        lambda_t = float(params.lambda_t)
        activation_threshold = float(params.activation_threshold)
        h, w = int(lattice.height), int(lattice.width)
        flat_energy = energy.reshape(-1, h, w)
        flat_tau = tau.reshape(-1, h, w)
        next_energy: list[np.ndarray] = []
        next_tau: list[np.ndarray] = []

        for plane_energy, plane_tau in zip(flat_energy, flat_tau):
            current_energy = plane_energy.astype(float, copy=True)
            current_tau = plane_tau.astype(float, copy=True)

            for _ in range(max(0, n_ticks)):
                entropy = self._compute_entropy(current_energy, params, boundary=boundary)

                mu = 2.0 * beta * (current_energy - e0)
                mu_eff = mu - mu.mean()

                sigma = 1.0 / (1.0 + alpha * entropy)
                v = 1.0 / (1.0 + lambda_t * entropy)

                tau_next = current_tau + v
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
                    flux_r = np.zeros_like(current_energy)
                    flux_d = np.zeros_like(current_energy)

                    flux_r[:, :-1] = (
                        kappa * sigma[:, :-1] * (mu_eff[:, :-1] - mu_eff[:, 1:]) * active_f[:, :-1]
                    )
                    flux_d[:-1, :] = (
                        kappa * sigma[:-1, :] * (mu_eff[:-1, :] - mu_eff[1:, :]) * active_f[:-1, :]
                    )

                    delta = -(flux_r + flux_d)
                    delta[:, 1:] += flux_r[:, :-1]
                    delta[1:, :] += flux_d[:-1, :]

                current_energy = current_energy + delta
                if params.energy_bounds is not None:
                    lo, hi = params.energy_bounds
                    current_energy = np.clip(current_energy, float(lo), float(hi))

                current_tau = tau_next

            next_energy.append(current_energy)
            next_tau.append(current_tau)

        energy_out = np.stack(next_energy, axis=0).reshape(shape)
        tau_out = np.stack(next_tau, axis=0).reshape(shape)
        entropy_out = self._compute_entropy(energy_out, params, boundary=boundary)
        return DETMFieldState(
            lattice=lattice,
            energy=energy_out,
            entropy=entropy_out,
            internal_time=tau_out,
            shape=shape,
        )
