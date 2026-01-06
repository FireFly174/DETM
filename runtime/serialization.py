"""State serialization helpers with forward compatibility hooks."""

from __future__ import annotations

import io
from typing import Any, Dict

import msgpack
import numpy as np

from core.entropy import DynamicsParameters
from core.fields import Lattice
from runtime.schemas import DETM_STATE_V1
from runtime.signature import digest_fields
from runtime.state import DETMFieldState, DETMState


def _to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None

    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def serialize_state(state: DETMState) -> bytes:
    """Serialize DETMState into a portable bytes blob.

    Uses msgpack for metadata and stores dense arrays via NumPy npz payload.
    """

    lattice = state.lattice
    energy = _to_numpy(state.field_state.energy).astype(float, copy=False).reshape(lattice.height, lattice.width)
    entropy = _to_numpy(state.field_state.entropy).astype(float, copy=False).reshape(lattice.height, lattice.width)
    internal_time = _to_numpy(state.field_state.internal_time).astype(float, copy=False).reshape(lattice.height, lattice.width)

    buffer = io.BytesIO()
    np.savez_compressed(buffer, energy=energy, entropy=entropy, internal_time=internal_time)
    payload = {
        "state_version": state.state_version,
        "step_count": state.step_count,
        "rng_state": state.rng_state,
        "config": state.config,
        "dynamics": state.dynamics.__dict__,
        "lattice": {"width": lattice.width, "height": lattice.height, "boundary": lattice.boundary},
        "arrays": buffer.getvalue(),
    }
    return msgpack.dumps(payload, use_bin_type=True)


def deserialize_state(blob: bytes) -> DETMState:
    """Reconstruct DETMState from bytes produced by :func:`serialize_state`."""

    data: Dict[str, Any] = msgpack.loads(blob, raw=False)
    arrays = np.load(io.BytesIO(data["arrays"]))
    lattice_info = data["lattice"]
    lattice = Lattice(width=int(lattice_info["width"]), height=int(lattice_info["height"]), boundary=str(lattice_info["boundary"]))

    field_state = DETMFieldState(
        lattice=lattice,
        energy=arrays["energy"].astype(float, copy=False),
        entropy=arrays["entropy"].astype(float, copy=False),
        internal_time=arrays["internal_time"].astype(float, copy=False),
    )
    state = DETMState(
        state_version=str(data.get("state_version", DETM_STATE_V1)),
        field_state=field_state,
        step_count=int(data.get("step_count", 0)),
        rng_state=data.get("rng_state", {}),
        config=data.get("config"),
        dynamics=DynamicsParameters(**data.get("dynamics", {})),
    )
    return state


def digest_blob(blob: bytes) -> bytes:
    state = deserialize_state(blob)
    sig = digest_fields(
        _to_numpy(state.field_state.energy).reshape(state.lattice.height, state.lattice.width),
        _to_numpy(state.field_state.entropy).reshape(state.lattice.height, state.lattice.width),
        _to_numpy(state.field_state.internal_time).reshape(state.lattice.height, state.lattice.width),
    )
    return msgpack.dumps(sig.as_dict(), use_bin_type=True)


def migrate_state(_blob: bytes, _from_version: str, _to_version: str) -> bytes:  # pragma: no cover - placeholder
    """Placeholder for future state migrations."""

    raise NotImplementedError("No state migrations defined yet")


__all__ = ["deserialize_state", "digest_blob", "migrate_state", "serialize_state"]
