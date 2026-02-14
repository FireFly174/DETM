from __future__ import annotations

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck
from detm.runtime.fabric import FabricArtifactResolver
from detm.runtime.fabric import FileFabricArtifactStore


def _packet(commit_id: str, *, tick: int) -> CommitPacket:
    return CommitPacket.from_dict(
        {
            "commit_type": "state",
            "mode": "realtime",
            "node_id": "node-A",
            "commit_id": commit_id,
            "tick_ref": {"base_level": "L0", "tick": tick},
            "delta_ref": f"artifact://delta/{tick}",
            "trace_ref": f"trace://run/{tick}",
            "signature": f"sig://node-A/{tick}",
        }
    )


def test_artifact_resolver_remember_and_resolve_commit_without_store():
    resolver = FabricArtifactResolver(node_id="node-A")
    packet = _packet("node-A:1", tick=1)
    pref = resolver.remember_commit(packet, "artifact://commit/1")
    assert pref == "artifact://commit/1"
    restored = resolver.resolve_commit(pref)
    assert restored is not None
    assert restored.to_dict() == packet.to_dict()


def test_artifact_resolver_write_and_resolve_ack_without_store():
    resolver = FabricArtifactResolver(node_id="node-A")
    ack = ProofAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:1",
        status="accepted",
        signature="sig://validator-1/proof/node-A:1",
    )
    ref = resolver.write_ack(ack)
    restored = resolver.resolve_ack(ref)
    assert restored is not None
    assert restored.to_dict() == ack.to_dict()


def test_artifact_resolver_replay_check_tracks_stats():
    resolver = FabricArtifactResolver(node_id="node-A")
    packet = _packet("node-A:2", tick=2)
    resolver.remember_commit(packet, "artifact://commit/2")
    ok, reason = resolver.replay_check(packet)
    assert ok is True
    assert reason is None
    snap = resolver.replay_snapshot()
    assert int(snap["checks_total"]) == 1
    assert int(snap["checks_failed"]) == 0


def test_artifact_resolver_uses_file_artifact_store(tmp_path):
    store = FileFabricArtifactStore(tmp_path / "artifacts")
    resolver = FabricArtifactResolver(node_id="node-A", artifact_store=store)
    packet = _packet("node-A:3", tick=3)
    pref = resolver.remember_commit(packet, "artifact://commit/3")
    resolver.commit_store.clear()
    restored = resolver.resolve_commit(pref)
    assert restored is not None
    assert restored.to_dict() == packet.to_dict()

