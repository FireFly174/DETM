from __future__ import annotations

from detm.runtime.fabric_commit_delivery import FabricCommitDeliveryService
from detm.runtime.fabric_delivery import JsonlFabricEnvelopeOutbox
from detm.runtime.fabric_delivery_receipts import CountDeliveryReceiptPolicy, InMemoryDeliveryReceiptCoordinator
from detm.runtime.fabric_delivery_tracking import DeliveryTrackingCoordinator
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_transport import InMemoryFabricBus


def _commit_env(delivery_id: str, *, mode: str = "realtime") -> FabricEnvelope:
    return FabricEnvelope.from_dict(
        {
            "message_type": "commit",
            "channel": "fabric.commit",
            "mode": mode,
            "sender": "node-A",
            "payload_ref": f"artifact://commit/{delivery_id}",
            "commit_ref": f"node-A:{delivery_id}",
            "delivery_id": delivery_id,
        }
    )


def _delivery_ack_env(delivery_id: str, *, mode: str = "realtime") -> FabricEnvelope:
    return FabricEnvelope.from_dict(
        {
            "message_type": "delivery_ack",
            "channel": "fabric.delivery.ack",
            "mode": mode,
            "sender": "validator-1",
            "payload_ref": f"artifact://delivery_ack/{delivery_id}",
            "payload_inline": {"delivery_id": delivery_id, "status": "received"},
            "delivery_id": delivery_id,
            "commit_ref": f"node-A:{delivery_id}",
        }
    )


def test_commit_delivery_service_tracks_acceptance_from_delivery_ack():
    bus = InMemoryFabricBus()
    receipt = InMemoryDeliveryReceiptCoordinator(policy=CountDeliveryReceiptPolicy(required_receipts=1))
    tracker = DeliveryTrackingCoordinator(
        receipt_coordinator=receipt,
        required_receipts=1,
        tracking_enabled=True,
        retry_interval_ms=0,
        max_attempts=2,
        timeout_ms=100,
    )
    service = FabricCommitDeliveryService(transport=bus, tracker=tracker)
    service.start()

    env = _commit_env("d1")
    tracker.register_delivery(env)
    tracker.mark_publish_attempt("d1", now_ms=0)

    bus.publish(_delivery_ack_env("d1"))
    snap = service.tick()

    assert int(snap["accepted_count"]) == 1
    assert int(snap["pending_count"]) == 0
    assert len(service.delivery_ack_envelopes) == 1
    service.stop()


def test_commit_delivery_service_routes_mode_specific_delivery_ack_channels():
    bus = InMemoryFabricBus()
    service = FabricCommitDeliveryService(
        transport=bus,
        delivery_ack_channel="fabric.delivery.ack",
        delivery_ack_channels_by_mode={
            "realtime": "fabric.delivery.ack.realtime",
            "audit": "fabric.delivery.ack.audit",
        },
        mode_filter="audit",
    )
    service.start()

    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "delivery_ack",
                "channel": "fabric.delivery.ack.realtime",
                "mode": "realtime",
                "sender": "validator-rt",
                "payload_ref": "artifact://delivery_ack/rt",
                "payload_inline": {"delivery_id": "rt", "status": "received"},
                "delivery_id": "rt",
            }
        )
    )
    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "delivery_ack",
                "channel": "fabric.delivery.ack.audit",
                "mode": "audit",
                "sender": "validator-au",
                "payload_ref": "artifact://delivery_ack/au",
                "payload_inline": {"delivery_id": "au", "status": "received"},
                "delivery_id": "au",
            }
        )
    )

    assert [str(env.mode) for env in service.delivery_ack_envelopes] == ["audit"]
    service.stop()


class _DroppingCommitBus(InMemoryFabricBus):
    def publish(self, envelope: FabricEnvelope) -> int:
        if envelope.message_type == "commit":
            return 0
        return super().publish(envelope)


def test_commit_delivery_service_dead_letters_and_outbox_on_publish_drop(tmp_path):
    bus = _DroppingCommitBus()
    outbox = JsonlFabricEnvelopeOutbox(path=tmp_path / "outbox.jsonl")
    service = FabricCommitDeliveryService(
        transport=bus,
        outbox=outbox,
        commit_publish_retry_attempts=1,
    )

    ok = service.publish_commit_envelope(_commit_env("d2"), track_delivery=False)
    assert ok is False
    assert len(service.dead_letters) == 1
    assert str(service.dead_letters[0]["queued_to_outbox"]) == "true"
    assert int(outbox.snapshot()["pending_count"]) == 1
