"""Runtime composition for quorum policy, validator registry, and ack aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from detm.runtime.fabric import AckEnvelopeConsumer
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import AckResolver, InMemoryQuorumCoordinator, ValidatorRegistry
from detm.runtime.fabric.quorum_runtime_coordination import (
    load_validator_coordination_state,
    persist_validator_coordination_state,
    validator_coordination_paths,
    validator_coordination_quorums,
    validator_coordination_snapshot,
)
from detm.runtime.fabric.quorum_runtime_factory import (
    build_quorum_runtime_ctor_kwargs,
    normalize_validator_binding_map,
)
from detm.runtime.fabric.quorum_runtime_flow import (
    on_ack_envelope as _on_ack_envelope_flow,
    snapshot as _snapshot_flow,
)

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (runtime composition extracted; subscriber no longer builds quorum policy directly)
# - OOP_TECH_DEBT: distributed membership and replicated quorum-state persistence


@dataclass
class FabricQuorumRuntimeService(AckEnvelopeConsumer):
    """Composes validator membership + quorum policy into a runtime-facing service."""

    coordinator: InMemoryQuorumCoordinator
    validator_registry: ValidatorRegistry
    enforce_active_validator_membership: bool = False
    enforce_ack_sender_validator_match: bool = False
    enforce_ack_auth_key_id_binding: bool = False
    validator_auth_key_ids: dict[str, frozenset[str]] = field(default_factory=dict)
    enforce_ack_transport_identity_binding: bool = False
    validator_transport_identities: dict[str, frozenset[str]] = field(default_factory=dict)
    dropped_inactive_validator_total: int = 0
    dropped_sender_mismatch_total: int = 0
    dropped_invalid_inline_ack_total: int = 0
    dropped_missing_auth_key_id_total: int = 0
    dropped_auth_key_id_mismatch_total: int = 0
    dropped_missing_transport_identity_total: int = 0
    dropped_transport_identity_mismatch_total: int = 0
    validator_coordination_state_path: str | None = None
    validator_coordination_replica_paths: tuple[str, ...] = field(default_factory=tuple)
    validator_coordination_replica_read_quorum: int | None = None
    validator_coordination_replica_write_quorum: int | None = None
    validator_coordination_generation: int = 0
    validator_coordination_mode: str = "memory"
    validator_coordination_read_quorum_reached: bool = False
    validator_coordination_write_quorum_reached: bool = False
    validator_coordination_last_sync_error: str | None = None
    validator_coordination_last_sync_ts_ms: int = 0

    def __post_init__(self) -> None:
        load_validator_coordination_state(self)

    @classmethod
    def from_policy_settings(
        cls,
        *,
        required_proof_accepts: int = 1,
        required_trust_accepts: int = 1,
        required_unique_proof_validators: int = 1,
        required_unique_trust_validators: int = 1,
        required_validator_ids: Sequence[str] | None = None,
        enforce_required_validator_ids: bool = False,
        reject_on_any_reject: bool = False,
        pending_timeout_ms: int | None = None,
        ack_resolver: AckResolver | None = None,
        enforce_active_validator_membership: bool = False,
        enforce_ack_sender_validator_match: bool = False,
        enforce_ack_auth_key_id_binding: bool = False,
        validator_auth_key_ids: Mapping[str, Sequence[str] | str] | None = None,
        enforce_ack_transport_identity_binding: bool = False,
        validator_transport_identities: Mapping[str, Sequence[str] | str] | None = None,
        validator_coordination_state_path: str | None = None,
        validator_coordination_replica_paths: Sequence[str] | None = None,
        validator_coordination_replica_read_quorum: int | None = None,
        validator_coordination_replica_write_quorum: int | None = None,
    ) -> "FabricQuorumRuntimeService":
        return cls(
            **build_quorum_runtime_ctor_kwargs(
                required_proof_accepts=required_proof_accepts,
                required_trust_accepts=required_trust_accepts,
                required_unique_proof_validators=required_unique_proof_validators,
                required_unique_trust_validators=required_unique_trust_validators,
                required_validator_ids=required_validator_ids,
                enforce_required_validator_ids=enforce_required_validator_ids,
                reject_on_any_reject=reject_on_any_reject,
                pending_timeout_ms=pending_timeout_ms,
                ack_resolver=ack_resolver,
                enforce_active_validator_membership=enforce_active_validator_membership,
                enforce_ack_sender_validator_match=enforce_ack_sender_validator_match,
                enforce_ack_auth_key_id_binding=enforce_ack_auth_key_id_binding,
                validator_auth_key_ids=validator_auth_key_ids,
                enforce_ack_transport_identity_binding=enforce_ack_transport_identity_binding,
                validator_transport_identities=validator_transport_identities,
                validator_coordination_state_path=validator_coordination_state_path,
                validator_coordination_replica_paths=validator_coordination_replica_paths,
                validator_coordination_replica_read_quorum=validator_coordination_replica_read_quorum,
                validator_coordination_replica_write_quorum=validator_coordination_replica_write_quorum,
            )
        )

    def register_commit(self, commit_ref: str, *, created_at_ms: int | None = None) -> None:
        self.coordinator.register_commit(str(commit_ref), created_at_ms=created_at_ms)
        self._persist_validator_coordination_state()

    def on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        _on_ack_envelope_flow(self, envelope)

    def snapshot(self) -> dict[str, object]:
        return _snapshot_flow(self)

    def _validator_coordination_snapshot(self) -> dict[str, object]:
        return validator_coordination_snapshot(self)

    def _validator_coordination_paths(self) -> list[Path]:
        return validator_coordination_paths(self)

    def _validator_coordination_quorums(self, replica_count: int) -> tuple[int, int]:
        return validator_coordination_quorums(self, replica_count)

    def _load_validator_coordination_state(self) -> None:
        load_validator_coordination_state(self)

    def _persist_validator_coordination_state(self) -> None:
        persist_validator_coordination_state(self)


def _normalize_validator_auth_key_ids(
    raw: Mapping[str, Sequence[str] | str] | None,
) -> dict[str, frozenset[str]]:
    return normalize_validator_binding_map(raw)


__all__ = ["FabricQuorumRuntimeService"]
