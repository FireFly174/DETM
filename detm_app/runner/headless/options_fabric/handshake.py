"""Handshake/quorum fabric option resolution."""

from __future__ import annotations

from typing import Any

from detm_app.runner.headless.helpers import as_list, flatten_list_args


def resolve_handshake_fabric_options(*, args: Any, runner_defaults: dict[str, Any]) -> dict[str, Any]:
    fabric_handshake = (
        args.fabric_handshake
        if args.fabric_handshake is not None
        else bool(runner_defaults.get("fabric_handshake", False))
    )
    fabric_required_proof_accepts = (
        int(args.fabric_proof_quorum)
        if args.fabric_proof_quorum is not None
        else int(runner_defaults.get("fabric_required_proof_accepts", 1))
    )
    fabric_required_trust_accepts = (
        int(args.fabric_trust_quorum)
        if args.fabric_trust_quorum is not None
        else int(runner_defaults.get("fabric_required_trust_accepts", 1))
    )
    fabric_required_unique_proof_validators = (
        int(args.fabric_unique_proof_validators)
        if args.fabric_unique_proof_validators is not None
        else int(runner_defaults.get("fabric_required_unique_proof_validators", 1))
    )
    fabric_required_unique_trust_validators = (
        int(args.fabric_unique_trust_validators)
        if args.fabric_unique_trust_validators is not None
        else int(runner_defaults.get("fabric_required_unique_trust_validators", 1))
    )
    if args.fabric_validator_set is not None:
        fabric_required_validator_ids = as_list(args.fabric_validator_set)
    else:
        fabric_required_validator_ids = as_list(runner_defaults.get("fabric_required_validator_ids"))
    fabric_handshake_profile = (
        str(args.fabric_handshake_profile)
        if args.fabric_handshake_profile is not None
        else str(runner_defaults.get("fabric_handshake_profile", "mvp"))
    )
    fabric_enforce_required_validator_ids = (
        bool(args.fabric_enforce_validator_set)
        if args.fabric_enforce_validator_set is not None
        else bool(runner_defaults.get("fabric_enforce_required_validator_ids", False))
    )
    fabric_enforce_active_validator_membership = (
        bool(args.fabric_enforce_active_validator_membership)
        if args.fabric_enforce_active_validator_membership is not None
        else bool(runner_defaults.get("fabric_enforce_active_validator_membership", False))
    )
    fabric_enforce_ack_sender_validator_match = (
        bool(args.fabric_enforce_ack_sender_validator_match)
        if args.fabric_enforce_ack_sender_validator_match is not None
        else bool(runner_defaults.get("fabric_enforce_ack_sender_validator_match", False))
    )
    fabric_enforce_ack_auth_key_id_binding = (
        bool(args.fabric_enforce_ack_auth_key_id_binding)
        if args.fabric_enforce_ack_auth_key_id_binding is not None
        else bool(runner_defaults.get("fabric_enforce_ack_auth_key_id_binding", False))
    )
    if args.fabric_validator_auth_key_id is not None:
        fabric_validator_auth_key_ids = flatten_list_args(list(args.fabric_validator_auth_key_id))
    else:
        fabric_validator_auth_key_ids = as_list(runner_defaults.get("fabric_validator_auth_key_ids"))
    fabric_enforce_ack_transport_identity_binding = (
        bool(args.fabric_enforce_ack_transport_identity_binding)
        if args.fabric_enforce_ack_transport_identity_binding is not None
        else bool(runner_defaults.get("fabric_enforce_ack_transport_identity_binding", False))
    )
    if args.fabric_validator_transport_identity is not None:
        fabric_validator_transport_identities = flatten_list_args(list(args.fabric_validator_transport_identity))
    else:
        fabric_validator_transport_identities = as_list(runner_defaults.get("fabric_validator_transport_identities"))
    fabric_reject_on_any_reject = (
        bool(args.fabric_reject_on_any_reject)
        if args.fabric_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_reject_on_any_reject", False))
    )
    fabric_retry_attempts = (
        int(args.fabric_retry_attempts)
        if args.fabric_retry_attempts is not None
        else int(runner_defaults.get("fabric_retry_attempts", 2))
    )
    fabric_commit_retry_attempts = (
        int(args.fabric_commit_retry_attempts)
        if args.fabric_commit_retry_attempts is not None
        else int(runner_defaults.get("fabric_commit_retry_attempts", 2))
    )
    raw_pending_timeout_ms = runner_defaults.get("fabric_pending_timeout_ms")
    fabric_pending_timeout_ms = (
        int(args.fabric_pending_timeout_ms)
        if args.fabric_pending_timeout_ms is not None
        else (None if raw_pending_timeout_ms is None else int(raw_pending_timeout_ms))
    )
    return {
        "fabric_handshake": bool(fabric_handshake),
        "fabric_required_proof_accepts": fabric_required_proof_accepts,
        "fabric_required_trust_accepts": fabric_required_trust_accepts,
        "fabric_required_unique_proof_validators": fabric_required_unique_proof_validators,
        "fabric_required_unique_trust_validators": fabric_required_unique_trust_validators,
        "fabric_required_validator_ids": fabric_required_validator_ids,
        "fabric_handshake_profile": fabric_handshake_profile,
        "fabric_enforce_required_validator_ids": bool(fabric_enforce_required_validator_ids),
        "fabric_enforce_active_validator_membership": bool(fabric_enforce_active_validator_membership),
        "fabric_enforce_ack_sender_validator_match": bool(fabric_enforce_ack_sender_validator_match),
        "fabric_enforce_ack_auth_key_id_binding": bool(fabric_enforce_ack_auth_key_id_binding),
        "fabric_validator_auth_key_ids": fabric_validator_auth_key_ids,
        "fabric_enforce_ack_transport_identity_binding": bool(fabric_enforce_ack_transport_identity_binding),
        "fabric_validator_transport_identities": fabric_validator_transport_identities,
        "fabric_reject_on_any_reject": bool(fabric_reject_on_any_reject),
        "fabric_retry_attempts": fabric_retry_attempts,
        "fabric_commit_retry_attempts": fabric_commit_retry_attempts,
        "fabric_pending_timeout_ms": fabric_pending_timeout_ms,
    }


__all__ = ["resolve_handshake_fabric_options"]
