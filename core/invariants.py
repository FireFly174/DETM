"""Helpers for computing coarse invariants from :mod:`core.fields` data.

The legacy visualiser (`legacy/viz/visualizer.py`) rendered both raw fields
(`E`, gradients, histograms) and aggregated invariants such as global extrema
or radial profiles (see `legacy/analyze_fields.py`).  The utilities here keep
that analysis layer thin and reusable for the newer ``FieldState`` structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import List, Mapping, Sequence, Tuple

from .fields import Coordinate, FieldState, ScalarField


@dataclass(frozen=True)
class FieldMoments:
    """Compact description of a scalar field."""

    minimum: float
    maximum: float
    mean: float
    variance: float


@dataclass(frozen=True)
class InvariantSnapshot:
    """Global invariants tracked for a single ``FieldState`` tick."""

    energy: FieldMoments
    entropy: FieldMoments
    internal_time: FieldMoments

    @property
    def as_dict(self) -> Mapping[str, float]:
        """Flattened mapping useful for logging or plotting."""

        return {
            "energy_min": self.energy.minimum,
            "energy_max": self.energy.maximum,
            "energy_mean": self.energy.mean,
            "energy_var": self.energy.variance,
            "entropy_mean": self.entropy.mean,
            "internal_time_mean": self.internal_time.mean,
        }


def describe_field(field: ScalarField) -> FieldMoments:
    """Return basic statistics for the provided scalar field."""

    values = [float(v) for v in field.values]
    if not values:
        raise ValueError("ScalarField contains no values")

    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return FieldMoments(
        minimum=min(values),
        maximum=max(values),
        mean=mean,
        variance=variance,
    )


def describe_state(state: FieldState) -> InvariantSnapshot:
    """Compute invariants for all fields in the state."""

    state.ensure_alignment()
    return InvariantSnapshot(
        energy=describe_field(state.energy),
        entropy=describe_field(state.entropy),
        internal_time=describe_field(state.internal_time),
    )


def collect_series(history: Sequence[FieldState]) -> Mapping[str, List[float]]:
    """Return per-step invariant time series from a trajectory of states."""

    energy_mean: List[float] = []
    energy_min: List[float] = []
    energy_max: List[float] = []
    entropy_mean: List[float] = []
    internal_time_mean: List[float] = []

    for state in history:
        snapshot = describe_state(state)
        energy_mean.append(snapshot.energy.mean)
        energy_min.append(snapshot.energy.minimum)
        energy_max.append(snapshot.energy.maximum)
        entropy_mean.append(snapshot.entropy.mean)
        internal_time_mean.append(snapshot.internal_time.mean)

    return {
        "energy_mean": energy_mean,
        "energy_min": energy_min,
        "energy_max": energy_max,
        "entropy_mean": entropy_mean,
        "internal_time_mean": internal_time_mean,
    }


def radial_profile(
    field: ScalarField, center: Coordinate | None = None, r_max: int | None = None
) -> Tuple[List[float], List[float]]:
    """Average field values across integer radii measured from ``center``."""

    lattice = field.lattice
    width, height = lattice.width, lattice.height

    if center is None:
        center = (width // 2, height // 2)
    cx, cy = center

    radii: List[List[int]] = []
    max_radius = 0
    for y in range(height):
        row: List[int] = []
        for x in range(width):
            radius = int(sqrt((x - cx) ** 2 + (y - cy) ** 2))
            row.append(radius)
            if radius > max_radius:
                max_radius = radius
        radii.append(row)

    if r_max is None:
        r_max = max_radius

    totals = [0.0 for _ in range(r_max + 1)]
    counts = [0 for _ in range(r_max + 1)]

    for y in range(height):
        for x in range(width):
            radius = radii[y][x]
            if radius > r_max:
                continue
            idx = y * width + x
            totals[radius] += float(field.values[idx])
            counts[radius] += 1

    profile = [
        (totals[r] / counts[r]) if counts[r] > 0 else float("nan") for r in range(r_max + 1)
    ]
    radii_vector = [float(r) for r in range(r_max + 1)]
    return profile, radii_vector


__all__ = [
    "FieldMoments",
    "InvariantSnapshot",
    "collect_series",
    "describe_field",
    "describe_state",
    "radial_profile",
]
