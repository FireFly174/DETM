from __future__ import annotations

import json

import numpy as np

from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import JsonlTraceWriter, WatchContractWriter
from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm.runtime.watch_contract import WatchContractPacket


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_watch_contract_trace_ref_and_outerfields_linkage(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=7,
        height=5,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=31)

    trace_path = tmp_path / "trace.jsonl"
    contract_path = tmp_path / "watch_contract.jsonl"
    outerfields_dir = tmp_path / "outerfields"

    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])
    WatchContractWriter.attach(
        session.bus,
        contract_path,
        outerfields_dir=outerfields_dir,
        retention_window=0,
        compaction_budget=0,
    )

    for _ in range(4):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    trace_entries = _read_jsonl(trace_path)
    contract_entries = _read_jsonl(contract_path)
    assert [entry["tick"] for entry in contract_entries] == [1, 2, 3, 4]
    assert [entry["trace_ref"] for entry in contract_entries] == [
        entry["trace_ref"] for entry in trace_entries
    ]

    for entry in contract_entries:
        packet = WatchContractPacket.from_dict(entry)
        ref = packet.outerfields_ref
        assert ref.kind == "outerfields"
        policy = dict(packet.policy)
        watchpoints = dict(dict(packet.metrics).get("watchpoints", {}))
        assert "runtime_adaptive_window_active" in policy
        assert "runtime_adaptive_profile" in policy
        assert "runtime_adaptive_signal_triggered" in policy
        assert "anti_goodhart" in policy
        assert "runtime_adaptive_window_active" in watchpoints
        assert "runtime_adaptive_profile" in watchpoints
        assert "runtime_adaptive_signal_triggered" in watchpoints
        assert "anti_goodhart_flag" in watchpoints
        assert "anti_goodhart_degraded_signal_count" in watchpoints
        assert "anti_goodhart_policy_reaction_applied" in watchpoints
        assert "anti_goodhart_runtime_profile_applied" in watchpoints
        assert "anti_goodhart" in watchpoints
        assert "exploration_horizon" in watchpoints
        assert "exploration_horizon_ticks" in watchpoints
        assert "horizon_start_tick" in watchpoints
        assert "horizon_break_reason" in watchpoints
        assert "horizon_recovery_cost_ticks" in watchpoints
        assert "operator_decision_count" in watchpoints
        assert "operator_reuse_count" in watchpoints
        assert "operator_search_count" in watchpoints
        assert "operator_reuse_rate" in watchpoints
        assert "operator_torsion_guard_block_count" in watchpoints
        assert "operator_torsion_flag_count" in watchpoints
        assert "operator_torsion_score_mean" in watchpoints
        artifact_path = contract_path.parent / ref.uri
        assert artifact_path.exists()
        with np.load(artifact_path) as data:
            assert {
                "dir_x",
                "dir_y",
                "strength",
                "stability",
                "instability",
                "boundary_activity",
                "capacity_violation_density",
                "meta_json",
            }.issubset(set(data.files))
            assert data["strength"].shape == (int(cfg.height), int(cfg.width))


def test_watch_contract_storage_policy_prunes_entries_and_artifacts(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=32)

    contract_path = tmp_path / "watch_contract.jsonl"
    outerfields_dir = tmp_path / "outerfields"

    WatchContractWriter.attach(
        session.bus,
        contract_path,
        outerfields_dir=outerfields_dir,
        retention_window=5,
        compaction_budget=3,
    )

    for _ in range(6):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    contract_entries = _read_jsonl(contract_path)
    assert [entry["tick"] for entry in contract_entries] == [4, 5, 6]
    for entry in contract_entries:
        watchpoints = dict(dict(entry.get("metrics", {})).get("watchpoints", {}))
        assert "operator_decision_count" in watchpoints
        assert "operator_search_count" in watchpoints
        assert "operator_torsion_flag_count" in watchpoints
        assert "anti_goodhart" in watchpoints
        assert "exploration_horizon" in watchpoints

    artifact_rows = sorted(outerfields_dir.glob("outerfields_*.npz"), key=lambda p: p.name)
    assert len(artifact_rows) == 3
    assert [int(path.stem.split("_")[-1]) for path in artifact_rows] == [4, 5, 6]


def test_watch_contract_preserves_plane_index_for_nd_refinement_events(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        shape=(2, 7, 5),
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=33)

    contract_path = tmp_path / "watch_contract.jsonl"
    outerfields_dir = tmp_path / "outerfields"

    WatchContractWriter.attach(
        session.bus,
        contract_path,
        outerfields_dir=outerfields_dir,
        retention_window=0,
        compaction_budget=0,
    )

    energy = np.zeros((2, 7, 5), dtype=float)
    energy[1, 3, 2] = 3.0
    session.state.field_state.energy = energy
    session.state.field_state.internal_time = np.zeros_like(energy)
    session.state.field_state.entropy = NumpyBackend._compute_entropy(
        energy,
        session.config.dynamics,
        boundary=session.state.lattice.boundary,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    contract_entries = _read_jsonl(contract_path)
    assert len(contract_entries) == 1
    events = list(contract_entries[0].get("events", []))
    refinement_events = [event for event in events if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    assert list(refinement_events[0].get("plane_index", [])) == [1]


def test_watch_contract_projects_nd_outerfields_and_records_projection_metadata(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        shape=(2, 7, 5),
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=34)

    contract_path = tmp_path / "watch_contract.jsonl"
    outerfields_dir = tmp_path / "outerfields"

    WatchContractWriter.attach(
        session.bus,
        contract_path,
        outerfields_dir=outerfields_dir,
        retention_window=0,
        compaction_budget=0,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    contract_entries = _read_jsonl(contract_path)
    assert len(contract_entries) == 1
    packet = WatchContractPacket.from_dict(contract_entries[0])
    projection = dict(packet.projection)
    assert projection["kind"] == "nd_projection"
    assert list(projection["source_shape"]) == [2, 7, 5]
    assert list(projection["projected_shape"]) == [7, 5]
    assert list(projection["collapsed_axes"]) == [0]
    assert projection["collapsed_plane_count"] == 2
    assert projection["reduction"] == "mean_leading_axes"

    artifact_path = contract_path.parent / packet.outerfields_ref.uri
    with np.load(artifact_path) as data:
        assert data["strength"].shape == (7, 5)
        meta = json.loads(str(data["meta_json"][0]))
    assert dict(meta.get("projection", {})) == projection
