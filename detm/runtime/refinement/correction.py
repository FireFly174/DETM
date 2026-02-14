"""Correction candidate scoring and selection for refinement runtime."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.refinement.geometry import neighbor_average


def candidate_score(
    *,
    candidate_energy: np.ndarray,
    candidate_entropy_roi: float,
    mask: np.ndarray,
    lo: float,
    hi: float,
) -> tuple[int, float]:
    overflow_after = (candidate_energy < float(lo)) | (candidate_energy > float(hi))
    overflow_count = int(overflow_after[mask].sum())
    return int(overflow_count), float(candidate_entropy_roi)


def select_correction(
    *,
    energy_before: np.ndarray,
    entropy_before: np.ndarray,
    mask: np.ndarray,
    boundary: str,
    dynamics: DynamicsParameters,
    lo: float,
    hi: float,
    blend_candidates: tuple[float, ...],
) -> Dict[str, Any] | None:
    entropy_before_roi = float(entropy_before[mask].mean())
    overflow_before = int((((energy_before < lo) | (energy_before > hi))[mask]).sum())
    baseline_score = (overflow_before, float(entropy_before_roi))

    neighbor = neighbor_average(energy_before, boundary=boundary)
    best: Dict[str, Any] | None = None
    for blend in blend_candidates:
        candidate = np.asarray(energy_before, dtype=float, copy=True)
        candidate[mask] = (1.0 - float(blend)) * energy_before[mask] + float(blend) * neighbor[mask]
        candidate[mask] = np.clip(candidate[mask], float(lo), float(hi))

        candidate_entropy = NumpyBackend._compute_entropy(candidate, dynamics, boundary=boundary)
        candidate_entropy_roi = float(candidate_entropy[mask].mean())
        score = candidate_score(
            candidate_energy=candidate,
            candidate_entropy_roi=float(candidate_entropy_roi),
            mask=mask,
            lo=float(lo),
            hi=float(hi),
        )
        if score >= baseline_score:
            continue
        if best is None or score < best["score"]:
            best = {
                "blend": float(blend),
                "energy": candidate,
                "entropy": candidate_entropy,
                "entropy_roi": float(candidate_entropy_roi),
                "score": score,
            }

    if best is None:
        return None
    return {
        "blend": float(best["blend"]),
        "energy": best["energy"],
        "entropy": best["entropy"],
        "entropy_before_roi": float(entropy_before_roi),
        "entropy_after_roi": float(best["entropy_roi"]),
        "overflow_before_roi": int(baseline_score[0]),
        "overflow_after_roi": int(best["score"][0]),
    }


__all__ = ["candidate_score", "select_correction"]
