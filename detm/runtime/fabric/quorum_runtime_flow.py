"""Flow helpers for FabricQuorumRuntimeService."""

from __future__ import annotations

from typing import Any

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric.quorum.resolver import ack_from_envelope_inline
from detm.runtime.fabric.quorum_runtime_coordination import validator_coordination_snapshot


def on_ack_envelope(runtime: Any, envelope: FabricEnvelope) -> None:
    sender_id = str(envelope.sender).strip()
    ack_inline = ack_from_envelope_inline(envelope)
    ack_any = ack_inline
    if ack_any is None and runtime.coordinator.ack_resolver is not None:
        try:
            ack_any = runtime.coordinator.ack_resolver(str(envelope.payload_ref))
        except Exception:
            ack_any = None
    validator_id = None
    if ack_any is not None:
        validator_id = str(getattr(ack_any, "validator_id", "")).strip() or None
    if validator_id is None:
        validator_id = sender_id or None
    if bool(runtime.enforce_ack_sender_validator_match) and ack_any is not None:
        if not sender_id or sender_id != str(validator_id or ""):
            runtime.dropped_sender_mismatch_total += 1
            runtime._persist_validator_coordination_state()
            return
    if bool(runtime.enforce_ack_sender_validator_match) and ack_inline is None and bool(envelope.payload_inline):
        runtime.dropped_invalid_inline_ack_total += 1
        runtime._persist_validator_coordination_state()
        return
    if bool(runtime.enforce_active_validator_membership):
        required_ids = runtime.validator_registry.required_validator_ids()
        if required_ids:
            if validator_id is None or not runtime.validator_registry.is_active(str(validator_id)):
                runtime.dropped_inactive_validator_total += 1
                runtime._persist_validator_coordination_state()
                return
    if bool(runtime.enforce_ack_auth_key_id_binding):
        raw_key_id = getattr(envelope, "auth_key_id", None)
        key_id = None if raw_key_id is None else str(raw_key_id).strip() or None
        allowed = runtime.validator_auth_key_ids.get(str(validator_id or "").strip(), frozenset())
        if key_id is None:
            runtime.dropped_missing_auth_key_id_total += 1
            runtime._persist_validator_coordination_state()
            return
        if not allowed or key_id not in allowed:
            runtime.dropped_auth_key_id_mismatch_total += 1
            runtime._persist_validator_coordination_state()
            return
    if bool(runtime.enforce_ack_transport_identity_binding):
        raw_transport_identity = getattr(envelope, "transport_identity", None)
        transport_identity = None if raw_transport_identity is None else str(raw_transport_identity).strip() or None
        allowed_transport = runtime.validator_transport_identities.get(str(validator_id or "").strip(), frozenset())
        if transport_identity is None:
            runtime.dropped_missing_transport_identity_total += 1
            runtime._persist_validator_coordination_state()
            return
        if not allowed_transport or transport_identity not in allowed_transport:
            runtime.dropped_transport_identity_mismatch_total += 1
            runtime._persist_validator_coordination_state()
            return
    runtime.coordinator.on_ack_envelope(envelope)
    runtime._persist_validator_coordination_state()


def snapshot(runtime: Any) -> dict[str, object]:
    out = dict(runtime.coordinator.snapshot())
    out["validator_registry"] = runtime.validator_registry.to_dict()
    out["pending_timeout_ms"] = (
        None if runtime.coordinator.pending_timeout_ms is None else int(runtime.coordinator.pending_timeout_ms)
    )
    out["membership_hardening"] = {
        "enforce_active_validator_membership": bool(runtime.enforce_active_validator_membership),
        "enforce_ack_sender_validator_match": bool(runtime.enforce_ack_sender_validator_match),
        "enforce_ack_auth_key_id_binding": bool(runtime.enforce_ack_auth_key_id_binding),
        "enforce_ack_transport_identity_binding": bool(runtime.enforce_ack_transport_identity_binding),
        "dropped_inactive_validator_total": int(runtime.dropped_inactive_validator_total),
        "dropped_sender_mismatch_total": int(runtime.dropped_sender_mismatch_total),
        "dropped_invalid_inline_ack_total": int(runtime.dropped_invalid_inline_ack_total),
        "dropped_missing_auth_key_id_total": int(runtime.dropped_missing_auth_key_id_total),
        "dropped_auth_key_id_mismatch_total": int(runtime.dropped_auth_key_id_mismatch_total),
        "dropped_missing_transport_identity_total": int(runtime.dropped_missing_transport_identity_total),
        "dropped_transport_identity_mismatch_total": int(runtime.dropped_transport_identity_mismatch_total),
        "registry_validator_count": int(len(runtime.validator_registry.required_validator_ids())),
        "validator_auth_key_ids": {
            str(validator_id): sorted(str(key_id) for key_id in key_ids)
            for validator_id, key_ids in sorted(runtime.validator_auth_key_ids.items())
        },
        "validator_transport_identities": {
            str(validator_id): sorted(str(identity) for identity in identities)
            for validator_id, identities in sorted(runtime.validator_transport_identities.items())
        },
    }
    out["validator_coordination_state"] = validator_coordination_snapshot(runtime)
    return out


__all__ = ["on_ack_envelope", "snapshot"]
