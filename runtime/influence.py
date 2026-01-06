"""Influence structures and helpers for DETM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

import numpy as np

from core.fields import FieldState, Lattice


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


def apply_influence(state: FieldState, influence: DETMInfluence, rng: np.random.Generator) -> InfluenceApplication:
    """Apply influence to energy field in-place.

    The implementation is intentionally simple: it perturbs energy in a masked
    region. More sophisticated behaviour can be added without changing the
    public signature.
    """

    lattice = state.lattice
    mask = _resolve_mask(lattice, influence)
    energy = np.asarray(state.energy.values, dtype=float).reshape(lattice.height, lattice.width)

    amplitude = influence.amplitude
    if influence.seed is not None:
        rng = np.random.default_rng(influence.seed)
    noise = rng.normal(loc=0.0, scale=0.05, size=energy.shape)
    energy[mask] = np.clip(energy[mask] + amplitude * (1.0 + noise[mask]), 0.0, 1.0)

    state.energy.values = energy.reshape(-1).tolist()

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
