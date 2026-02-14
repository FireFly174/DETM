from __future__ import annotations

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FileFabricArtifactStore


def _make_commit(commit_id: str, tick: int) -> CommitPacket:
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


def test_file_fabric_artifact_store_roundtrip_commit_and_ack(tmp_path):
    store = FileFabricArtifactStore(tmp_path / "shared")
    commit = _make_commit("node-A:1", tick=1)
    proof = ProofAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:1",
        status="accepted",
        signature="sig://validator-1/proof/1",
    )
    trust = TrustAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:1",
        status="accepted",
        signature="sig://validator-1/trust/1",
    )

    cref = store.write_commit(commit)
    pref = store.write_ack(proof)
    tref = store.write_ack(trust)

    restored_commit = store.read_commit(cref)
    restored_proof = store.read_ack(pref)
    restored_trust = store.read_ack(tref)

    assert restored_commit is not None
    assert restored_commit.commit_id == "node-A:1"
    assert isinstance(restored_proof, ProofAck)
    assert isinstance(restored_trust, TrustAck)
    assert store.read_commit("artifact://missing/commit") is None
    assert store.read_ack("artifact://missing/ack") is None

