"""Torch backend (CPU/CUDA capable).

Notes:
- This backend is optional: `torch` is imported lazily.
- Currently supports `boundary="periodic"` only; other boundaries fall back to NumPy.
- The backend does **not** convert state between representations; it expects
  tensor-backed state and returns tensor-backed state.
"""

from __future__ import annotations

from core.entropy import DynamicsParameters
from core.fields import Lattice
from runtime.backends.base import BackendConfig
from runtime.state import DETMFieldState


def _require_torch():
    try:
        import torch  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError("Torch backend requested but torch is not installed") from exc
    return torch


class TorchBackend:
    def __init__(self, device: str = "cpu") -> None:
        self._torch = _require_torch()
        self.config = BackendConfig(name="torch", device=self._normalize_device(device))

    def _normalize_device(self, requested: str) -> str:
        torch = self._torch
        dev = str(requested).strip() or "cpu"
        if dev.startswith("cuda") and not torch.cuda.is_available():
            return "cpu"
        return dev

    def supports(self, lattice: Lattice) -> bool:
        return lattice.boundary == "periodic"

    def step(self, state: DETMFieldState, params: DynamicsParameters, n_ticks: int) -> DETMFieldState:
        state.ensure_alignment()
        lattice = state.lattice
        if lattice.boundary != "periodic":
            raise NotImplementedError("TorchBackend currently supports only periodic boundary")

        torch = self._torch
        if not isinstance(state.energy, torch.Tensor) or not isinstance(state.internal_time, torch.Tensor):
            raise TypeError("TorchBackend requires tensor-backed state")

        device = state.energy.device
        dtype = state.energy.dtype

        h, w = lattice.height, lattice.width
        e = state.energy.reshape(h, w).to(device=device, dtype=dtype)
        tau = state.internal_time.reshape(h, w).to(device=device, dtype=dtype)

        e0 = float(params.equilibrium_energy)
        beta = float(params.beta)
        gamma = float(params.gamma)
        kappa = float(params.kappa)
        alpha = float(params.alpha)
        lambda_t = float(params.lambda_t)
        activation_threshold = float(params.activation_threshold)

        def compute_entropy_t(energy: "torch.Tensor") -> "torch.Tensor":
            local_delta = energy - e0
            neighbourhood = (
                (torch.roll(energy, shifts=1, dims=1) - e0) ** 2
                + (torch.roll(energy, shifts=-1, dims=1) - e0) ** 2
                + (torch.roll(energy, shifts=1, dims=0) - e0) ** 2
                + (torch.roll(energy, shifts=-1, dims=0) - e0) ** 2
            )
            return beta * (local_delta**2) + gamma * neighbourhood

        current_e = e
        current_tau = tau
        for _ in range(max(0, n_ticks)):
            s = compute_entropy_t(current_e)

            mu = 2.0 * beta * (current_e - e0)
            mu_eff = mu - mu.mean()

            sigma = 1.0 / (1.0 + alpha * s)
            v = 1.0 / (1.0 + lambda_t * s)

            tau_next = current_tau + v
            active = tau_next >= activation_threshold
            tau_next = torch.where(active, tau_next - activation_threshold, tau_next)

            active_f = active.to(dtype)

            mu_r = torch.roll(mu_eff, shifts=-1, dims=1)
            mu_d = torch.roll(mu_eff, shifts=-1, dims=0)

            flux_r = kappa * sigma * (mu_eff - mu_r) * active_f
            flux_d = kappa * sigma * (mu_eff - mu_d) * active_f

            delta = -(flux_r + flux_d)
            delta = delta + torch.roll(flux_r, shifts=1, dims=1) + torch.roll(flux_d, shifts=1, dims=0)

            current_e = current_e + delta
            if params.energy_bounds is not None:
                lo, hi = params.energy_bounds
                current_e = torch.clamp(current_e, min=float(lo), max=float(hi))

            current_tau = tau_next

        # recompute entropy for returned state (matches core.entropy.step behaviour)
        final_entropy = compute_entropy_t(current_e)

        return DETMFieldState(
            lattice=lattice,
            energy=current_e,
            entropy=final_entropy,
            internal_time=current_tau,
        )
