"""Compact digest utilities for DETM."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

import numpy as np

from detm.runtime.schemas import DETM_SIGNATURE_V1


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


def _is_torch_tensor(value: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(value, torch.Tensor)


def digest_fields(energy: np.ndarray, entropy: np.ndarray, internal_time: np.ndarray) -> DETMSignature:
    """NumPy implementation (reference)."""
    energy_desc = describe_field_from_array(energy)
    entropy_desc = describe_field_from_array(entropy)
    time_desc = describe_field_from_array(internal_time)

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


def _describe_field_from_torch(values) -> Dict[str, float]:
    import torch  # type: ignore

    flat = values.to(dtype=torch.float64).reshape(-1)
    mean = flat.mean()
    var = ((flat - mean) ** 2).mean()
    return {
        "minimum": float(flat.min().item()),
        "maximum": float(flat.max().item()),
        "mean": float(mean.item()),
        "variance": float(var.item()),
    }


def _center_of_mass_from_torch(energy) -> tuple[float, float]:
    import torch  # type: ignore

    h, w = int(energy.shape[0]), int(energy.shape[1])
    e = energy.to(dtype=torch.float64)
    total = e.sum() + 1e-12
    xs = torch.arange(w, device=e.device, dtype=torch.float64).reshape(1, w)
    ys = torch.arange(h, device=e.device, dtype=torch.float64).reshape(h, 1)
    cx = (e * xs).sum() / total
    cy = (e * ys).sum() / total
    return float(cx.item()), float(cy.item())


def project_field_plane_any(values: Any) -> Any:
    """Project an N-D field to the canonical 2D runtime plane.

    Until G-ND-02 lands, digest/readout contracts remain 2D. For tensors or
    arrays with leading axes, collapse those axes by mean and keep the trailing
    `(H, W)` plane.
    """

    if _is_torch_tensor(values):
        dims = int(values.ndim)
        if dims < 2:
            raise ValueError(f"field must be at least 2D, got ndim={dims}")
        if dims == 2:
            return values
        import torch  # type: ignore

        leading_axes = tuple(range(dims - 2))
        return values.to(dtype=torch.float64).mean(dim=leading_axes)

    array = np.asarray(values, dtype=float)
    if array.ndim < 2:
        raise ValueError(f"field must be at least 2D, got ndim={array.ndim}")
    if array.ndim == 2:
        return array
    leading_axes = tuple(range(array.ndim - 2))
    return array.mean(axis=leading_axes)


def digest_fields_any(energy: Any, entropy: Any, internal_time: Any) -> DETMSignature:
    """Compute signature without forcing a dense CPU copy of fields."""
    if _is_torch_tensor(energy) or _is_torch_tensor(entropy) or _is_torch_tensor(internal_time):
        energy_desc = _describe_field_from_torch(energy)
        entropy_desc = _describe_field_from_torch(entropy)
        time_desc = _describe_field_from_torch(internal_time)
        center_x, center_y = _center_of_mass_from_torch(energy)
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

    return digest_fields(np.asarray(energy), np.asarray(entropy), np.asarray(internal_time))


def describe_field_from_array(values: np.ndarray) -> Dict[str, float]:
    flat = values.astype(float).reshape(-1)
    moments = {
        "minimum": float(flat.min()),
        "maximum": float(flat.max()),
        "mean": float(flat.mean()),
        "variance": float(((flat - flat.mean()) ** 2).mean()),
    }
    return moments


def describe_field_any(values: Any) -> Dict[str, float]:
    if _is_torch_tensor(values):
        return _describe_field_from_torch(values)
    return describe_field_from_array(np.asarray(values))


__all__ = [
    "DETM_SIGNATURE_V1",
    "DETMSignature",
    "describe_field_any",
    "describe_field_from_array",
    "digest_fields",
    "digest_fields_any",
    "project_field_plane_any",
]
