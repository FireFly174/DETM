"""Mask and tensor helpers for influence application."""

from __future__ import annotations

from typing import Any

import numpy as np

from detm.core.fields import Lattice
from detm.runtime.influence.contracts import DETMInfluence


def resolve_mask(lattice: Lattice, influence: DETMInfluence, field_shape: tuple[int, ...] | None = None) -> np.ndarray:
    if influence.mask is not None:
        mask = np.asarray(influence.mask, dtype=bool)
        if field_shape is not None and mask.shape == tuple(int(dim) for dim in field_shape):
            return mask
        if mask.shape != (lattice.height, lattice.width):
            raise ValueError("Influence mask shape does not match lattice")
        return mask

    sid = str(influence.symbol_id or "")
    h, w = lattice.height, lattice.width
    y, x = np.ogrid[:h, :w]

    if sid == "noise_burst" and influence.region is None:
        return np.ones((h, w), dtype=bool)

    cx, cy, radius = influence.region if influence.region is not None else (w // 2, h // 2, max(w, h) // 4)
    cx = int(cx)
    cy = int(cy)
    radius = max(0, int(radius))
    dist2 = (x - cx) ** 2 + (y - cy) ** 2

    if sid == "ring":
        r_out = max(1, radius)
        r_in = max(0, int(round(r_out * 0.6)))
        return (dist2 <= r_out**2) & (dist2 >= r_in**2)

    if sid == "stripe":
        # A deterministic stripe mask. `phase` selects orientation when provided:
        # phase < 0.5 => vertical, else horizontal.
        orientation = "vertical"
        if influence.phase is not None:
            try:
                orientation = "vertical" if float(influence.phase) < 0.5 else "horizontal"
            except Exception:
                orientation = "vertical"
        stripe_half = max(1, int(round(radius if influence.region is not None else max(1, w // 10))))
        if orientation == "horizontal":
            mask = np.abs(y - cy) <= stripe_half
            return np.broadcast_to(mask, (h, w))
        mask = np.abs(x - cx) <= stripe_half
        return np.broadcast_to(mask, (h, w))

    if sid == "focus":
        # Smaller, tighter spot than a default pulse.
        r = max(1, int(round(radius * 0.5))) if influence.region is not None else max(1, max(w, h) // 8)
        return dist2 <= r**2

    if sid == "disturb":
        # Checker-like pattern to differ visually from `pulse`.
        base = dist2 <= max(1, radius) ** 2
        return base & (((x + y) % 2) == 0)

    return dist2 <= max(1, radius) ** 2


def is_torch_tensor(value: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(value, torch.Tensor)


__all__ = ["is_torch_tensor", "resolve_mask"]
