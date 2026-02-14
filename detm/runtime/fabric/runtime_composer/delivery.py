"""Delivery-related builders for fabric runtime composition."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detm.runtime.fabric import (
    CountDeliveryReceiptPolicy,
    DeliveryTrackingCoordinator,
    InMemoryDeliveryReceiptCoordinator,
    JsonlFabricEnvelopeOutbox,
    OUTBOX_DROP_POLICIES,
    ReplicatedJsonlFabricEnvelopeOutbox,
    ValidatorSetDeliveryReceiptPolicy,
)


def build_delivery_receipt_policy(*, rec: Any):
    if bool(rec.delivery_enforce_required_validator_ids) or bool(list(rec.delivery_required_validator_ids or [])):
        return ValidatorSetDeliveryReceiptPolicy(
            required_receipts=max(0, int(rec.delivery_required_receipts)),
            required_validator_ids=frozenset(str(v).strip() for v in list(rec.delivery_required_validator_ids or [])),
            enforce_required_validator_ids=bool(rec.delivery_enforce_required_validator_ids),
            reject_on_any_reject=bool(rec.delivery_reject_on_any_reject),
        )
    return CountDeliveryReceiptPolicy(
        required_receipts=max(0, int(rec.delivery_required_receipts)),
        reject_on_any_reject=bool(rec.delivery_reject_on_any_reject),
    )


def build_delivery_tracker(
    *,
    rec: Any,
    delivery_pending: dict[str, dict[str, Any]],
    delivery_tracking_state_path: Path,
    delivery_receipt_coordinator: InMemoryDeliveryReceiptCoordinator,
) -> DeliveryTrackingCoordinator:
    return DeliveryTrackingCoordinator(
        receipt_coordinator=delivery_receipt_coordinator,
        required_receipts=max(0, int(rec.delivery_required_receipts)),
        retry_interval_ms=max(0, int(rec.delivery_retry_interval_ms)),
        max_attempts=max(1, int(rec.delivery_max_attempts)),
        timeout_ms=max(1, int(rec.delivery_timeout_ms)),
        tracking_enabled=bool(
            int(rec.delivery_required_receipts) > 0
            or (bool(rec.delivery_enforce_required_validator_ids) and bool(list(rec.delivery_required_validator_ids or [])))
            or bool(rec.delivery_reject_on_any_reject)
        ),
        pending=delivery_pending,
        state_path=str(delivery_tracking_state_path),
    )


def build_delivery_outbox(*, rec: Any):
    outbox_drop_policy = (
        str(rec.delivery_outbox_drop_policy).strip().lower()
        if str(rec.delivery_outbox_drop_policy).strip().lower() in OUTBOX_DROP_POLICIES
        else "audit_first"
    )
    outbox_replica_paths = [str(v).strip() for v in list(getattr(rec, "delivery_outbox_replica_paths", []) or [])]
    if outbox_replica_paths:
        return ReplicatedJsonlFabricEnvelopeOutbox(
            paths=outbox_replica_paths,
            read_quorum=getattr(rec, "delivery_outbox_replica_read_quorum", None),
            write_quorum=getattr(rec, "delivery_outbox_replica_write_quorum", None),
            max_entries=rec.delivery_outbox_max_entries,
            drop_policy=outbox_drop_policy,
        )
    outbox_path = (
        Path(rec.delivery_outbox_path)
        if rec.delivery_outbox_path is not None
        else Path(rec.out_dir) / "fabric_delivery_outbox.jsonl"
    )
    return JsonlFabricEnvelopeOutbox(
        path=Path(outbox_path),
        max_entries=rec.delivery_outbox_max_entries,
        drop_policy=outbox_drop_policy,
    )


__all__ = [
    "build_delivery_outbox",
    "build_delivery_receipt_policy",
    "build_delivery_tracker",
]
