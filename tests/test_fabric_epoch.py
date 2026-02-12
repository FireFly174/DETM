from __future__ import annotations

import os
import time

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric_epoch import (
    FileEpochWatermarkCoordinator,
    InMemoryEpochWatermarkCoordinator,
    ReplicatedFileEpochWatermarkCoordinator,
    commit_epoch,
    commit_watermark,
)


def _make_commit(
    commit_id: str,
    tick: int,
    *,
    node_id: str = "node-A",
    epoch: int | None = None,
    watermark: int | None = None,
) -> CommitPacket:
    summary = {}
    if epoch is not None:
        summary["epoch"] = int(epoch)
    if watermark is not None:
        summary["watermark"] = int(watermark)
    return CommitPacket.from_dict(
        {
            "commit_type": "state",
            "mode": "realtime",
            "node_id": node_id,
            "commit_id": commit_id,
            "tick_ref": {"base_level": "L0", "tick": tick},
            "delta_ref": f"artifact://delta/{tick}",
            "trace_ref": f"trace://run/{tick}",
            "summary": summary,
            "signature": f"sig://{node_id}/{tick}",
            "created_at_ms": tick,
        }
    )


def test_commit_epoch_and_watermark_fallback_to_tick():
    packet = _make_commit("node-A:1", tick=7)
    assert commit_epoch(packet) == 7
    assert commit_watermark(packet) == 7


def test_in_memory_epoch_coordinator_rejects_epoch_regression():
    coordinator = InMemoryEpochWatermarkCoordinator()
    d1 = coordinator.evaluate_commit(_make_commit("node-A:1", tick=1, epoch=1, watermark=1))
    d2 = coordinator.evaluate_commit(_make_commit("node-A:2", tick=2, epoch=0, watermark=0))
    assert d1.accepted is True
    assert d2.accepted is False
    assert "epoch regression" in str(d2.reason)


def test_in_memory_epoch_coordinator_tracks_global_epoch_and_watermark():
    coordinator = InMemoryEpochWatermarkCoordinator()
    assert coordinator.evaluate_commit(_make_commit("node-A:1", tick=1, node_id="node-A")).accepted
    assert coordinator.evaluate_commit(_make_commit("node-B:1", tick=1, node_id="node-B")).accepted
    snap = coordinator.snapshot()
    assert int(snap["node_count"]) == 2
    assert int(snap["global"]["epoch"]) == 1
    assert int(snap["global"]["watermark"]) == 1


def test_file_epoch_coordinator_shares_state_between_instances(tmp_path):
    state_path = tmp_path / "epoch_state.json"
    c1 = FileEpochWatermarkCoordinator(state_path)
    c2 = FileEpochWatermarkCoordinator(state_path)
    assert c1.evaluate_commit(_make_commit("node-A:1", tick=1, node_id="node-A")).accepted
    assert c2.evaluate_commit(_make_commit("node-B:1", tick=1, node_id="node-B")).accepted

    snap = c1.snapshot()
    assert int(snap["node_count"]) == 2
    assert int(snap["global"]["epoch"]) == 1
    assert int(snap["global"]["watermark"]) == 1
    assert str(snap["state_path"]).endswith("epoch_state.json")


def test_file_epoch_coordinator_rejects_regression_from_shared_state(tmp_path):
    state_path = tmp_path / "epoch_state.json"
    c1 = FileEpochWatermarkCoordinator(state_path)
    c2 = FileEpochWatermarkCoordinator(state_path)

    ok = c1.evaluate_commit(_make_commit("node-A:2", tick=2, node_id="node-A", epoch=2, watermark=2))
    bad = c2.evaluate_commit(_make_commit("node-A:3", tick=3, node_id="node-A", epoch=1, watermark=1))
    assert ok.accepted is True
    assert bad.accepted is False
    assert "epoch regression" in str(bad.reason)


def test_file_epoch_coordinator_rejects_when_lock_timeout_reached(tmp_path):
    state_path = tmp_path / "epoch_state.json"
    coordinator = FileEpochWatermarkCoordinator(
        state_path,
        lock_timeout_ms=20,
        lock_poll_ms=5,
        lock_stale_ms=None,
    )
    lock_path = state_path.with_suffix(".json.lock")
    lock_path.write_text("busy", encoding="utf-8")

    decision = coordinator.evaluate_commit(_make_commit("node-A:1", tick=1))
    assert decision.accepted is False
    assert "lock timeout" in str(decision.reason)


def test_file_epoch_coordinator_clears_stale_lock(tmp_path):
    state_path = tmp_path / "epoch_state.json"
    coordinator = FileEpochWatermarkCoordinator(
        state_path,
        lock_timeout_ms=200,
        lock_poll_ms=5,
        lock_stale_ms=50,
    )
    lock_path = state_path.with_suffix(".json.lock")
    lock_path.write_text("stale", encoding="utf-8")
    old = time.time() - 10.0
    os.utime(lock_path, (old, old))

    decision = coordinator.evaluate_commit(_make_commit("node-A:1", tick=1))
    assert decision.accepted is True
    snap = coordinator.snapshot()
    lock = dict(snap["lock"])
    assert str(lock["lock_path"]).endswith(".json.lock")
    assert int(lock["timeout_ms"]) == 200


def test_replicated_epoch_coordinator_accepts_with_write_quorum(tmp_path):
    paths = [tmp_path / "r1.json", tmp_path / "r2.json", tmp_path / "r3.json"]
    coordinator = ReplicatedFileEpochWatermarkCoordinator(
        state_paths=paths,
        read_quorum=2,
        write_quorum=2,
    )
    decision = coordinator.evaluate_commit(_make_commit("node-A:1", tick=1))
    assert decision.accepted is True
    snap = coordinator.snapshot()
    assert int(snap["replication"]["replica_count"]) == 3
    assert int(snap["replication"]["read_quorum"]) == 2
    assert int(snap["replication"]["write_quorum"]) == 2


def test_replicated_epoch_coordinator_rejects_when_write_quorum_not_reached(tmp_path):
    paths = [tmp_path / "r1.json", tmp_path / "r2.json", tmp_path / "r3.json"]
    coordinator = ReplicatedFileEpochWatermarkCoordinator(
        state_paths=paths,
        read_quorum=2,
        write_quorum=3,
        lock_timeout_ms=20,
        lock_poll_ms=5,
        lock_stale_ms=None,
    )
    # Block one replica lock so only 2/3 can accept.
    blocked_lock = (tmp_path / "r1.json").with_suffix(".json.lock")
    blocked_lock.write_text("busy", encoding="utf-8")
    decision = coordinator.evaluate_commit(_make_commit("node-A:1", tick=1))
    assert decision.accepted is False
    assert "write quorum not reached" in str(decision.reason)


def test_replicated_epoch_snapshot_reports_read_quorum_failure(tmp_path):
    paths = [tmp_path / "r1.json", tmp_path / "r2.json", tmp_path / "r3.json"]
    coordinator = ReplicatedFileEpochWatermarkCoordinator(
        state_paths=paths,
        read_quorum=3,
        write_quorum=2,
    )
    # Initialize 1 replica to keep at least one snapshot file.
    single = FileEpochWatermarkCoordinator(paths[0])
    assert single.evaluate_commit(_make_commit("node-A:1", tick=1)).accepted
    # Remove two replicas so snapshot can't reach quorum.
    # Simulate failures by pointing coordinators to unreadable lock-timeout state:
    lock2 = paths[1].with_suffix(".json.lock")
    lock3 = paths[2].with_suffix(".json.lock")
    lock2.write_text("busy", encoding="utf-8")
    lock3.write_text("busy", encoding="utf-8")

    # Recreate coordinator with strict short lock timeout to surface read failures quickly.
    strict = ReplicatedFileEpochWatermarkCoordinator(
        state_paths=paths,
        read_quorum=3,
        write_quorum=2,
        lock_timeout_ms=20,
        lock_poll_ms=5,
        lock_stale_ms=None,
    )
    snap = strict.snapshot()
    assert "error" in snap
    assert "read quorum not reached" in str(snap["error"])
