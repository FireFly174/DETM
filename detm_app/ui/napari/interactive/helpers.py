"""Helper functions for napari interactive controls."""

from __future__ import annotations

from itertools import product
from typing import Any

import numpy as np

MAX_EXPLICIT_PROJECTION_PLANES = 64


def central_grad(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    dx = 0.5 * (np.roll(arr, -1, axis=1) - np.roll(arr, 1, axis=1))
    dy = 0.5 * (np.roll(arr, -1, axis=0) - np.roll(arr, 1, axis=0))
    return dx, dy


def build_quiver_vectors(field: np.ndarray, *, step: int, scale: float) -> np.ndarray:
    arr = np.asarray(field, dtype=np.float32)
    if arr.ndim != 2:
        return np.zeros((0, 2, 2), dtype=np.float32)
    height, width = arr.shape
    dx, dy = central_grad(arr)
    mag = np.hypot(dx, dy)
    mmax = float(np.max(mag)) if mag.size else 0.0
    if (not np.isfinite(mmax)) or mmax <= 1e-12:
        return np.zeros((0, 2, 2), dtype=np.float32)

    q_step = max(1, int(step))
    q_scale = max(0.0, float(scale))
    out: list[np.ndarray] = []
    for y in range(0, int(height), q_step):
        for x in range(0, int(width), q_step):
            vx = float(dx[y, x]) / mmax
            vy = float(dy[y, x]) / mmax
            origin = np.array([float(y), float(x)], dtype=np.float32)
            delta = np.array([vy * q_scale, vx * q_scale], dtype=np.float32)
            out.append(np.stack((origin, delta), axis=0))
    if not out:
        return np.zeros((0, 2, 2), dtype=np.float32)
    return np.stack(out, axis=0).astype(np.float32, copy=False)


def resolve_influence_policy(*, policy: str, selected_mode: str, duration_steps: int) -> tuple[str, int]:
    mode = str(selected_mode or "").strip().lower()
    pol = str(policy or "").strip().lower()
    dur = max(0, int(duration_steps))
    if mode in {"", "none", "(none)"}:
        return ("none", 0)
    if pol in {"off", "disabled", "none"}:
        return ("none", 0)
    if pol in {"pulse", "pulse_once", "oneshot"}:
        return (mode, max(1, dur))
    return (mode, 0)


def to_int(text: str, default: int) -> int:
    try:
        return int(str(text).strip())
    except Exception:
        return int(default)


def to_float(text: str, default: float) -> float:
    try:
        return float(str(text).strip())
    except Exception:
        return float(default)


def format_projection_plane_label(plane_index: tuple[int, ...] | None) -> str:
    if plane_index is None:
        return "mean"
    return "plane[" + ",".join(str(int(value)) for value in tuple(plane_index)) + "]"


def build_projection_plane_options(shape: tuple[int, ...] | list[int]) -> list[tuple[str, tuple[int, ...] | None]]:
    dims = tuple(int(dim) for dim in tuple(shape))
    if len(dims) <= 2:
        return [("native", None)]
    leading_shape = dims[:-2]
    total_planes = int(np.prod(leading_shape, dtype=np.int64)) if len(leading_shape) > 0 else 1
    options: list[tuple[str, tuple[int, ...] | None]] = [("mean projection", None)]
    if total_planes > int(MAX_EXPLICIT_PROJECTION_PLANES):
        return options
    for plane_index in product(*[range(int(dim)) for dim in leading_shape]):
        plane_tuple = tuple(int(value) for value in plane_index)
        options.append((format_projection_plane_label(plane_tuple), plane_tuple))
    return options


__all__ = [
    "build_quiver_vectors",
    "build_projection_plane_options",
    "format_projection_plane_label",
    "resolve_influence_policy",
    "to_float",
    "to_int",
]
