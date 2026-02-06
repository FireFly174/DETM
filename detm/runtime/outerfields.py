"""OuterFields artifacts (GPU-friendly) for inter-level publish/subscribe.

This module is intentionally lightweight and optional: it must not require
materializing a full CPU copy of DETM fields, and it must not be required
for running L0 dynamics.

The canonical schema is described in:
`docs/rus/30_architecture/OuterFields_and_Subscriptions.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


def _is_torch_tensor(value: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(value, torch.Tensor)


def _roll(a: Any, shift: int, axis: int) -> Any:
    if _is_torch_tensor(a):
        import torch  # type: ignore

        return torch.roll(a, shifts=int(shift), dims=int(axis))
    return np.roll(np.asarray(a), shift=int(shift), axis=int(axis))


def _clip01(x: Any) -> Any:
    if _is_torch_tensor(x):
        import torch  # type: ignore

        return torch.clamp(x, 0.0, 1.0)
    return np.clip(np.asarray(x, dtype=float), 0.0, 1.0)


def _sqrt(x: Any) -> Any:
    if _is_torch_tensor(x):
        import torch  # type: ignore

        return torch.sqrt(x)
    return np.sqrt(np.asarray(x, dtype=float))


def _abs(x: Any) -> Any:
    if _is_torch_tensor(x):
        import torch  # type: ignore

        return torch.abs(x)
    return np.abs(np.asarray(x, dtype=float))


def _where(cond: Any, a: Any, b: Any) -> Any:
    if _is_torch_tensor(cond):
        import torch  # type: ignore

        return torch.where(cond, a, b)
    return np.where(np.asarray(cond), np.asarray(a), np.asarray(b))


def _central_grad_2d(field: Any) -> tuple[Any, Any]:
    dx = 0.5 * (_roll(field, -1, axis=1) - _roll(field, 1, axis=1))
    dy = 0.5 * (_roll(field, -1, axis=0) - _roll(field, 1, axis=0))
    return dx, dy


def _normalize_vector(dx: Any, dy: Any, eps: float = 1e-12) -> tuple[Any, Any, Any]:
    mag = _sqrt(dx * dx + dy * dy)
    if _is_torch_tensor(mag):
        import torch  # type: ignore

        mag_safe = torch.clamp(mag, min=float(eps))
    else:
        mag_safe = np.maximum(np.asarray(mag, dtype=float), float(eps))
    return dx / mag_safe, dy / mag_safe, mag


@dataclass(frozen=True)
class OuterFieldsV1:
    """Minimal V1 OuterFields channels (same topology as the target level)."""

    dir_x: Any
    dir_y: Any
    strength: Any
    stability: Any
    instability: Any
    boundary_activity: Any
    capacity_violation_density: Any
    meta: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dir_x": self.dir_x,
            "dir_y": self.dir_y,
            "strength": self.strength,
            "stability": self.stability,
            "instability": self.instability,
            "boundary_activity": self.boundary_activity,
            "capacity_violation_density": self.capacity_violation_density,
            "meta": dict(self.meta or {}),
        }


def compute_outerfields_v1(*, energy: Any, entropy: Any | None = None, internal_time: Any | None = None) -> OuterFieldsV1:
    """Compute a GPU-friendly OuterFieldsV1 artifact from dense fields.

    This is a best-effort default that is safe to run on either numpy or torch
    tensors. Higher-level code is expected to:
    - aggregate over `window_ticks`
    - downsample/remap to the target level topology
    - publish/store according to subscriptions
    """

    energy_f = energy
    dx, dy = _central_grad_2d(energy_f)
    dir_x, dir_y, grad_mag = _normalize_vector(dx, dy)

    # strength/boundary proxies: normalized gradient magnitude
    if _is_torch_tensor(grad_mag):
        import torch  # type: ignore

        gmax = torch.clamp(grad_mag.max(), min=1e-12)
        boundary = grad_mag / gmax
    else:
        g = np.asarray(grad_mag, dtype=float)
        gmax = max(float(np.max(g)), 1e-12)
        boundary = g / gmax

    boundary = _clip01(boundary)
    strength = boundary

    # validity proxy: overflow above 1 (should be zero for strict L0, but may be >0 on higher levels)
    if _is_torch_tensor(energy_f):
        import torch  # type: ignore

        overflow = torch.clamp(energy_f - 1.0, min=0.0)
        cap_violation = _clip01(overflow)
    else:
        e = np.asarray(energy_f, dtype=float)
        cap_violation = _clip01(np.maximum(0.0, e - 1.0))

    instability = _clip01(boundary + cap_violation)
    stability = _clip01(1.0 - instability)

    meta = {"schema": "OUTERFIELDS_V1"}
    if entropy is not None:
        meta["has_entropy"] = True
    if internal_time is not None:
        meta["has_internal_time"] = True

    return OuterFieldsV1(
        dir_x=dir_x,
        dir_y=dir_y,
        strength=strength,
        stability=stability,
        instability=instability,
        boundary_activity=boundary,
        capacity_violation_density=cap_violation,
        meta=meta,
    )


__all__ = ["OuterFieldsV1", "compute_outerfields_v1"]

