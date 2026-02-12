from __future__ import annotations

from detm.runtime.fabric_delivery_receipts import CountDeliveryReceiptPolicy, InMemoryDeliveryReceiptCoordinator
from detm.runtime.fabric_delivery_tracking import DeliveryTrackingCoordinator
from detm.runtime.fabric_envelope import FabricEnvelope


def _commit_env(delivery_id: str) -> FabricEnvelope:
    return FabricEnvelope.from_dict(
        {
            "message_type": "commit",
            "channel": "fabric.commit",
            "mode": "realtime",
            "sender": "node-A",
            "payload_ref": f"artifact://commit/{delivery_id}",
            "commit_ref": f"node-A:{delivery_id}",
            "delivery_id": delivery_id,
        }
    )


def _delivery_ack_env(delivery_id: str, *, status: str = "received", sender: str = "validator-1") -> FabricEnvelope:
    return FabricEnvelope.from_dict(
        {
            "message_type": "delivery_ack",
            "channel": "fabric.delivery.ack",
            "mode": "realtime",
            "sender": sender,
            "payload_ref": f"artifact://delivery_ack/{delivery_id}",
            "payload_inline": {"delivery_id": delivery_id, "status": status},
            "delivery_id": delivery_id,
            "commit_ref": f"node-A:{delivery_id}",
        }
    )


def test_delivery_tracking_accepts_when_receipt_policy_accepts():
    receipt = InMemoryDeliveryReceiptCoordinator(policy=CountDeliveryReceiptPolicy(required_receipts=1))
    tracker = DeliveryTrackingCoordinator(
        receipt_coordinator=receipt,
        required_receipts=1,
        tracking_enabled=True,
        retry_interval_ms=0,
        max_attempts=2,
        timeout_ms=100,
    )
    env = _commit_env("d1")
    did = tracker.register_delivery(env)
    assert did == "d1"
    tracker.mark_publish_attempt("d1", now_ms=10)
    tracker.on_delivery_ack_envelope(_delivery_ack_env("d1", status="received"))
    tracker.tick(lambda _env: True, now_ms=20)
    snap = tracker.snapshot()
    assert int(snap["accepted_count"]) == 1
    assert int(snap["pending_count"]) == 0


def test_delivery_tracking_retries_and_rejects_on_max_attempts():
    receipt = InMemoryDeliveryReceiptCoordinator(policy=CountDeliveryReceiptPolicy(required_receipts=1))
    tracker = DeliveryTrackingCoordinator(
        receipt_coordinator=receipt,
        required_receipts=1,
        tracking_enabled=True,
        retry_interval_ms=0,
        max_attempts=2,
        timeout_ms=1000,
    )
    env = _commit_env("d2")
    tracker.register_delivery(env)
    tracker.mark_publish_attempt("d2", now_ms=10)
    tracker.tick(lambda _env: True, now_ms=20)
    snap = tracker.snapshot()
    assert int(snap["retries_total"]) == 1
    assert int(snap["rejected_count"]) == 1
    assert int(snap["pending_count"]) == 0


def test_delivery_tracking_rejects_by_timeout():
    receipt = InMemoryDeliveryReceiptCoordinator(policy=CountDeliveryReceiptPolicy(required_receipts=1))
    tracker = DeliveryTrackingCoordinator(
        receipt_coordinator=receipt,
        required_receipts=1,
        tracking_enabled=True,
        retry_interval_ms=0,
        max_attempts=10,
        timeout_ms=5,
    )
    env = _commit_env("d3")
    tracker.register_delivery(env, now_ms=0)
    tracker.mark_publish_attempt("d3", now_ms=0)
    tracker.tick(lambda _env: False, now_ms=10)
    snap = tracker.snapshot()
    assert int(snap["rejected_count"]) == 1
    assert int(snap["pending_count"]) == 0
