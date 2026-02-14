from __future__ import annotations

import pytest

from detm.runtime.commit_chain import CommitChainManager
from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.schemas import DETM_FABRIC_ENVELOPE_V1, get_schema_versions


def _make_commit(commit_id: str, tick: int, parent_ref: str | None = None) -> CommitPacket:
    return CommitPacket.from_dict(
        {
            "commit_type": "state",
            "mode": "realtime",
            "node_id": "node-A",
            "commit_id": commit_id,
            "parent_ref": parent_ref,
            "tick_ref": {"base_level": "L0", "tick": tick},
            "delta_ref": f"artifact://delta/{tick}",
            "trace_ref": f"trace://run/{tick}",
            "signature": f"sig://node-A/{tick}",
        }
    )


def test_fabric_envelope_roundtrip_and_schema_registry():
    payload = {
        "schema_version": DETM_FABRIC_ENVELOPE_V1,
        "message_type": "commit",
        "channel": "fabric.commit.realtime",
        "mode": "realtime",
        "sender": "node-A",
        "recipient": "validator-1",
        "payload_ref": "artifact://commit/node-A/42",
        "payload_inline": {"commit_id": "node-A:42", "meta": {"bridge": True}},
        "trace_ref": "trace://run/42",
        "commit_ref": "node-A:42",
        "auth_key_id": "kid-42",
        "transport_identity": "cn:node-A",
    }
    envelope = FabricEnvelope.from_dict(payload)
    restored = FabricEnvelope.from_dict(envelope.to_dict())

    assert restored.channel == "fabric.commit.realtime"
    assert restored.payload_ref == "artifact://commit/node-A/42"
    assert isinstance(restored.payload_inline, dict)
    assert dict(restored.payload_inline)["commit_id"] == "node-A:42"
    assert restored.auth_key_id == "kid-42"
    assert restored.transport_identity == "cn:node-A"
    assert get_schema_versions()["fabric_envelope"] == DETM_FABRIC_ENVELOPE_V1


def test_commit_chain_manager_sequences_parent_links():
    manager = CommitChainManager(node_id="node-A")
    first = manager.sequence(_make_commit("node-A:1", tick=1))
    second = manager.sequence(_make_commit("node-A:2", tick=2))

    assert first.parent_ref is None
    assert second.parent_ref == "node-A:1"
    assert manager.tail_ref == "node-A:2"


def test_commit_chain_manager_rejects_wrong_parent():
    manager = CommitChainManager(node_id="node-A")
    manager.sequence(_make_commit("node-A:1", tick=1))

    with pytest.raises(ValueError, match="parent mismatch"):
        manager.accept(_make_commit("node-A:2", tick=2, parent_ref="node-A:999"))


def test_commit_chain_manager_rejects_non_monotonic_tick():
    manager = CommitChainManager(node_id="node-A")
    manager.sequence(_make_commit("node-A:10", tick=10))

    with pytest.raises(ValueError, match="monotonic"):
        manager.accept(_make_commit("node-A:11", tick=9, parent_ref="node-A:10"))

