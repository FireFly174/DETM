"""State serialization helpers with forward compatibility hooks."""

from __future__ import annotations

import io
from typing import Any, Dict

import msgpack
import numpy as np

from core.entropy import DynamicsParameters, compute_entropy
from core.fields import FieldState, Lattice, ScalarField
from runtime.schemas import DETM_STATE_V1
from runtime.signature import digest_fields
from runtime.state import DETMState


def serialize_state(state: DETMState) -> bytes:
    """Serialize DETMState into a portable bytes blob.

    Uses msgpack for metadata and stores dense arrays via NumPy npz payload.
    """

    lattice = state.lattice
    energy = np.asarray(state.field_state.energy.values, dtype=float).reshape(lattice.height, lattice.width)
    entropy = np.asarray(state.field_state.entropy.values, dtype=float).reshape(lattice.height, lattice.width)
    internal_time = np.asarray(state.field_state.internal_time.values, dtype=float).reshape(lattice.height, lattice.width)

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

    energy = ScalarField(lattice, arrays["energy"].reshape(-1).astype(float).tolist())
    entropy = ScalarField(lattice, arrays["entropy"].reshape(-1).astype(float).tolist())
    internal_time = ScalarField(lattice, arrays["internal_time"].reshape(-1).astype(float).tolist())

    field_state = FieldState(energy=energy, entropy=entropy, internal_time=internal_time)
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
        np.asarray(state.field_state.energy.values).reshape(state.lattice.height, state.lattice.width),
        np.asarray(state.field_state.entropy.values).reshape(state.lattice.height, state.lattice.width),
        np.asarray(state.field_state.internal_time.values).reshape(state.lattice.height, state.lattice.width),
    )
    return msgpack.dumps(sig.as_dict(), use_bin_type=True)


def migrate_state(_blob: bytes, _from_version: str, _to_version: str) -> bytes:  # pragma: no cover - placeholder
    """Placeholder for future state migrations."""

    raise NotImplementedError("No state migrations defined yet")


__all__ = ["deserialize_state", "digest_blob", "migrate_state", "serialize_state"]
