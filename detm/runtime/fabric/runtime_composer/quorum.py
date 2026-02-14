"""Quorum runtime builders for fabric runtime composition."""

from __future__ import annotations

from typing import Any, Callable


def build_quorum_runtime(
    *,
    rec: Any,
    artifact_resolver: Any,
    from_policy_settings: Callable[..., Any],
) -> tuple[Any, Any, Any]:
    quorum_runtime = from_policy_settings(
        required_proof_accepts=int(rec.required_proof_accepts),
        required_trust_accepts=int(rec.required_trust_accepts),
        required_unique_proof_validators=int(rec.required_unique_proof_validators),
        required_unique_trust_validators=int(rec.required_unique_trust_validators),
        required_validator_ids=rec.required_validator_ids,
        enforce_required_validator_ids=bool(rec.enforce_required_validator_ids),
        reject_on_any_reject=bool(rec.reject_on_any_reject),
        pending_timeout_ms=rec.pending_timeout_ms,
        ack_resolver=artifact_resolver.resolve_ack,
        enforce_active_validator_membership=bool(getattr(rec, "enforce_active_validator_membership", False)),
        enforce_ack_sender_validator_match=bool(getattr(rec, "enforce_ack_sender_validator_match", False)),
        enforce_ack_auth_key_id_binding=bool(getattr(rec, "enforce_ack_auth_key_id_binding", False)),
        validator_auth_key_ids=getattr(rec, "validator_auth_key_ids", None),
        enforce_ack_transport_identity_binding=bool(
            getattr(rec, "enforce_ack_transport_identity_binding", False)
        ),
        validator_transport_identities=getattr(rec, "validator_transport_identities", None),
        validator_coordination_state_path=getattr(rec, "validator_coordination_state_path", None),
        validator_coordination_replica_paths=getattr(rec, "validator_coordination_replica_paths", None),
        validator_coordination_replica_read_quorum=getattr(rec, "validator_coordination_replica_read_quorum", None),
        validator_coordination_replica_write_quorum=getattr(rec, "validator_coordination_replica_write_quorum", None),
    )
    quorum = quorum_runtime.coordinator
    validator_registry = quorum_runtime.validator_registry
    return quorum_runtime, quorum, validator_registry


__all__ = ["build_quorum_runtime"]
