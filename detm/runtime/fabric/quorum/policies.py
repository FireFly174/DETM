"""Concrete quorum policy implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Sequence

from detm.runtime.fabric import ProofAck, TrustAck


def _norm_validator_set(values: Sequence[str] | None) -> FrozenSet[str]:
    if not values:
        return frozenset()
    return frozenset(str(v).strip() for v in values if str(v).strip())


@dataclass(frozen=True)
class BasicQuorumPolicy:
    """Simple count-based quorum for local/distributed MVP flows."""

    required_proof_accepts: int = 1
    required_trust_accepts: int = 1
    reject_on_any_reject: bool = False

    def evaluate(
        self,
        proof_acks: Sequence[ProofAck],
        trust_acks: Sequence[TrustAck],
    ) -> tuple[str, str | None]:
        proof_accepts = sum(1 for ack in proof_acks if ack.status == "accepted")
        trust_accepts = sum(1 for ack in trust_acks if ack.status == "accepted")
        proof_rejects = sum(1 for ack in proof_acks if ack.status == "rejected")
        trust_rejects = sum(1 for ack in trust_acks if ack.status == "rejected")

        if self.reject_on_any_reject and (proof_rejects > 0 or trust_rejects > 0):
            return "rejected", "at least one rejection under reject_on_any_reject policy"
        if proof_accepts >= int(self.required_proof_accepts) and trust_accepts >= int(self.required_trust_accepts):
            return "accepted", None
        return "pending", "quorum threshold not reached"


@dataclass(frozen=True)
class ValidatorSetQuorumPolicy:
    """Quorum policy with validator-set and unique-validator constraints."""

    required_proof_accepts: int = 1
    required_trust_accepts: int = 1
    required_unique_proof_validators: int = 1
    required_unique_trust_validators: int = 1
    required_validator_ids: FrozenSet[str] = field(default_factory=frozenset)
    enforce_required_validator_ids: bool = False
    reject_on_any_reject: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_validator_ids", _norm_validator_set(self.required_validator_ids))

    def evaluate(
        self,
        proof_acks: Sequence[ProofAck],
        trust_acks: Sequence[TrustAck],
    ) -> tuple[str, str | None]:
        proof_accepts = [ack for ack in proof_acks if ack.status == "accepted"]
        trust_accepts = [ack for ack in trust_acks if ack.status == "accepted"]
        proof_rejects = [ack for ack in proof_acks if ack.status == "rejected"]
        trust_rejects = [ack for ack in trust_acks if ack.status == "rejected"]
        if self.reject_on_any_reject and (proof_rejects or trust_rejects):
            return "rejected", "at least one rejection under reject_on_any_reject policy"

        if len(proof_accepts) < int(self.required_proof_accepts):
            return "pending", "proof_ack threshold not reached"
        if len(trust_accepts) < int(self.required_trust_accepts):
            return "pending", "trust_ack threshold not reached"

        proof_validators = {str(ack.validator_id) for ack in proof_accepts}
        trust_validators = {str(ack.validator_id) for ack in trust_accepts}
        if len(proof_validators) < int(self.required_unique_proof_validators):
            return "pending", "proof unique-validator threshold not reached"
        if len(trust_validators) < int(self.required_unique_trust_validators):
            return "pending", "trust unique-validator threshold not reached"

        required = set(self.required_validator_ids)
        if required and self.enforce_required_validator_ids:
            missing_proof = sorted(required.difference(proof_validators))
            missing_trust = sorted(required.difference(trust_validators))
            if missing_proof or missing_trust:
                return "pending", (
                    f"required validator set missing: "
                    f"proof_missing={missing_proof}, trust_missing={missing_trust}"
                )
        return "accepted", None


__all__ = ["BasicQuorumPolicy", "ValidatorSetQuorumPolicy"]


