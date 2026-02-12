"""Delivery receipt policy/coordinator primitives for commit envelope tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Mapping, Protocol, Sequence

from detm.runtime.fabric_envelope import FabricEnvelope

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (policy + coordinator abstraction exists)
# - OOP_TECH_DEBT: replicated durable coordinator and cross-node consensus integration


def _norm_status(value: object) -> str:
    raw = str(value).strip().lower()
    if raw in {"received", "accepted", "ok"}:
        return "accepted"
    if raw in {"rejected", "reject", "error", "failed"}:
        return "rejected"
    return "unknown"


def _norm_validator_set(values: Sequence[str] | None) -> FrozenSet[str]:
    if not values:
        return frozenset()
    return frozenset(str(v).strip() for v in values if str(v).strip())


class DeliveryReceiptPolicy(Protocol):
    """Policy deciding delivery status from per-sender receipt statuses."""

    def evaluate(self, status_by_sender: Mapping[str, str]) -> tuple[str, str | None, Dict[str, object]]:
        ...


@dataclass(frozen=True)
class CountDeliveryReceiptPolicy:
    """Count-based receipt policy with optional reject-on-any-reject semantics."""

    required_receipts: int = 1
    reject_on_any_reject: bool = False

    def evaluate(self, status_by_sender: Mapping[str, str]) -> tuple[str, str | None, Dict[str, object]]:
        accepted = sorted(str(s) for s, st in dict(status_by_sender).items() if _norm_status(st) == "accepted")
        rejected = sorted(str(s) for s, st in dict(status_by_sender).items() if _norm_status(st) == "rejected")
        if bool(self.reject_on_any_reject) and rejected:
            return (
                "rejected",
                "delivery rejected by at least one receipt under reject_on_any_reject policy",
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": [],
                },
            )
        if len(accepted) >= int(self.required_receipts):
            return (
                "accepted",
                None,
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": [],
                },
            )
        return (
            "pending",
            "delivery receipt threshold not reached",
            {
                "accepted_senders": accepted,
                "rejected_senders": rejected,
                "required_receipts": int(self.required_receipts),
                "missing_required_validators": [],
            },
        )


@dataclass(frozen=True)
class ValidatorSetDeliveryReceiptPolicy:
    """Count policy extended with required validator set enforcement."""

    required_receipts: int = 1
    required_validator_ids: FrozenSet[str] = field(default_factory=frozenset)
    enforce_required_validator_ids: bool = False
    reject_on_any_reject: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_validator_ids", _norm_validator_set(self.required_validator_ids))

    def evaluate(self, status_by_sender: Mapping[str, str]) -> tuple[str, str | None, Dict[str, object]]:
        accepted = sorted(str(s) for s, st in dict(status_by_sender).items() if _norm_status(st) == "accepted")
        rejected = sorted(str(s) for s, st in dict(status_by_sender).items() if _norm_status(st) == "rejected")
        if bool(self.reject_on_any_reject) and rejected:
            return (
                "rejected",
                "delivery rejected by at least one receipt under reject_on_any_reject policy",
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": sorted(self.required_validator_ids.difference(set(accepted))),
                },
            )

        if len(accepted) < int(self.required_receipts):
            return (
                "pending",
                "delivery receipt threshold not reached",
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": sorted(self.required_validator_ids.difference(set(accepted))),
                },
            )

        missing_required = sorted(self.required_validator_ids.difference(set(accepted)))
        if bool(self.enforce_required_validator_ids) and missing_required:
            return (
                "pending",
                f"required delivery validator set missing: {missing_required}",
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": missing_required,
                },
            )
        return (
            "accepted",
            None,
            {
                "accepted_senders": accepted,
                "rejected_senders": rejected,
                "required_receipts": int(self.required_receipts),
                "missing_required_validators": missing_required,
            },
        )


@dataclass
class InMemoryDeliveryReceiptCoordinator:
    """Aggregates delivery_ack envelopes and evaluates receipt status per delivery id."""

    policy: DeliveryReceiptPolicy = field(default_factory=CountDeliveryReceiptPolicy)
    _status_by_delivery: Dict[str, Dict[str, str]] = field(default_factory=dict)
    _commit_by_delivery: Dict[str, str] = field(default_factory=dict)
    _first_seen_ms: Dict[str, int] = field(default_factory=dict)

    def register_delivery(self, delivery_id: str, *, commit_ref: str, created_at_ms: int | None = None) -> None:
        did = str(delivery_id).strip()
        if not did:
            return
        self._status_by_delivery.setdefault(did, {})
        self._commit_by_delivery.setdefault(did, str(commit_ref))
        if did not in self._first_seen_ms:
            self._first_seen_ms[did] = int(created_at_ms) if created_at_ms is not None else int(time.time() * 1000)

    def on_delivery_ack_envelope(self, envelope: FabricEnvelope) -> None:
        if envelope.message_type != "delivery_ack":
            return
        payload = envelope.payload_inline if isinstance(envelope.payload_inline, dict) else {}
        delivery_id = str(payload.get("delivery_id", envelope.delivery_id or "")).strip()
        if not delivery_id:
            return
        commit_ref = str(payload.get("commit_ref", envelope.commit_ref or ""))
        self.register_delivery(delivery_id, commit_ref=commit_ref)
        status_by_sender = self._status_by_delivery.setdefault(delivery_id, {})
        status_by_sender[str(envelope.sender)] = _norm_status(payload.get("status", "received"))

    def evaluate(self, delivery_id: str) -> Dict[str, object]:
        did = str(delivery_id).strip()
        if not did:
            return {
                "delivery_id": "",
                "commit_ref": "",
                "status": "rejected",
                "reason": "empty delivery_id",
                "accepted_senders": [],
                "rejected_senders": [],
                "missing_required_validators": [],
                "status_by_sender": {},
            }
        status_by_sender = dict(self._status_by_delivery.get(did, {}))
        status, reason, details = self.policy.evaluate(status_by_sender)
        return {
            "delivery_id": did,
            "commit_ref": str(self._commit_by_delivery.get(did, "")),
            "status": str(status),
            "reason": None if reason is None else str(reason),
            "accepted_senders": list(details.get("accepted_senders", [])),
            "rejected_senders": list(details.get("rejected_senders", [])),
            "missing_required_validators": list(details.get("missing_required_validators", [])),
            "status_by_sender": status_by_sender,
        }

    def remove(self, delivery_id: str) -> None:
        did = str(delivery_id).strip()
        if not did:
            return
        self._status_by_delivery.pop(did, None)
        self._commit_by_delivery.pop(did, None)
        self._first_seen_ms.pop(did, None)

    def snapshot(self) -> Dict[str, object]:
        rows = [self.evaluate(did) for did in sorted(self._status_by_delivery.keys())]
        return {
            "delivery_count": len(rows),
            "accepted_count": sum(1 for row in rows if row.get("status") == "accepted"),
            "pending_count": sum(1 for row in rows if row.get("status") == "pending"),
            "rejected_count": sum(1 for row in rows if row.get("status") == "rejected"),
            "evaluations": rows,
        }


__all__ = [
    "CountDeliveryReceiptPolicy",
    "DeliveryReceiptPolicy",
    "InMemoryDeliveryReceiptCoordinator",
    "ValidatorSetDeliveryReceiptPolicy",
]
