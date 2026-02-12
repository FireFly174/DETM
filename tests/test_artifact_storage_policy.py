from __future__ import annotations

import json

from detm.cli import run_headless
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_l0_artifact_storage_policy_applies_to_streaming_artifacts(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        watch_trace_enabled=True,
        trace_system_retention_window=99,  # must be overridden by artifact_storage_policy
        trace_watch_retention_window=99,  # must be overridden by artifact_storage_policy
        trace_watch_compaction_budget=99,  # must be overridden by artifact_storage_policy
        artifact_storage_policy={
            "L0": {
                "trace": {"retention_window": 4, "compaction_budget": 2},
                "history": {"retention_window": 3, "compaction_budget": 0},
                "watch_trace": {"retention_window": 5, "compaction_budget": 3},
                "watch_contract": {"retention_window": 5, "compaction_budget": 3},
                "outerfields": {"retention_window": 4, "compaction_budget": 2},
                "commits": {"retention_window": 2, "compaction_budget": 0},
                "commits_audit": {"retention_window": 1, "compaction_budget": 0},
                "invariants": {"retention_window": 2, "compaction_budget": 0},
            }
        },
        level_policy=LevelPolicy(
            active_level="L0",
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=True,
            audit_commit_stride=1,
        ),
    )
    out_dir = tmp_path / "out"
    run_headless(
        config=cfg,
        seed=17,
        symbol_ids=["pulse"] * 6,
        steps=1,
        out_dir=out_dir,
        viz_transport=None,
        invariant_streams=["inv0=1/1"],
    )

    trace_entries = _read_jsonl(out_dir / "trace.jsonl")
    history_entries = _read_jsonl(out_dir / "history.jsonl")
    watch_entries = _read_jsonl(out_dir / "watch_trace.jsonl")
    watch_contract_entries = _read_jsonl(out_dir / "watch_contract.jsonl")
    commits_entries = _read_jsonl(out_dir / "commits.jsonl")
    commits_audit_entries = _read_jsonl(out_dir / "commits_audit.jsonl")
    invariant_entries = _read_jsonl(out_dir / "invariants.jsonl")

    assert [entry["tick"] for entry in trace_entries] == [5, 6]
    assert len(history_entries) == 3
    assert [entry["tick"] for entry in watch_entries] == [4, 5, 6]
    assert [entry["tick"] for entry in watch_contract_entries] == [4, 5, 6]
    assert [int(entry["tick_ref"]["tick"]) for entry in commits_entries] == [5, 6]
    assert [int(entry["tick_ref"]["tick"]) for entry in commits_audit_entries] == [6]
    assert len(invariant_entries) == 2

    outerfields_rows = sorted((out_dir / "outerfields").glob("outerfields_*.npz"), key=lambda p: p.name)
    assert [int(path.stem.split("_")[-1]) for path in outerfields_rows] == [5, 6]


def test_l0_artifact_storage_policy_applies_to_fabric_reports(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        watch_trace_enabled=False,
        artifact_storage_policy={
            "L0": {
                "fabric_acks": {"retention_window": 4, "compaction_budget": 0},
                "fabric_ack_envelopes": {"retention_window": 3, "compaction_budget": 0},
                "fabric_delivery_acks": {"retention_window": 2, "compaction_budget": 0},
            }
        },
        level_policy=LevelPolicy(
            active_level="L0",
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=False,
        ),
    )
    out_dir = tmp_path / "out"
    run_headless(
        config=cfg,
        seed=18,
        symbol_ids=["pulse"] * 6,
        steps=1,
        out_dir=out_dir,
        viz_transport=None,
        fabric_handshake=True,
        fabric_delivery_required_receipts=1,
        fabric_delivery_max_attempts=2,
        fabric_delivery_retry_interval_ms=0,
        fabric_delivery_timeout_ms=500,
    )

    fabric_acks = _read_jsonl(out_dir / "fabric_acks.jsonl")
    fabric_ack_envelopes = _read_jsonl(out_dir / "fabric_ack_envelopes.jsonl")
    fabric_delivery_acks = _read_jsonl(out_dir / "fabric_delivery_acks.jsonl")

    assert len(fabric_acks) == 4
    assert len(fabric_ack_envelopes) == 3
    assert len(fabric_delivery_acks) == 2


def test_l1_profile_applies_for_active_level_and_watch_contract_level_src(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        watch_trace_enabled=True,
        artifact_storage_policy={
            "L0": {
                "trace": {"retention_window": 6, "compaction_budget": 0},
                "watch_trace": {"retention_window": 6, "compaction_budget": 0},
                "watch_contract": {"retention_window": 6, "compaction_budget": 0},
                "outerfields": {"retention_window": 6, "compaction_budget": 0},
                "commits": {"retention_window": 4, "compaction_budget": 0},
            },
            "L1": {
                "trace": {"retention_window": 3, "compaction_budget": 0},
                "watch_trace": {"retention_window": 2, "compaction_budget": 0},
                "watch_contract": {"retention_window": 2, "compaction_budget": 0},
                "outerfields": {"retention_window": 2, "compaction_budget": 0},
                "commits": {"retention_window": 1, "compaction_budget": 0},
            },
        },
        level_policy=LevelPolicy(
            active_level="L1",
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=False,
        ),
    )
    out_dir = tmp_path / "out_l1"
    run_headless(
        config=cfg,
        seed=19,
        symbol_ids=["pulse"] * 4,
        steps=1,
        out_dir=out_dir,
        viz_transport=None,
    )

    trace_entries = _read_jsonl(out_dir / "trace.jsonl")
    watch_entries = _read_jsonl(out_dir / "watch_trace.jsonl")
    watch_contract_entries = _read_jsonl(out_dir / "watch_contract.jsonl")
    commits_entries = _read_jsonl(out_dir / "commits.jsonl")

    assert [entry["tick"] for entry in trace_entries] == [2, 3, 4]
    assert [entry["tick"] for entry in watch_entries] == [3, 4]
    assert [entry["tick"] for entry in watch_contract_entries] == [3, 4]
    assert [int(entry["tick_ref"]["tick"]) for entry in commits_entries] == [4]
    assert {str(entry["outerfields_ref"]["level_src"]) for entry in watch_contract_entries} == {"L1"}

    outerfields_rows = sorted((out_dir / "outerfields").glob("outerfields_*.npz"), key=lambda p: p.name)
    assert [int(path.stem.split("_")[-1]) for path in outerfields_rows] == [3, 4]


def test_l2_level_fallback_uses_l1_then_l0_policies(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        watch_trace_enabled=False,
        artifact_storage_policy={
            "L0": {
                "commits": {"retention_window": 2, "compaction_budget": 0},
            },
            "L1": {
                "trace": {"retention_window": 3, "compaction_budget": 0},
            },
        },
        level_policy=LevelPolicy(
            active_level="L2",
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=False,
        ),
    )
    out_dir = tmp_path / "out_l2"
    run_headless(
        config=cfg,
        seed=20,
        symbol_ids=["pulse"] * 4,
        steps=1,
        out_dir=out_dir,
        viz_transport=None,
    )

    trace_entries = _read_jsonl(out_dir / "trace.jsonl")
    commits_entries = _read_jsonl(out_dir / "commits.jsonl")
    assert [entry["tick"] for entry in trace_entries] == [2, 3, 4]
    assert [int(entry["tick_ref"]["tick"]) for entry in commits_entries] == [3, 4]


def test_commit_validation_policy_applies_to_history_report(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        watch_trace_enabled=False,
        artifact_storage_policy={
            "L1": {
                "commit_validation": {"retention_window": 2, "compaction_budget": 0},
            }
        },
        level_policy=LevelPolicy(
            active_level="L1",
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=False,
        ),
    )
    out_dir = tmp_path / "out_validation"
    for seed in (31, 32, 33):
        run_headless(
            config=cfg,
            seed=seed,
            symbol_ids=["pulse"] * 2,
            steps=1,
            out_dir=out_dir,
            viz_transport=None,
        )

    history_rows = _read_jsonl(out_dir / "commit_validation_history.jsonl")
    assert len(history_rows) == 2
    assert all(isinstance(row, dict) for row in history_rows)
    assert (out_dir / "commit_validation.json").exists()


def test_fabric_quorum_report_policy_applies_to_history_report(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        watch_trace_enabled=False,
        artifact_storage_policy={
            "L1": {
                "fabric_quorum_report": {"retention_window": 2, "compaction_budget": 0},
            }
        },
        level_policy=LevelPolicy(
            active_level="L1",
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=False,
        ),
    )
    out_dir = tmp_path / "out_quorum"
    for seed in (41, 42, 43):
        run_headless(
            config=cfg,
            seed=seed,
            symbol_ids=["pulse"] * 2,
            steps=1,
            out_dir=out_dir,
            viz_transport=None,
            fabric_handshake=True,
        )

    history_rows = _read_jsonl(out_dir / "fabric_quorum_report_history.jsonl")
    assert len(history_rows) == 2
    assert all(isinstance(row, dict) for row in history_rows)
    assert (out_dir / "fabric_quorum_report.json").exists()
