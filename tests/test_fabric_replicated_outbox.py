from __future__ import annotations

from pathlib import Path

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import ReplicatedJsonlFabricEnvelopeOutbox


def _env(commit_ref: str) -> FabricEnvelope:
    return FabricEnvelope.from_dict(
        {
            "message_type": "commit",
            "channel": "fabric.commit",
            "mode": "realtime",
            "sender": "node-A",
            "payload_ref": f"artifact://commit/{commit_ref}",
            "commit_ref": commit_ref,
        }
    )


def test_replicated_outbox_flush_replicates_state_to_all_replicas(tmp_path):
    paths = [tmp_path / "r1.jsonl", tmp_path / "r2.jsonl", tmp_path / "r3.jsonl"]
    outbox = ReplicatedJsonlFabricEnvelopeOutbox(
        paths=[str(p) for p in paths],
        read_quorum=2,
        write_quorum=2,
    )
    outbox.enqueue(_env("1"))
    outbox.enqueue(_env("2"))

    seen: list[str] = []
    report = outbox.flush(lambda env: seen.append(str(env.commit_ref)) or 1)

    assert seen == ["1", "2"]
    assert int(report["sent"]) == 2
    assert int(report["write_quorum_reached"]) == 1
    assert int(report["read_quorum_reached"]) == 1
    assert int(report["remaining"]) == 0
    bodies = [Path(p).read_text(encoding="utf-8") for p in paths]
    assert len(set(bodies)) == 1
    snap = outbox.snapshot()
    assert str(snap.get("mode")) == "replicated"
    assert int(snap.get("replica_count", 0)) == 3


def test_replicated_outbox_reports_read_quorum_failure(monkeypatch, tmp_path):
    outbox = ReplicatedJsonlFabricEnvelopeOutbox(
        paths=[str(tmp_path / "r1.jsonl"), str(tmp_path / "r2.jsonl"), str(tmp_path / "r3.jsonl")],
        read_quorum=3,
        write_quorum=2,
    )
    outbox.enqueue(_env("1"))

    # Simulate two unavailable replicas.
    for _, replica in outbox._replicas[1:]:
        monkeypatch.setattr(replica, "snapshot", lambda: (_ for _ in ()).throw(RuntimeError("offline")))

    report = outbox.flush(lambda _env: 1)
    assert int(report["read_quorum_reached"]) == 0
    assert int(report["write_quorum_reached"]) == 0
    assert int(report["failed"]) == 1
