"""Factory helpers for Fabric quorum runtime construction."""

from __future__ import annotations

from typing import Mapping, Sequence

from detm.runtime.fabric import (
    AckResolver,
    BasicQuorumPolicy,
    InMemoryQuorumCoordinator,
    StaticValidatorRegistry,
    ValidatorSetQuorumPolicy,
)


def normalize_validator_binding_map(
    raw: Mapping[str, Sequence[str] | str] | None,
) -> dict[str, frozenset[str]]:
    out: dict[str, set[str]] = {}
    if raw is None:
        return {}
    for raw_validator_id, raw_values in dict(raw).items():
        validator_id = str(raw_validator_id).strip()
        if not validator_id:
            continue
        values: list[str]
        if isinstance(raw_values, str):
            values = [chunk.strip() for chunk in raw_values.split(",") if chunk.strip()]
        elif isinstance(raw_values, Sequence):
            values = [str(chunk).strip() for chunk in list(raw_values) if str(chunk).strip()]
        else:
            value = str(raw_values).strip()
            values = [value] if value else []
        if not values:
            continue
        bucket = out.setdefault(validator_id, set())
        bucket.update(values)
    return {validator_id: frozenset(sorted(values)) for validator_id, values in out.items() if values}


def build_quorum_runtime_ctor_kwargs(
    *,
    required_proof_accepts: int,
    required_trust_accepts: int,
    required_unique_proof_validators: int,
    required_unique_trust_validators: int,
    required_validator_ids: Sequence[str] | None,
    enforce_required_validator_ids: bool,
    reject_on_any_reject: bool,
    pending_timeout_ms: int | None,
    ack_resolver: AckResolver | None,
    enforce_active_validator_membership: bool,
    enforce_ack_sender_validator_match: bool,
    enforce_ack_auth_key_id_binding: bool,
    validator_auth_key_ids: Mapping[str, Sequence[str] | str] | None,
    enforce_ack_transport_identity_binding: bool,
    validator_transport_identities: Mapping[str, Sequence[str] | str] | None,
    validator_coordination_state_path: str | None,
    validator_coordination_replica_paths: Sequence[str] | None,
    validator_coordination_replica_read_quorum: int | None,
    validator_coordination_replica_write_quorum: int | None,
) -> dict[str, object]:
    registry = StaticValidatorRegistry.from_ids(required_validator_ids)
    auth_key_ids = normalize_validator_binding_map(validator_auth_key_ids)
    transport_identities = normalize_validator_binding_map(validator_transport_identities)
    if bool(enforce_ack_auth_key_id_binding) and not auth_key_ids:
        raise ValueError("validator_auth_key_ids must be non-empty when enforce_ack_auth_key_id_binding=true")
    if bool(enforce_ack_transport_identity_binding) and not transport_identities:
        raise ValueError(
            "validator_transport_identities must be non-empty when enforce_ack_transport_identity_binding=true"
        )
    validator_set = sorted(registry.required_validator_ids())
    if (
        int(required_unique_proof_validators) > 1
        or int(required_unique_trust_validators) > 1
        or bool(enforce_required_validator_ids)
        or len(validator_set) > 0
    ):
        policy = ValidatorSetQuorumPolicy(
            required_proof_accepts=int(required_proof_accepts),
            required_trust_accepts=int(required_trust_accepts),
            required_unique_proof_validators=int(required_unique_proof_validators),
            required_unique_trust_validators=int(required_unique_trust_validators),
            required_validator_ids=frozenset(validator_set),
            enforce_required_validator_ids=bool(enforce_required_validator_ids),
            reject_on_any_reject=bool(reject_on_any_reject),
        )
    else:
        policy = BasicQuorumPolicy(
            required_proof_accepts=int(required_proof_accepts),
            required_trust_accepts=int(required_trust_accepts),
            reject_on_any_reject=bool(reject_on_any_reject),
        )
    coordinator = InMemoryQuorumCoordinator(policy=policy, ack_resolver=ack_resolver)
    coordinator.pending_timeout_ms = pending_timeout_ms
    replica_paths = tuple(
        str(path).strip() for path in list(validator_coordination_replica_paths or []) if str(path).strip()
    )
    return {
        "coordinator": coordinator,
        "validator_registry": registry,
        "enforce_active_validator_membership": bool(enforce_active_validator_membership),
        "enforce_ack_sender_validator_match": bool(enforce_ack_sender_validator_match),
        "enforce_ack_auth_key_id_binding": bool(enforce_ack_auth_key_id_binding),
        "validator_auth_key_ids": auth_key_ids,
        "enforce_ack_transport_identity_binding": bool(enforce_ack_transport_identity_binding),
        "validator_transport_identities": transport_identities,
        "validator_coordination_state_path": (
            None
            if validator_coordination_state_path is None or not str(validator_coordination_state_path).strip()
            else str(validator_coordination_state_path).strip()
        ),
        "validator_coordination_replica_paths": replica_paths,
        "validator_coordination_replica_read_quorum": (
            None
            if validator_coordination_replica_read_quorum is None
            else max(1, int(validator_coordination_replica_read_quorum))
        ),
        "validator_coordination_replica_write_quorum": (
            None
            if validator_coordination_replica_write_quorum is None
            else max(1, int(validator_coordination_replica_write_quorum))
        ),
    }


__all__ = ["build_quorum_runtime_ctor_kwargs", "normalize_validator_binding_map"]
