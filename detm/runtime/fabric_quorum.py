"""Quorum policy and in-memory coordinator for ack aggregation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Protocol, Sequence

from detm.runtime.fabric_ack import ProofAck, TrustAck
from detm.runtime.fabric_envelope import FabricEnvelope

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (quorum policy abstraction exists)
# - OOP_TECH_DEBT: distributed persistent coordinator and cross-node consensus strategy


class QuorumPolicy(Protocol):
    """Abstract policy deciding commit status from proof/trust acknowledgements."""

    def evaluate(
        self,
        proof_acks: Sequence[ProofAck],
        trust_acks: Sequence[TrustAck],
    ) -> tuple[str, str | None]:
        ...


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


def _norm_validator_set(values: Sequence[str] | None) -> FrozenSet[str]:
    if not values:
        return frozenset()
    return frozenset(str(v).strip() for v in values if str(v).strip())


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


AckResolver = Callable[[str], ProofAck | TrustAck | None]


def _ack_from_envelope_inline(envelope: FabricEnvelope) -> ProofAck | TrustAck | None:
    payload = envelope.payload_inline
    if not isinstance(payload, dict):
        return None
    try:
        if envelope.message_type == "proof_ack":
            return ProofAck.from_dict(payload)
        if envelope.message_type == "trust_ack":
            return TrustAck.from_dict(payload)
    except Exception:
        return None
    return None


@dataclass
class InMemoryQuorumCoordinator:
    """Aggregates ack envelopes and evaluates commit status with a quorum policy."""

    policy: QuorumPolicy = field(default_factory=BasicQuorumPolicy)
    ack_resolver: AckResolver | None = None
    pending_timeout_ms: int | None = None
    _proof_by_commit: Dict[str, List[ProofAck]] = field(default_factory=dict)
    _trust_by_commit: Dict[str, List[TrustAck]] = field(default_factory=dict)
    _first_seen_ms: Dict[str, int] = field(default_factory=dict)

    def register_commit(self, commit_ref: str, *, created_at_ms: int | None = None) -> None:
        cref = str(commit_ref)
        if cref not in self._first_seen_ms:
            self._first_seen_ms[cref] = int(created_at_ms) if created_at_ms is not None else int(time.time() * 1000)

    def on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        if envelope.message_type not in {"proof_ack", "trust_ack"}:
            return
        ack = self.ack_resolver(str(envelope.payload_ref)) if self.ack_resolver is not None else None
        if ack is None:
            ack = _ack_from_envelope_inline(envelope)
        if ack is None:
            return
        commit_ref = str(envelope.commit_ref or ack.commit_ref)
        ack_created_at_ms = int(getattr(ack, "created_at_ms", 0) or 0)
        self.register_commit(
            commit_ref,
            created_at_ms=ack_created_at_ms if ack_created_at_ms > 0 else None,
        )
        if isinstance(ack, ProofAck):
            self._proof_by_commit.setdefault(commit_ref, []).append(ack)
        elif isinstance(ack, TrustAck):
            self._trust_by_commit.setdefault(commit_ref, []).append(ack)

    def evaluate(self, commit_ref: str, *, now_ms: int | None = None) -> Dict[str, object]:
        cref = str(commit_ref)
        self.register_commit(cref)
        proof_acks = list(self._proof_by_commit.get(cref, []))
        trust_acks = list(self._trust_by_commit.get(cref, []))
        status, reason = self.policy.evaluate(proof_acks, trust_acks)
        proof_validators = sorted({str(ack.validator_id) for ack in proof_acks if ack.status == "accepted"})
        trust_validators = sorted({str(ack.validator_id) for ack in trust_acks if ack.status == "accepted"})
        first_seen = int(self._first_seen_ms.get(cref, int(time.time() * 1000)))
        current_ms = int(now_ms) if now_ms is not None else int(time.time() * 1000)
        age_ms = max(0, current_ms - first_seen)
        timeout_enabled = self.pending_timeout_ms is not None
        timeout_exceeded = bool(timeout_enabled and age_ms >= int(self.pending_timeout_ms or 0))
        if status == "pending" and timeout_exceeded:
            status = "rejected"
            reason = f"pending timeout exceeded ({age_ms}ms >= {int(self.pending_timeout_ms or 0)}ms)"
        return {
            "commit_ref": cref,
            "status": status,
            "reason": reason,
            "age_ms": age_ms,
            "timeout": {
                "enabled": timeout_enabled,
                "pending_timeout_ms": None if self.pending_timeout_ms is None else int(self.pending_timeout_ms),
                "exceeded": timeout_exceeded,
            },
            "proof": {
                "total": len(proof_acks),
                "accepted": sum(1 for ack in proof_acks if ack.status == "accepted"),
                "rejected": sum(1 for ack in proof_acks if ack.status == "rejected"),
                "unique_accepted_validators": proof_validators,
            },
            "trust": {
                "total": len(trust_acks),
                "accepted": sum(1 for ack in trust_acks if ack.status == "accepted"),
                "rejected": sum(1 for ack in trust_acks if ack.status == "rejected"),
                "unique_accepted_validators": trust_validators,
            },
        }

    def snapshot(self) -> Dict[str, object]:
        commit_refs = (
            set(self._proof_by_commit.keys()) | set(self._trust_by_commit.keys()) | set(self._first_seen_ms.keys())
        )
        now_ms = int(time.time() * 1000)
        evaluations = [self.evaluate(cref, now_ms=now_ms) for cref in sorted(commit_refs)]
        return {
            "commit_count": len(evaluations),
            "accepted_count": sum(1 for row in evaluations if row.get("status") == "accepted"),
            "pending_count": sum(1 for row in evaluations if row.get("status") == "pending"),
            "rejected_count": sum(1 for row in evaluations if row.get("status") == "rejected"),
            "evaluations": evaluations,
        }


__all__ = [
    "AckResolver",
    "BasicQuorumPolicy",
    "InMemoryQuorumCoordinator",
    "QuorumPolicy",
    "ValidatorSetQuorumPolicy",
]
