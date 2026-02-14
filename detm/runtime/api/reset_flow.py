"""Reset-path helpers for runtime API."""

from __future__ import annotations

import numpy as np

from detm.runtime.api.helpers import backend_from_config as _backend_from_config
from detm.runtime.backends import NumpyBackend, TorchBackend
from detm.runtime.config import DETMConfig
from detm.runtime.state import DETMFieldState


def build_initial_field_state(*, config: DETMConfig, lattice, rng: np.random.Generator) -> DETMFieldState:
    energy_init = rng.normal(
        loc=config.dynamics.equilibrium_energy, scale=config.initial_noise, size=(lattice.height, lattice.width)
    )
    energy_init = np.clip(energy_init, 0.0, 1.0).astype(float, copy=False)

    backend = _backend_from_config(config, lattice)
    entropy_init = NumpyBackend._compute_entropy(energy_init, config.dynamics, boundary=lattice.boundary)

    if isinstance(backend, TorchBackend):
        torch = backend._torch
        device = torch.device(backend.config.device)
        dtype = torch.float64
        return DETMFieldState(
            lattice=lattice,
            energy=torch.tensor(energy_init, device=device, dtype=dtype),
            entropy=torch.tensor(entropy_init, device=device, dtype=dtype),
            internal_time=torch.zeros((lattice.height, lattice.width), device=device, dtype=dtype),
        )
    return DETMFieldState(
        lattice=lattice,
        energy=energy_init,
        entropy=entropy_init,
        internal_time=np.zeros((lattice.height, lattice.width), dtype=float),
    )


__all__ = ["build_initial_field_state"]
