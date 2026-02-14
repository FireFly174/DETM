from __future__ import annotations

import pytest

from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import InMemoryFabricBus
from detm.runtime.schemas import DETM_FABRIC_ACK_V1, get_schema_versions


def test_fabric_ack_roundtrip_and_schema_registry():
    proof_payload = {
        "schema_version": DETM_FABRIC_ACK_V1,
        "ack_type": "proof_ack",
        "validator_id": "validator-1",
        "node_id": "node-A",
        "commit_ref": "node-A:42",
        "status": "accepted",
        "proof_ref": "artifact://proof/42",
        "epoch": 4,
        "watermark": 42,
        "signature": "sig://validator-1/42",
        "created_at_ms": 123456,
    }
    trust_payload = {
        "schema_version": DETM_FABRIC_ACK_V1,
        "ack_type": "trust_ack",
        "validator_id": "validator-1",
        "node_id": "node-A",
        "commit_ref": "node-A:42",
        "status": "accepted",
        "trust_ref": "artifact://trust/validator-1/node-A",
        "signature": "sig://validator-1/trust-42",
        "created_at_ms": 123457,
    }

    proof = ProofAck.from_dict(proof_payload)
    trust = TrustAck.from_dict(trust_payload)

    assert ProofAck.from_dict(proof.to_dict()).commit_ref == "node-A:42"
    assert TrustAck.from_dict(trust.to_dict()).trust_ref == "artifact://trust/validator-1/node-A"
    assert get_schema_versions()["fabric_ack"] == DETM_FABRIC_ACK_V1


def test_fabric_ack_rejects_wrong_ack_type():
    payload = {
        "ack_type": "trust_ack",
        "validator_id": "validator-1",
        "node_id": "node-A",
        "commit_ref": "node-A:42",
        "status": "accepted",
        "signature": "sig://validator-1/42",
    }
    with pytest.raises(ValueError, match="proof_ack"):
        ProofAck.from_dict(payload)


def test_in_memory_fabric_bus_routes_by_channel_and_mode():
    bus = InMemoryFabricBus()
    calls: list[str] = []

    def on_realtime(_envelope: FabricEnvelope) -> None:
        calls.append("realtime")

    def on_channel_any_mode(_envelope: FabricEnvelope) -> None:
        calls.append("channel-any")

    def on_global(_envelope: FabricEnvelope) -> None:
        calls.append("global")

    bus.subscribe("fabric.commit", on_realtime, mode="realtime")
    bus.subscribe("fabric.commit", on_channel_any_mode)
    bus.subscribe("*", on_global)

    realtime = FabricEnvelope.from_dict(
        {
            "message_type": "commit",
            "channel": "fabric.commit",
            "mode": "realtime",
            "sender": "node-A",
            "payload_ref": "artifact://commit/node-A/1",
        }
    )
    audit = FabricEnvelope.from_dict(
        {
            "message_type": "commit",
            "channel": "fabric.commit",
            "mode": "audit",
            "sender": "node-A",
            "payload_ref": "artifact://commit/node-A/2",
        }
    )

    delivered_realtime = bus.publish(realtime)
    delivered_audit = bus.publish(audit)

    assert delivered_realtime == 3
    assert delivered_audit == 2
    assert calls == ["channel-any", "realtime", "global", "channel-any", "global"]


def test_in_memory_fabric_bus_dedup_ingress_drops_duplicate_delivery_id():
    bus = InMemoryFabricBus(dedup_ingress_enabled=True, dedup_ttl_ms=60_000, dedup_max_entries=128)
    calls: list[str] = []
    bus.subscribe("fabric.commit", lambda _envelope: calls.append("hit"), mode="realtime")

    env = FabricEnvelope.from_dict(
        {
            "message_type": "commit",
            "channel": "fabric.commit",
            "mode": "realtime",
            "sender": "node-A",
            "payload_ref": "artifact://commit/node-A/1",
            "commit_ref": "node-A:1",
            "delivery_id": "node-A:1:1",
        }
    )
    delivered_first = bus.publish(env)
    delivered_second = bus.publish(env)

    assert delivered_first == 1
    assert delivered_second == 0
    assert calls == ["hit"]
    snap = bus.snapshot()
    dedup = dict(snap.get("dedup", {}))
    assert bool(dedup.get("enabled")) is True
    assert int(dedup.get("duplicates_total", 0)) == 1

