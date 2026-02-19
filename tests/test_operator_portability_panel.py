from __future__ import annotations

import json

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import OperatorDecisionWriter


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


def _run_scope_transfer_scenario(*, scope: str, out_path) -> list[dict]:
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        observables_mode="minimal",
        dynamics=DynamicsParameters(energy_bounds=None),
        pattern_reuse_enabled=True,
        pattern_reuse_scope=scope,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            active_level="L0",
            refinement_operator_torsion_guard_enabled=False,
        ),
    )
    session = DetmSession.create(cfg, seed=91)
    OperatorDecisionWriter.attach(session.bus, out_path)

    for _ in range(2):
        _seed_overflow_hotspot(session)
        session.step(None, 1, rng=session.state.restore_rng())

    updated = session.config.to_dict()
    updated["observables_mode"] = "cpu_full"
    level_policy = dict(updated.get("level_policy", {}))
    level_policy["active_level"] = "L1"
    updated["level_policy"] = level_policy
    session.config = DETMConfig.from_dict(updated)
    session.state.config = session.config.to_dict()

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())
    session.close()
    return _read_jsonl(out_path)


def test_operator_portability_panel_fields_present_and_bounded(tmp_path):
    rows = _run_scope_transfer_scenario(scope="portable", out_path=tmp_path / "operator_decisions.jsonl")
    assert len(rows) == 3
    panel = dict(dict(rows[-1].get("summary", {})).get("portability_panel", {}))
    assert set(panel.keys()) == {
        "hold_rate",
        "operator_reuse",
        "transferability",
        "torsion_flag_rate",
        "torsion_health",
        "counts",
        "thresholds",
        "acceptance",
        "anti_goodhart",
    }
    assert 0.0 <= float(panel.get("hold_rate", -1.0)) <= 1.0
    assert 0.0 <= float(panel.get("operator_reuse", -1.0)) <= 1.0
    assert 0.0 <= float(panel.get("transferability", -1.0)) <= 1.0
    assert 0.0 <= float(panel.get("torsion_flag_rate", -1.0)) <= 1.0
    assert 0.0 <= float(panel.get("torsion_health", -1.0)) <= 1.0
    thresholds = dict(panel.get("thresholds", {}))
    assert set(thresholds.keys()) == {"hold_rate_min", "operator_reuse_min", "transferability_min"}
    acceptance = dict(panel.get("acceptance", {}))
    assert "passed" in acceptance
    assert "failed_signals" in acceptance
    anti_goodhart = dict(panel.get("anti_goodhart", {}))
    assert "goodhart_flag" in anti_goodhart
    assert "policy_reaction" in anti_goodhart


def test_operator_portability_panel_portable_vs_strict_transferability(tmp_path):
    portable_rows = _run_scope_transfer_scenario(scope="portable", out_path=tmp_path / "portable.jsonl")
    strict_rows = _run_scope_transfer_scenario(scope="strict", out_path=tmp_path / "strict.jsonl")

    portable_third = dict(list(portable_rows[-1].get("decisions", []))[0])
    strict_third = dict(list(strict_rows[-1].get("decisions", []))[0])
    assert str(portable_third.get("source", "")) == "reuse"
    assert str(strict_third.get("source", "")) == "search"

    portable_panel = dict(dict(portable_rows[-1].get("summary", {})).get("portability_panel", {}))
    strict_panel = dict(dict(strict_rows[-1].get("summary", {})).get("portability_panel", {}))
    assert float(portable_panel.get("transferability", 0.0)) > float(strict_panel.get("transferability", 0.0))
    assert bool(dict(portable_panel.get("acceptance", {})).get("passed")) is True
    strict_acceptance = dict(strict_panel.get("acceptance", {}))
    assert bool(strict_acceptance.get("passed")) is False
    assert "transferability" in list(strict_acceptance.get("failed_signals", []))


def test_operator_portability_panel_goodhart_not_triggered_in_stable_portable_path(tmp_path):
    rows = _run_scope_transfer_scenario(scope="portable", out_path=tmp_path / "portable_goodhart.jsonl")
    panel = dict(dict(rows[-1].get("summary", {})).get("portability_panel", {}))
    anti_goodhart = dict(panel.get("anti_goodhart", {}))
    assert bool(anti_goodhart.get("goodhart_flag")) is False
