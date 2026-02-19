from __future__ import annotations

import json

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import JsonlTraceWriter, OperatorDecisionWriter


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_overflow_hotspot(session: DetmSession) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.zeros((h, w), dtype=float)
    energy[h // 2, w // 2] = 3.0
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(energy, session.config.dynamics, boundary=state.lattice.boundary)


def test_operator_decision_writer_trace_ref_linkage(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=81)
    trace_path = tmp_path / "trace.jsonl"
    decisions_path = tmp_path / "operator_decisions.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])
    OperatorDecisionWriter.attach(session.bus, decisions_path)

    for _ in range(3):
        _seed_overflow_hotspot(session)
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    trace_entries = _read_jsonl(trace_path)
    decision_entries = _read_jsonl(decisions_path)
    assert [entry["tick"] for entry in decision_entries] == [1, 2, 3]
    assert [entry["trace_ref"] for entry in decision_entries] == [entry["trace_ref"] for entry in trace_entries]

    first = decision_entries[0]
    assert str(first.get("type")) == "operator_decisions_step"
    assert int(first.get("decision_count", 0)) >= 1
    first_decision = dict(list(first.get("decisions", []))[0])
    assert str(first_decision.get("id", "")).strip() != ""
    assert str(first_decision.get("source", "")).strip() in {"search", "reuse"}
    assert str(dict(first_decision.get("contract", {})).get("type", "")) == "discrete_torsion_v1"


def test_operator_decision_writer_storage_policy_prunes_entries(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=82)
    decisions_path = tmp_path / "operator_decisions.jsonl"
    OperatorDecisionWriter.attach(
        session.bus,
        decisions_path,
        retention_window=5,
        compaction_budget=3,
    )

    for _ in range(6):
        _seed_overflow_hotspot(session)
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    decision_entries = _read_jsonl(decisions_path)
    assert [entry["tick"] for entry in decision_entries] == [4, 5, 6]


def test_operator_decision_writer_reads_anti_goodhart_policy_from_level_policy(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            anti_goodhart_enabled=False,
            anti_goodhart_target_signal="hold_rate",
            anti_goodhart_policy_reaction_enabled=False,
            anti_goodhart_prefer_runtime_profile="throughput",
        ),
    )
    session = DetmSession.create(cfg, seed=83)
    decisions_path = tmp_path / "operator_decisions.jsonl"
    OperatorDecisionWriter.attach(session.bus, decisions_path)

    for _ in range(2):
        _seed_overflow_hotspot(session)
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    rows = _read_jsonl(decisions_path)
    panel = dict(dict(rows[-1].get("summary", {})).get("portability_panel", {}))
    anti_goodhart = dict(panel.get("anti_goodhart", {}))
    assert str(anti_goodhart.get("applicability", "")) == "disabled"
    assert bool(anti_goodhart.get("goodhart_flag")) is False
    assert str(anti_goodhart.get("target_signal", "")) == "hold_rate"
    assert bool(anti_goodhart.get("policy_reaction_enabled")) is False
    assert str(anti_goodhart.get("preferred_runtime_profile", "")) == "throughput"
