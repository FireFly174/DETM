"""State <-> payload conversion helpers for serialization."""

from __future__ import annotations

import io
from typing import Any, Callable

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.runtime.schemas import DETM_STATE_V1
from detm.runtime.state import DETMFieldState, DETMState


def _coerce_shape(raw_shape: Any) -> tuple[int, ...]:
    if raw_shape in (None, "", (), []):
        return ()
    shape = tuple(int(dim) for dim in raw_shape)
    if len(shape) < 2:
        raise ValueError("serialized shape must contain at least two axes")
    if any(int(dim) <= 0 for dim in shape):
        raise ValueError("serialized shape axes must be positive")
    return shape


def resolve_shape(payload: dict[str, Any], arrays: Any) -> tuple[int, ...]:
    lattice_info = payload.get("lattice")
    if isinstance(lattice_info, dict):
        shape = _coerce_shape(lattice_info.get("shape"))
        if shape:
            return shape

    shape = _coerce_shape(payload.get("shape"))
    if shape:
        return shape

    energy = np.asarray(arrays["energy"], dtype=float)
    if energy.ndim < 2:
        raise ValueError(f"serialized energy must be at least 2D, got shape={energy.shape}")
    return tuple(int(dim) for dim in energy.shape)


def resolve_lattice(payload: dict[str, Any], arrays: Any) -> Lattice:
    lattice_info = payload.get("lattice")
    boundary = "periodic"
    if isinstance(lattice_info, dict):
        boundary = str(lattice_info.get("boundary", "periodic"))
        shape = _coerce_shape(lattice_info.get("shape"))
        if shape:
            return Lattice(width=int(shape[-1]), height=int(shape[-2]), boundary=boundary)
        width_raw = lattice_info.get("width")
        height_raw = lattice_info.get("height")
        if width_raw is not None and height_raw is not None:
            return Lattice(width=int(width_raw), height=int(height_raw), boundary=boundary)

    shape = resolve_shape(payload, arrays)
    height, width = int(shape[-2]), int(shape[-1])
    return Lattice(width=width, height=height, boundary="periodic")


def build_state_from_payload(payload: dict[str, Any]) -> DETMState:
    with np.load(io.BytesIO(payload["arrays"])) as arrays:
        shape = resolve_shape(payload, arrays)
        lattice = resolve_lattice(payload, arrays)
        field_state = DETMFieldState(
            lattice=lattice,
            energy=arrays["energy"].astype(float, copy=False),
            entropy=arrays["entropy"].astype(float, copy=False),
            internal_time=arrays["internal_time"].astype(float, copy=False),
            shape=shape,
        )

    return DETMState(
        state_version=DETM_STATE_V1,
        field_state=field_state,
        step_count=int(payload.get("step_count", 0)),
        rng_state=dict(payload.get("rng_state", {})) if isinstance(payload.get("rng_state", {}), dict) else {},
        config=payload.get("config"),
        dynamics=DynamicsParameters(**dict(payload.get("dynamics", {})))
        if isinstance(payload.get("dynamics", {}), dict)
        else DynamicsParameters(),
    )


def state_to_payload(
    state: DETMState,
    *,
    to_numpy: Callable[[Any], np.ndarray],
) -> dict[str, Any]:
    lattice = state.lattice
    shape = tuple(int(dim) for dim in state.shape)
    energy = to_numpy(state.field_state.energy).astype(float, copy=False)
    entropy = to_numpy(state.field_state.entropy).astype(float, copy=False)
    internal_time = to_numpy(state.field_state.internal_time).astype(float, copy=False)

    buffer = io.BytesIO()
    np.savez_compressed(buffer, energy=energy, entropy=entropy, internal_time=internal_time)
    return {
        "state_version": DETM_STATE_V1,
        "step_count": int(state.step_count),
        "rng_state": dict(state.rng_state),
        "config": state.config,
        "dynamics": state.dynamics.__dict__,
        "shape": list(shape),
        "lattice": {"width": lattice.width, "height": lattice.height, "boundary": lattice.boundary, "shape": list(shape)},
        "arrays": buffer.getvalue(),
    }


__all__ = ["build_state_from_payload", "resolve_lattice", "state_to_payload"]
