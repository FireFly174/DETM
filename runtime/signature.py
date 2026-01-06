"""Compact digest utilities for DETM."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List

import numpy as np

from core.invariants import describe_field
from runtime.schemas import DETM_SIGNATURE_V1


@dataclass(frozen=True)
class DETMSignature:
    version: str
    vector: List[float]
    summary: Dict[str, float]

    def as_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["vector"] = list(self.vector)
        data["summary"] = dict(self.summary)
        return data


def digest_fields(energy: np.ndarray, entropy: np.ndarray, internal_time: np.ndarray) -> DETMSignature:
    energy_desc = describe_field_from_array(energy)
    entropy_desc = describe_field_from_array(entropy)
    time_desc = describe_field_from_array(internal_time)

    # basic spatial moments
    coords_x, coords_y = np.meshgrid(np.arange(energy.shape[1]), np.arange(energy.shape[0]))
    total_energy = float(energy.sum()) + 1e-12
    center_x = float((coords_x * energy).sum() / total_energy)
    center_y = float((coords_y * energy).sum() / total_energy)

    vector = [
        energy_desc["mean"],
        energy_desc["variance"],
        energy_desc["minimum"],
        energy_desc["maximum"],
        entropy_desc["mean"],
        entropy_desc["variance"],
        time_desc["mean"],
        center_x,
        center_y,
    ]

    summary = {
        "energy_mean": energy_desc["mean"],
        "energy_var": energy_desc["variance"],
        "entropy_mean": entropy_desc["mean"],
        "internal_time_mean": time_desc["mean"],
        "center_of_mass_x": center_x,
        "center_of_mass_y": center_y,
    }

    return DETMSignature(version=DETM_SIGNATURE_V1, vector=vector, summary=summary)


def describe_field_from_array(values: np.ndarray) -> Dict[str, float]:
    flat = values.astype(float).reshape(-1)
    moments = {
        "minimum": float(flat.min()),
        "maximum": float(flat.max()),
        "mean": float(flat.mean()),
        "variance": float(((flat - flat.mean()) ** 2).mean()),
    }
    return moments


__all__ = ["DETM_SIGNATURE_V1", "DETMSignature", "describe_field_from_array", "digest_fields"]
