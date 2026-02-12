from __future__ import annotations

import json

from detm_app.session import DetmSession
from detm_app.subscribers import CommitJsonlWriter, JsonlTraceWriter
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy


def test_commit_writer_links_to_trace_refs(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=2, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=5)
    trace_path = tmp_path / "trace.jsonl"
    commits_path = tmp_path / "commits.jsonl"

    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])
    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-test", mode="realtime")

    for _ in range(5):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    trace_entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    commit_entries = [json.loads(line) for line in commits_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert [entry["tick"] for entry in trace_entries] == [2, 4]
    assert [entry["tick_ref"]["tick"] for entry in commit_entries] == [2, 4]
    assert [entry["trace_ref"] for entry in commit_entries] == [entry["trace_ref"] for entry in trace_entries]
    assert commit_entries[0]["parent_ref"] is None
    assert commit_entries[1]["parent_ref"] == commit_entries[0]["commit_id"]
    assert all(entry["commit_type"] == "state" for entry in commit_entries)
    assert all(entry["mode"] == "realtime" for entry in commit_entries)
    assert [int(entry["summary"]["epoch"]) for entry in commit_entries] == [2, 4]
    assert [int(entry["summary"]["watermark"]) for entry in commit_entries] == [2, 4]


def test_audit_commit_writer_uses_policy_stride_and_snapshot_summary(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(
            commit_stride=1,
            audit_commit_enabled=True,
            audit_commit_stride=3,
            microsteps_per_global_tick=1,
        ),
    )
    session = DetmSession.create(cfg, seed=7)
    audit_path = tmp_path / "commits_audit.jsonl"

    CommitJsonlWriter.attach(
        session.bus,
        audit_path,
        node_id="node-audit",
        commit_type="proof",
        mode="audit",
    )

    for _ in range(7):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [entry["tick_ref"]["tick"] for entry in entries] == [3, 6]
    assert all(entry["mode"] == "audit" for entry in entries)
    assert all(entry["commit_type"] == "proof" for entry in entries)
    assert all(isinstance(entry["summary"].get("snapshot_sha256"), str) for entry in entries)
    assert all(int(entry["summary"].get("snapshot_bytes", 0)) > 0 for entry in entries)
    assert all(int(entry["summary"].get("audit_commit_stride", 0)) == 3 for entry in entries)


def test_commit_writer_emits_all_boundaries_within_single_step_call(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(
            commit_stride=2,
            batch_size=8,
            microsteps_per_global_tick=1,
        ),
    )
    session = DetmSession.create(cfg, seed=11)
    trace_path = tmp_path / "trace.jsonl"
    commits_path = tmp_path / "commits.jsonl"

    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])
    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-test", mode="realtime")

    session.step(None, 5, rng=session.state.restore_rng())
    session.close()

    trace_entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    commit_entries = [json.loads(line) for line in commits_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert [entry["tick"] for entry in trace_entries] == [2, 4]
    assert [entry["tick_ref"]["tick"] for entry in commit_entries] == [2, 4]
    assert [entry["trace_ref"] for entry in commit_entries] == [entry["trace_ref"] for entry in trace_entries]
