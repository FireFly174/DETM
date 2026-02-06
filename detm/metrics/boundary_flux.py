"""Boundary-flux metrics for trace logging.

Goal: make the "fixed point on the boundary" hypothesis testable from
`trace.jsonl` alone by logging a compact time series proxy for `Φ_boundary(t)`.

Important: this must stay lightweight and avoid forcing dense CPU copies. When
the simulation runs on torch/GPU, computations happen on-device and only final
scalars are moved to CPU via `.item()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

from detm.metrics.base import MetricContext, MetricPlugin


def _is_torch_tensor(x: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(x, torch.Tensor)


def _roll(x: Any, shift: int, axis: int) -> Any:
    if _is_torch_tensor(x):
        import torch  # type: ignore

        return torch.roll(x, shifts=int(shift), dims=int(axis))
    return np.roll(np.asarray(x), shift=int(shift), axis=int(axis))


def _sqrt(x: Any) -> Any:
    if _is_torch_tensor(x):
        import torch  # type: ignore

        return torch.sqrt(x)
    return np.sqrt(np.asarray(x))


def _abs(x: Any) -> Any:
    if _is_torch_tensor(x):
        import torch  # type: ignore

        return torch.abs(x)
    return np.abs(np.asarray(x))


def _mean(x: Any) -> float:
    if _is_torch_tensor(x):
        return float(x.mean().item())
    return float(np.asarray(x, dtype=float).mean())


def _sum(x: Any) -> float:
    if _is_torch_tensor(x):
        return float(x.sum().item())
    return float(np.asarray(x, dtype=float).sum())


def _rms(x: Any) -> float:
    if _is_torch_tensor(x):
        return float((_sqrt((x * x).mean())).item())
    arr = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(arr * arr)))

def _std(x: Any) -> float:
    if _is_torch_tensor(x):
        return float(x.std(unbiased=False).item())
    return float(np.asarray(x, dtype=float).std())


def _central_diffs(E: Any) -> tuple[Any, Any]:
    """Return (Jx, Jy) proxy as central differences of E."""

    Jx = 0.5 * (_roll(E, -1, 0) - _roll(E, +1, 0))
    Jy = 0.5 * (_roll(E, -1, 1) - _roll(E, +1, 1))
    return Jx, Jy


@dataclass(frozen=True)
class BoundaryFluxMetrics(MetricPlugin):
    """Log compact boundary flux readouts.

    This plugin is intentionally "outer boundary only" for now. For internal
    object boundaries (masks) use `fields_hist.npz` + offline analyzers (or pass
    a mask-aware plugin later).
    """

    name: str = "boundary_flux"

    def compute(self, ctx: MetricContext) -> Dict[str, Any]:
        cfg = ctx.state.config or {}
        if not bool(cfg.get("trace_boundary_flux", False)):
            return {"enabled": False}

        state = ctx.state
        lattice = state.lattice
        E = state.field_state.energy.reshape(lattice.height, lattice.width)

        Jx, Jy = _central_diffs(E)
        Jmag = _sqrt(Jx * Jx + Jy * Jy)

        # Outer boundary normal components (signed net + absolute throughput).
        # Conventions: axis=0 is x, axis=1 is y.
        top = -Jx[0, :]
        bottom = Jx[-1, :]
        left = -Jy[:, 0]
        right = Jy[:, -1]
        phi_net = _sum(top) + _sum(bottom) + _sum(left) + _sum(right)
        phi_abs = _sum(_abs(top)) + _sum(_abs(bottom)) + _sum(_abs(left)) + _sum(_abs(right))

        # Boundary activity proxy: |∇E| on the outer ring (sum/mean).
        ring_sum = _sum(Jmag[0, :]) + _sum(Jmag[-1, :]) + _sum(Jmag[1:-1, 0]) + _sum(Jmag[1:-1, -1])
        ring_count = int(2 * lattice.width + 2 * (lattice.height - 2))
        ring_mean = float(ring_sum / max(1, ring_count))

        # A "flow entropy" surrogate is spectral, so we log time series here and compute offline.
        # Still, we can log a quick spatial dispersion proxy.
        return {
            "enabled": True,
            "phi_outer_normal_net": float(phi_net),
            "phi_outer_normal_abs": float(phi_abs),
            "grad_mag_mean": float(_mean(Jmag)),
            "grad_mag_ring_mean": float(ring_mean),
            "grad_mag_ring_sum": float(ring_sum),
            "grad_mag_std": float(_std(Jmag)),
            # Laplacian(E) RMS as divergence(J) RMS (since J ≈ ∇E here)
            "divJ_rms": float(_rms(0.5 * (_roll(Jx, -1, 0) - _roll(Jx, +1, 0)) + 0.5 * (_roll(Jy, -1, 1) - _roll(Jy, +1, 1)))),
        }


__all__ = ["BoundaryFluxMetrics"]
