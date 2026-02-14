"""Influence contracts for DETM runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


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
    dynamics_overrides: Dict[str, float] | None = None


@dataclass(frozen=True)
class InfluenceApplication:
    """Description of how an influence was applied."""

    symbol_id: str
    affected_fraction: float
    amplitude: float
    region: tuple[int, int, int] | None = None
    external_features: Dict[str, float] | None = None


__all__ = ["DETMInfluence", "InfluenceApplication"]
