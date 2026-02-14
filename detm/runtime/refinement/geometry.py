"""Geometry helpers for refinement ROI and neighborhood operations."""

from __future__ import annotations

import numpy as np


def roi_mask(shape: tuple[int, int], *, center_y: int, center_x: int, radius: int, boundary: str) -> np.ndarray:
    h, w = int(shape[0]), int(shape[1])
    yy = np.arange(h, dtype=np.int32).reshape(h, 1)
    xx = np.arange(w, dtype=np.int32).reshape(1, w)
    if str(boundary) == "periodic":
        dy = np.minimum((yy - center_y) % h, (center_y - yy) % h)
        dx = np.minimum((xx - center_x) % w, (center_x - xx) % w)
    else:
        dy = np.abs(yy - center_y)
        dx = np.abs(xx - center_x)
    return (dy * dy + dx * dx) <= int(radius) * int(radius)


def neighbor_average(energy: np.ndarray, *, boundary: str) -> np.ndarray:
    if str(boundary) == "periodic":
        return (
            np.roll(energy, shift=1, axis=0)
            + np.roll(energy, shift=-1, axis=0)
            + np.roll(energy, shift=1, axis=1)
            + np.roll(energy, shift=-1, axis=1)
        ) / 4.0
    padded = np.pad(energy, ((1, 1), (1, 1)), mode="edge")
    up = padded[:-2, 1:-1]
    down = padded[2:, 1:-1]
    left = padded[1:-1, :-2]
    right = padded[1:-1, 2:]
    return (up + down + left + right) / 4.0


__all__ = ["neighbor_average", "roi_mask"]
