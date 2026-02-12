"""Runtime composition for quorum policy, validator registry, and ack aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from detm.runtime.fabric_ack_ingress import AckEnvelopeConsumer
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_quorum import (
    AckResolver,
    BasicQuorumPolicy,
    InMemoryQuorumCoordinator,
    ValidatorSetQuorumPolicy,
)
from detm.runtime.fabric_validator_registry import StaticValidatorRegistry, ValidatorRegistry

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (runtime composition extracted; subscriber no longer builds quorum policy directly)
# - OOP_TECH_DEBT: distributed membership and replicated quorum-state persistence


@dataclass
class FabricQuorumRuntimeService(AckEnvelopeConsumer):
    """Composes validator membership + quorum policy into a runtime-facing service."""

    coordinator: InMemoryQuorumCoordinator
    validator_registry: ValidatorRegistry

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
    ) -> "FabricQuorumRuntimeService":
        registry = StaticValidatorRegistry.from_ids(required_validator_ids)
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
        return cls(coordinator=coordinator, validator_registry=registry)

    def register_commit(self, commit_ref: str, *, created_at_ms: int | None = None) -> None:
        self.coordinator.register_commit(str(commit_ref), created_at_ms=created_at_ms)

    def on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        self.coordinator.on_ack_envelope(envelope)

    def snapshot(self) -> dict[str, object]:
        out = dict(self.coordinator.snapshot())
        out["validator_registry"] = self.validator_registry.to_dict()
        out["pending_timeout_ms"] = (
            None if self.coordinator.pending_timeout_ms is None else int(self.coordinator.pending_timeout_ms)
        )
        return out


__all__ = ["FabricQuorumRuntimeService"]
