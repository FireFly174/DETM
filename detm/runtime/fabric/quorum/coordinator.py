"""In-memory quorum coordinator implementation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List

from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric.quorum.contracts import AckResolver, QuorumPolicy
from detm.runtime.fabric.quorum.policies import BasicQuorumPolicy
from detm.runtime.fabric.quorum.resolver import ack_from_envelope_inline


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
            ack = ack_from_envelope_inline(envelope)
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


__all__ = ["InMemoryQuorumCoordinator"]



