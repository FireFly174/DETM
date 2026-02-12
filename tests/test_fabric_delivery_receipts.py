from __future__ import annotations

from detm.runtime.fabric_delivery_receipts import (
    CountDeliveryReceiptPolicy,
    InMemoryDeliveryReceiptCoordinator,
    ValidatorSetDeliveryReceiptPolicy,
)
from detm.runtime.fabric_envelope import FabricEnvelope


def test_count_delivery_receipt_policy_threshold_and_reject():
    policy = CountDeliveryReceiptPolicy(required_receipts=2, reject_on_any_reject=True)
    status, reason, details = policy.evaluate({"validator-1": "received", "validator-2": "rejected"})
    assert status == "rejected"
    assert "reject_on_any_reject" in str(reason)
    assert list(details["accepted_senders"]) == ["validator-1"]


def test_validator_set_delivery_receipt_policy_enforces_required_set():
    policy = ValidatorSetDeliveryReceiptPolicy(
        required_receipts=1,
        required_validator_ids=frozenset({"validator-1", "validator-2"}),
        enforce_required_validator_ids=True,
        reject_on_any_reject=False,
    )
    status_pending, _reason_pending, details_pending = policy.evaluate({"validator-1": "received"})
    assert status_pending == "pending"
    assert list(details_pending["missing_required_validators"]) == ["validator-2"]

    status_ok, reason_ok, details_ok = policy.evaluate({"validator-1": "received", "validator-2": "accepted"})
    assert status_ok == "accepted"
    assert reason_ok is None
    assert sorted(details_ok["accepted_senders"]) == ["validator-1", "validator-2"]


def test_delivery_receipt_coordinator_consumes_delivery_ack_envelopes():
    coordinator = InMemoryDeliveryReceiptCoordinator(policy=CountDeliveryReceiptPolicy(required_receipts=1))
    coordinator.register_delivery("d1", commit_ref="node-A:1")
    coordinator.on_delivery_ack_envelope(
        FabricEnvelope.from_dict(
            {
                "message_type": "delivery_ack",
                "channel": "fabric.delivery.ack",
                "mode": "realtime",
                "sender": "validator-1",
                "payload_ref": "artifact://delivery_ack/1",
                "payload_inline": {"delivery_id": "d1", "status": "received"},
                "delivery_id": "d1",
                "commit_ref": "node-A:1",
            }
        )
    )

    row = coordinator.evaluate("d1")
    assert row["status"] == "accepted"
    assert row["commit_ref"] == "node-A:1"
    assert row["status_by_sender"] == {"validator-1": "accepted"}
