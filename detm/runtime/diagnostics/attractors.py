"""Lightweight attractor detection and stability metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, List

import numpy as np

from detm.runtime.signature import digest_fields

if TYPE_CHECKING:
    from detm.runtime.state import DETMState


def _to_numpy(array) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None

    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


@dataclass(frozen=True)
class Attractor:
    position: tuple[int, int]
    strength: float
    stability_score: float
    period_estimate: float | None = None


@dataclass(frozen=True)
class StabilityReport:
    status: str
    delta: float


def detect_attractors(state_or_energy: np.ndarray | "DETMState", threshold: float = 0.8, top_k: int = 4) -> List[Attractor]:
    """Heuristic attractor detector based on local energy peaks.

    Accepts either a raw energy field (2D array) or a full DETMState.
    """

    if isinstance(state_or_energy, np.ndarray):
        energy = state_or_energy
    else:
        lattice = state_or_energy.lattice
        energy = _to_numpy(state_or_energy.field_state.energy).reshape(lattice.height, lattice.width)

    if energy.size == 0:
        return []

    peaks: List[Attractor] = []
    mean = float(energy.mean())
    std = float(energy.std()) + 1e-9
    scaled = (energy - mean) / std

    candidate_indices = np.argwhere(scaled > threshold)
    for y, x in candidate_indices:
        strength = float(scaled[y, x])
        peaks.append(Attractor(position=(int(x), int(y)), strength=strength, stability_score=min(1.0, strength / (threshold + 1e-9))))

    peaks.sort(key=lambda a: a.strength, reverse=True)
    return peaks[:top_k]


def stability_metrics(signatures: Iterable[np.ndarray]) -> StabilityReport:
    """Classify behaviour based on signature jitter."""

    vectors = [np.asarray(sig, dtype=float).reshape(-1) for sig in signatures]
    if len(vectors) < 2:
        return StabilityReport(status="unknown", delta=0.0)

    deltas = [float(np.linalg.norm(vectors[i] - vectors[i - 1])) for i in range(1, len(vectors))]
    mean_delta = float(np.mean(deltas))

    if mean_delta < 1e-3:
        status = "plateau"
    elif mean_delta < 1e-2:
        status = "small_oscillation"
    else:
        status = "progress"

    return StabilityReport(status=status, delta=mean_delta)


def signature_from_state(state) -> np.ndarray:
    import numpy as _np

    lattice = state.lattice
    energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width)
    entropy = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width)
    internal_time = _to_numpy(state.field_state.internal_time).reshape(lattice.height, lattice.width)
    return _np.asarray(digest_fields(energy, entropy, internal_time).vector, dtype=float)


__all__ = ["Attractor", "StabilityReport", "detect_attractors", "signature_from_state", "stability_metrics"]
