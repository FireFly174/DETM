from __future__ import annotations

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric_artifact_resolver import FabricArtifactResolver
from detm.runtime.fabric_commit_delivery import FabricCommitDeliveryService
from detm.runtime.fabric_commit_ingress import FabricCommitIngressService
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_transport import InMemoryFabricBus


def _packet(*, commit_id: str, mode: str = "realtime") -> CommitPacket:
    return CommitPacket.from_dict(
        {
            "schema_version": "detm.commit_packet.v1",
            "commit_type": "state",
            "mode": mode,
            "node_id": "node-A",
            "commit_id": commit_id,
            "parent_ref": None,
            "tick_ref": {"base_level": "L0", "tick": 1},
            "inputs_ref": "artifact://inputs/1",
            "delta_ref": "artifact://delta/1",
            "invariants_ref": None,
            "trace_ref": "trace://L0/1",
            "summary": {},
            "signature": "sig:node-A",
            "created_at_ms": 1,
        }
    )


class _QuorumStub:
    def __init__(self) -> None:
        self.registered: list[str] = []

    def register_commit(self, commit_id: str) -> None:
        self.registered.append(str(commit_id))


def test_commit_ingress_service_publishes_commit_envelope_and_registers_quorum():
    bus = InMemoryFabricBus()
    captured: list[FabricEnvelope] = []
    bus.subscribe("fabric.commit", captured.append)

    resolver = FabricArtifactResolver(node_id="node-A")
    delivery = FabricCommitDeliveryService(transport=bus)
    quorum = _QuorumStub()
    ingress = FabricCommitIngressService(
        artifact_resolver=resolver,
        delivery_runtime=delivery,
        commit_channel="fabric.commit",
        delivery_required_receipts=1,
        publish_inline_payload=True,
        quorum_runtime=quorum,
    )
    packet = _packet(commit_id="node-A:1")

    ok = ingress.on_commit_packet(
        packet=packet,
        payload_ref="artifact://commit/node-A/1",
        mode="realtime",
        trace_ref="trace://L0/1",
    )

    assert ok is True
    assert ingress.delivery_counter == 1
    assert quorum.registered == ["node-A:1"]
    assert len(captured) == 1
    envelope = captured[0]
    assert envelope.channel == "fabric.commit"
    assert envelope.payload_ref == "artifact://commit/node-A/1"
    assert envelope.delivery_id == "node-A:node-A:1:1"
    assert envelope.payload_inline == packet.to_dict()
    assert resolver.resolve_commit("artifact://commit/node-A/1") == packet


def test_commit_ingress_service_routes_channel_by_mode():
    bus = InMemoryFabricBus()
    captured_realtime: list[FabricEnvelope] = []
    captured_audit: list[FabricEnvelope] = []
    bus.subscribe("fabric.commit", captured_realtime.append, mode="realtime")
    bus.subscribe("fabric.commit.audit", captured_audit.append, mode="audit")

    ingress = FabricCommitIngressService(
        artifact_resolver=FabricArtifactResolver(node_id="node-A"),
        delivery_runtime=FabricCommitDeliveryService(transport=bus),
        commit_channel="fabric.commit",
        commit_channels_by_mode={"audit": "fabric.commit.audit"},
        delivery_required_receipts=0,
        publish_inline_payload=True,
    )

    ok_realtime = ingress.on_commit_packet(
        packet=_packet(commit_id="node-A:2", mode="realtime"),
        payload_ref="artifact://commit/node-A/2",
        mode="realtime",
    )
    ok_audit = ingress.on_commit_packet(
        packet=_packet(commit_id="node-A:3", mode="audit"),
        payload_ref="artifact://commit/node-A/3",
        mode="audit",
    )

    assert ok_realtime is True
    assert ok_audit is True
    assert [env.channel for env in captured_realtime] == ["fabric.commit"]
    assert [env.channel for env in captured_audit] == ["fabric.commit.audit"]


def test_commit_ingress_service_without_receipts_omits_delivery_id_and_inline_payload():
    bus = InMemoryFabricBus()
    captured: list[FabricEnvelope] = []
    bus.subscribe("fabric.commit", captured.append)

    ingress = FabricCommitIngressService(
        artifact_resolver=FabricArtifactResolver(node_id="node-A"),
        delivery_runtime=FabricCommitDeliveryService(transport=bus),
        commit_channel="fabric.commit",
        delivery_required_receipts=0,
        publish_inline_payload=False,
    )

    ok = ingress.on_commit_packet(
        packet=_packet(commit_id="node-A:4"),
        payload_ref="artifact://commit/node-A/4",
        mode="realtime",
    )

    assert ok is True
    assert ingress.delivery_counter == 0
    assert len(captured) == 1
    envelope = captured[0]
    assert envelope.delivery_id is None
    assert envelope.payload_inline is None
