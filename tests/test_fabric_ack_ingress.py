from __future__ import annotations

from detm.runtime.fabric_ack_ingress import FabricAckIngressService
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_transport import InMemoryFabricBus


def _ack_env(*, channel: str = "fabric.ack", mode: str = "realtime", sender: str = "validator-1") -> FabricEnvelope:
    return FabricEnvelope.from_dict(
        {
            "message_type": "proof_ack",
            "channel": channel,
            "mode": mode,
            "sender": sender,
            "payload_ref": f"artifact://ack/{sender}/{mode}",
            "commit_ref": "node-A:1",
        }
    )


class _Collector:
    def __init__(self) -> None:
        self.rows: list[FabricEnvelope] = []

    def on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        self.rows.append(envelope)


def test_ack_ingress_subscribes_mode_specific_channels():
    bus = InMemoryFabricBus()
    collector = _Collector()
    service = FabricAckIngressService(
        transport=bus,
        ack_channel="fabric.ack",
        ack_channels_by_mode={
            "realtime": "fabric.ack.realtime",
            "audit": "fabric.ack.audit",
        },
        mode_filter="audit",
        consumer=collector,
    )
    service.start()

    bus.publish(_ack_env(channel="fabric.ack.realtime", mode="realtime"))
    bus.publish(_ack_env(channel="fabric.ack.audit", mode="audit"))

    assert [str(env.mode) for env in service.ack_envelopes] == ["audit"]
    assert [str(env.mode) for env in collector.rows] == ["audit"]
    service.stop()


def test_ack_ingress_forwards_envelopes_to_consumer():
    bus = InMemoryFabricBus()
    collector = _Collector()
    service = FabricAckIngressService(transport=bus, consumer=collector)
    service.start()

    bus.publish(_ack_env())

    assert len(service.ack_envelopes) == 1
    assert len(collector.rows) == 1
    assert str(collector.rows[0].message_type) == "proof_ack"
    service.stop()


def test_ack_ingress_stop_unsubscribes_handlers():
    bus = InMemoryFabricBus()
    service = FabricAckIngressService(transport=bus)
    service.start()
    service.stop()

    bus.publish(_ack_env())

    assert service.ack_envelopes == []
