from __future__ import annotations

import numpy as np
import pytest

from core.entropy import DynamicsParameters
from core.fields import Lattice
from runtime.backends import NumpyBackend, TorchBackend
from runtime.state import DETMFieldState


def test_torch_backend_matches_numpy_periodic():
    torch = pytest.importorskip("torch")

    lattice = Lattice(8, 6, boundary="periodic")
    params = DynamicsParameters(
        equilibrium_energy=0.4,
        beta=1.0,
        gamma=0.5,
        kappa=0.15,
        alpha=0.8,
        lambda_t=0.7,
        activation_threshold=0.5,
        energy_bounds=(0.0, 1.0),
    )

    rng = np.random.default_rng(123)
    energy_np = rng.random((lattice.height, lattice.width)).astype(float)
    zeros = np.zeros((lattice.height, lattice.width), dtype=float)

    numpy_backend = NumpyBackend()
    torch_backend = TorchBackend(device="cpu")

    numpy_state = DETMFieldState(lattice=lattice, energy=energy_np.copy(), entropy=zeros.copy(), internal_time=zeros.copy())
    energy_t = torch.tensor(energy_np, dtype=torch.float64)
    torch_state = DETMFieldState(
        lattice=lattice,
        energy=energy_t,
        entropy=torch.zeros_like(energy_t),
        internal_time=torch.zeros_like(energy_t),
    )

    numpy_out = numpy_backend.step(numpy_state, params, n_ticks=3)
    torch_out = torch_backend.step(torch_state, params, n_ticks=3)

    assert numpy_out.energy == pytest.approx(torch_out.energy.detach().cpu().numpy(), abs=1e-12, rel=0.0)
    assert numpy_out.internal_time == pytest.approx(torch_out.internal_time.detach().cpu().numpy(), abs=1e-12, rel=0.0)
