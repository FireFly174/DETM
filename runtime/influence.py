"""Influence structures and helpers for DETM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

from core.fields import Lattice
from runtime.state import DETMFieldState


@dataclass(frozen=True)
class DETMInfluence:
    """External influence applied during a step."""

    symbol_id: str
    amplitude: float = 1.0
    phase: float | None = None
    seed: int | None = None
    region: tuple[int, int, int] | None = None  # (cx, cy, radius)
    mask: np.ndarray | None = None
    duration: int | None = None
    external_features: np.ndarray | Dict[str, float] | None = None


@dataclass(frozen=True)
class InfluenceApplication:
    """Description of how an influence was applied."""

    symbol_id: str
    affected_fraction: float
    amplitude: float
    region: tuple[int, int, int] | None = None
    external_features: Dict[str, float] | None = None


def _resolve_mask(lattice: Lattice, influence: DETMInfluence) -> np.ndarray:
    if influence.mask is not None:
        mask = np.asarray(influence.mask, dtype=bool)
        if mask.shape != (lattice.height, lattice.width):
            raise ValueError("Influence mask shape does not match lattice")
        return mask

    cx, cy, radius = influence.region if influence.region is not None else (lattice.width // 2, lattice.height // 2, max(lattice.width, lattice.height) // 4)
    y, x = np.ogrid[: lattice.height, : lattice.width]
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def _is_torch_tensor(value: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(value, torch.Tensor)


def apply_influence(state: DETMFieldState, influence: DETMInfluence, rng: np.random.Generator) -> InfluenceApplication:
    """Apply influence to energy field in-place.

    The implementation is intentionally simple: it perturbs energy in a masked
    region. More sophisticated behaviour can be added without changing the
    public signature.
    """

    lattice = state.lattice
    mask = _resolve_mask(lattice, influence)
    amplitude = float(influence.amplitude)

    influence_rng = rng
    if influence.seed is not None:
        influence_rng = np.random.Generator(np.random.PCG64(int(influence.seed)))

    if _is_torch_tensor(state.energy):
        import torch  # type: ignore

        energy_t = state.energy
        device = energy_t.device
        dtype = energy_t.dtype

        mask_t = torch.from_numpy(mask).to(device=device)
        noise_np = influence_rng.normal(loc=0.0, scale=0.05, size=mask.shape).astype(np.float64)
        noise_t = torch.from_numpy(noise_np).to(device=device, dtype=dtype)

        updated = energy_t + amplitude * (1.0 + noise_t)
        updated = torch.clamp(updated, min=0.0, max=1.0)
        state.energy = torch.where(mask_t, updated, energy_t)
    else:
        energy = np.asarray(state.energy, dtype=float)
        noise = influence_rng.normal(loc=0.0, scale=0.05, size=energy.shape)
        energy[mask] = np.clip(energy[mask] + amplitude * (1.0 + noise[mask]), 0.0, 1.0)
        state.energy = energy

    affected_fraction = float(mask.mean()) if mask.size else 0.0
    external_features = None
    if isinstance(influence.external_features, dict):
        external_features = {str(k): float(v) for k, v in influence.external_features.items()}

    return InfluenceApplication(
        symbol_id=influence.symbol_id,
        affected_fraction=affected_fraction,
        amplitude=float(amplitude),
        region=influence.region,
        external_features=external_features,
    )


__all__ = ["DETMInfluence", "InfluenceApplication", "apply_influence"]
