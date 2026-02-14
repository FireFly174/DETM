from __future__ import annotations

from detm.runtime.fabric import FabricCommitDeliveryService
from detm.runtime.fabric import JsonlFabricEnvelopeOutbox
from detm.runtime.fabric import CountDeliveryReceiptPolicy, InMemoryDeliveryReceiptCoordinator
from detm.runtime.fabric import DeliveryTrackingCoordinator
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import InMemoryFabricBus


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


def test_commit_delivery_service_retry_accepts_after_late_delivery_ack():
    bus = InMemoryFabricBus()
    receipt = InMemoryDeliveryReceiptCoordinator(policy=CountDeliveryReceiptPolicy(required_receipts=1))
    tracker = DeliveryTrackingCoordinator(
        receipt_coordinator=receipt,
        required_receipts=1,
        tracking_enabled=True,
        retry_interval_ms=0,
        max_attempts=3,
        timeout_ms=1000,
    )
    service = FabricCommitDeliveryService(
        transport=bus,
        tracker=tracker,
        commit_publish_retry_attempts=1,
    )
    service.start()

    commit_deliveries: list[str] = []

    def _on_commit(env: FabricEnvelope) -> None:
        delivery_id = str(env.delivery_id or "")
        if not delivery_id:
            return
        commit_deliveries.append(delivery_id)
        if len(commit_deliveries) == 2:
            bus.publish(_delivery_ack_env(delivery_id))

    bus.subscribe("fabric.commit", _on_commit, mode="realtime")
    env = _commit_env("d-retry")

    ok = service.publish_commit_envelope(env, track_delivery=True)
    assert ok is True
    assert commit_deliveries == ["d-retry"]

    snap_after_retry = service.tick()
    assert int(snap_after_retry["pending_count"]) == 1
    assert int(snap_after_retry["retries_total"]) == 1

    snap_after_ack = service.tick()
    assert int(snap_after_ack["accepted_count"]) == 1
    assert int(snap_after_ack["pending_count"]) == 0
    assert commit_deliveries == ["d-retry", "d-retry"]
    service.stop()


def test_commit_delivery_outbox_replay_after_restart_and_dedup_drops_duplicate_ingress(tmp_path):
    outbox_path = tmp_path / "outbox.jsonl"
    outbox = JsonlFabricEnvelopeOutbox(path=outbox_path)
    env = _commit_env("d-crash")

    # Simulate crash path: publish fails and commit envelope is persisted into outbox.
    failed_service = FabricCommitDeliveryService(
        transport=_DroppingCommitBus(),
        outbox=outbox,
        commit_publish_retry_attempts=1,
    )
    ok = failed_service.publish_commit_envelope(env, track_delivery=False)
    assert ok is False
    assert int(outbox.snapshot()["pending_count"]) == 1

    # Simulate restart path: same outbox is replayed into a dedup-enabled ingress transport.
    restart_bus = InMemoryFabricBus(dedup_ingress_enabled=True, dedup_ttl_ms=60_000, dedup_max_entries=128)
    received_refs: list[str] = []
    restart_bus.subscribe("fabric.commit", lambda row: received_refs.append(str(row.commit_ref)), mode="realtime")
    recovered_outbox = JsonlFabricEnvelopeOutbox(path=outbox_path)
    recovered_service = FabricCommitDeliveryService(
        transport=restart_bus,
        outbox=recovered_outbox,
    )
    recovered_service.start()
    try:
        assert received_refs == ["node-A:d-crash"]
        assert int(recovered_outbox.snapshot()["pending_count"]) == 0

        delivered_duplicate = restart_bus.publish(env)
        assert delivered_duplicate == 0
        assert received_refs == ["node-A:d-crash"]
        dedup = dict(restart_bus.snapshot().get("dedup", {}))
        assert bool(dedup.get("enabled")) is True
        assert int(dedup.get("duplicates_total", 0)) == 1
    finally:
        recovered_service.stop()

