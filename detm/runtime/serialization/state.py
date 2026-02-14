"""State <-> payload conversion helpers for serialization."""

from __future__ import annotations

import io
from typing import Any, Callable

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.runtime.schemas import DETM_STATE_V1
from detm.runtime.state import DETMFieldState, DETMState


def resolve_lattice(payload: dict[str, Any], arrays: Any) -> Lattice:
    lattice_info = payload.get("lattice")
    if isinstance(lattice_info, dict):
        width_raw = lattice_info.get("width")
        height_raw = lattice_info.get("height")
        boundary = str(lattice_info.get("boundary", "periodic"))
        if width_raw is not None and height_raw is not None:
            return Lattice(width=int(width_raw), height=int(height_raw), boundary=boundary)

    energy = np.asarray(arrays["energy"], dtype=float)
    if energy.ndim != 2:
        raise ValueError(f"serialized energy must be 2D, got shape={energy.shape}")
    height, width = int(energy.shape[0]), int(energy.shape[1])
    return Lattice(width=width, height=height, boundary="periodic")


def build_state_from_payload(payload: dict[str, Any]) -> DETMState:
    with np.load(io.BytesIO(payload["arrays"])) as arrays:
        lattice = resolve_lattice(payload, arrays)
        field_state = DETMFieldState(
            lattice=lattice,
            energy=arrays["energy"].astype(float, copy=False),
            entropy=arrays["entropy"].astype(float, copy=False),
            internal_time=arrays["internal_time"].astype(float, copy=False),
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
    energy = to_numpy(state.field_state.energy).astype(float, copy=False).reshape(lattice.height, lattice.width)
    entropy = to_numpy(state.field_state.entropy).astype(float, copy=False).reshape(lattice.height, lattice.width)
    internal_time = to_numpy(state.field_state.internal_time).astype(float, copy=False).reshape(
        lattice.height, lattice.width
    )

    buffer = io.BytesIO()
    np.savez_compressed(buffer, energy=energy, entropy=entropy, internal_time=internal_time)
    return {
        "state_version": DETM_STATE_V1,
        "step_count": int(state.step_count),
        "rng_state": dict(state.rng_state),
        "config": state.config,
        "dynamics": state.dynamics.__dict__,
        "lattice": {"width": lattice.width, "height": lattice.height, "boundary": lattice.boundary},
        "arrays": buffer.getvalue(),
    }


__all__ = ["build_state_from_payload", "resolve_lattice", "state_to_payload"]
