"""State serialization helpers with explicit schema migration support."""

from __future__ import annotations

from detm.runtime.schemas import DETM_STATE_V1
from detm.runtime.serialization.migration import (
    MigrationAdapter,
    migrate_payload,
    register_migration,
)
from detm.runtime.serialization.payload import (
    DETM_STATE_LEGACY,
    StatePayload,
    detect_payload_state_version,
    pack_payload,
    to_numpy,
    unpack_payload,
)
from detm.runtime.serialization.state import build_state_from_payload, state_to_payload
from detm.runtime.signature import digest_fields
from detm.runtime.state import DETMState

_MIGRATION_ADAPTERS: dict[tuple[str, str], MigrationAdapter] = {}


@register_migration(_MIGRATION_ADAPTERS, DETM_STATE_LEGACY, DETM_STATE_V1)
def _migrate_legacy_to_v1(payload: StatePayload) -> StatePayload:
    out = dict(payload)
    out["state_version"] = DETM_STATE_V1
    out["step_count"] = int(out.get("step_count", 0))
    out["rng_state"] = dict(out.get("rng_state", {})) if isinstance(out.get("rng_state", {}), dict) else {}
    out["config"] = out.get("config", None)
    out["dynamics"] = dict(out.get("dynamics", {})) if isinstance(out.get("dynamics", {}), dict) else {}
    lattice = out.get("lattice", None)
    out["lattice"] = dict(lattice) if isinstance(lattice, dict) else {}
    return out


@register_migration(_MIGRATION_ADAPTERS, DETM_STATE_V1, DETM_STATE_LEGACY)
def _migrate_v1_to_legacy(payload: StatePayload) -> StatePayload:
    out = dict(payload)
    out.pop("state_version", None)
    return out


def _migrate_payload(payload: StatePayload, *, from_version: str, to_version: str) -> StatePayload:
    return migrate_payload(
        payload,
        from_version=from_version,
        to_version=to_version,
        registry=_MIGRATION_ADAPTERS,
    )


def serialize_state(state: DETMState) -> bytes:
    """Serialize DETMState into a portable bytes blob.

    Uses msgpack for metadata and stores dense arrays via NumPy npz payload.
    Output uses the canonical current state schema version.
    """

    payload = state_to_payload(state, to_numpy=to_numpy)
    return pack_payload(payload)


def deserialize_state(blob: bytes) -> DETMState:
    """Reconstruct DETMState from bytes produced by :func:`serialize_state`.

    Legacy payloads are migrated to the canonical schema before reconstruction.
    """

    payload = unpack_payload(blob)
    from_version = detect_payload_state_version(payload)
    if from_version != DETM_STATE_V1:
        payload = _migrate_payload(payload, from_version=from_version, to_version=DETM_STATE_V1)
    return build_state_from_payload(payload)


def digest_blob(blob: bytes) -> bytes:
    state = deserialize_state(blob)
    sig = digest_fields(
        to_numpy(state.field_state.energy).reshape(state.lattice.height, state.lattice.width),
        to_numpy(state.field_state.entropy).reshape(state.lattice.height, state.lattice.width),
        to_numpy(state.field_state.internal_time).reshape(state.lattice.height, state.lattice.width),
    )
    return pack_payload(sig.as_dict())


def migrate_state(blob: bytes, from_version: str, to_version: str) -> bytes:
    """Migrate serialized state blob between supported schema versions."""

    source_version = str(from_version).strip()
    target_version = str(to_version).strip()
    if not source_version:
        raise ValueError("from_version must be a non-empty string")
    if not target_version:
        raise ValueError("to_version must be a non-empty string")

    payload = unpack_payload(blob)
    embedded_version = detect_payload_state_version(payload)
    if embedded_version != source_version:
        raise ValueError(
            f"state blob version mismatch: expected {source_version!r}, embedded {embedded_version!r}"
        )

    migrated = _migrate_payload(payload, from_version=source_version, to_version=target_version)
    if target_version == DETM_STATE_V1:
        migrated["state_version"] = DETM_STATE_V1
    if target_version == DETM_STATE_LEGACY:
        migrated.pop("state_version", None)
    return pack_payload(migrated)


__all__ = ["deserialize_state", "digest_blob", "migrate_state", "serialize_state"]
