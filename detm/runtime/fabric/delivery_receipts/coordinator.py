"""In-memory delivery receipt coordinator."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict

from detm.runtime.fabric.delivery_receipts.contracts import DeliveryReceiptPolicy
from detm.runtime.fabric.delivery_receipts.policies import CountDeliveryReceiptPolicy, norm_status
from detm.runtime.fabric import FabricEnvelope


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
        status_by_sender[str(envelope.sender)] = norm_status(payload.get("status", "received"))

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

    def snapshot_state(self) -> Dict[str, object]:
        return {
            "status_by_delivery": {
                str(delivery_id): {
                    str(sender): str(status)
                    for sender, status in dict(status_by_sender).items()
                    if str(sender).strip()
                }
                for delivery_id, status_by_sender in dict(self._status_by_delivery).items()
                if str(delivery_id).strip()
            },
            "commit_by_delivery": {
                str(delivery_id): str(commit_ref)
                for delivery_id, commit_ref in dict(self._commit_by_delivery).items()
                if str(delivery_id).strip()
            },
            "first_seen_ms": {
                str(delivery_id): int(seen_ms)
                for delivery_id, seen_ms in dict(self._first_seen_ms).items()
                if str(delivery_id).strip()
            },
        }

    def load_snapshot(self, payload: Dict[str, object] | object) -> None:
        raw = dict(payload) if isinstance(payload, dict) else {}
        status_by_delivery: Dict[str, Dict[str, str]] = {}
        for delivery_id, status_row in dict(raw.get("status_by_delivery", {})).items():
            did = str(delivery_id).strip()
            if not did or not isinstance(status_row, dict):
                continue
            status_by_delivery[did] = {
                str(sender).strip(): norm_status(status)
                for sender, status in dict(status_row).items()
                if str(sender).strip()
            }
        commit_by_delivery: Dict[str, str] = {
            str(delivery_id).strip(): str(commit_ref)
            for delivery_id, commit_ref in dict(raw.get("commit_by_delivery", {})).items()
            if str(delivery_id).strip()
        }
        first_seen_ms: Dict[str, int] = {
            str(delivery_id).strip(): max(0, int(seen_ms))
            for delivery_id, seen_ms in dict(raw.get("first_seen_ms", {})).items()
            if str(delivery_id).strip()
        }
        self._status_by_delivery.clear()
        self._status_by_delivery.update(status_by_delivery)
        self._commit_by_delivery.clear()
        self._commit_by_delivery.update(commit_by_delivery)
        self._first_seen_ms.clear()
        self._first_seen_ms.update(first_seen_ms)


__all__ = ["InMemoryDeliveryReceiptCoordinator"]



