from __future__ import annotations

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm_app.config.ui_models import UiRunSettings
from detm_app.runtime.ui_runtime import DetmUiRunner
from detm_app.runtime.ui_runtime.learning import learning_status_compact, learning_status_multiline


def _seed_overflow_hotspot(runner: DetmUiRunner) -> None:
    state = runner.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.zeros((h, w), dtype=float)
    energy[h // 2, w // 2] = 3.0
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(
        energy,
        runner.settings.config.dynamics,
        boundary=state.lattice.boundary,
    )


def test_ui_runner_learning_snapshot_tracks_refinement_and_runtime_adaptive() -> None:
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
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_hold_ticks=2,
        ),
    )
    settings = UiRunSettings(
        config=cfg,
        ticks_per_step=1,
        influence_mode="none",
        viz_enabled=False,
        viz_transport="none",
        learning_view_enabled=True,
        learning_window_steps=8,
    )
    runner = DetmUiRunner(settings)
    try:
        _seed_overflow_hotspot(runner)
        runner.step_once()

        snapshot = runner.learning_snapshot
        assert int(snapshot.get("tick", 0)) >= 1
        assert int(snapshot.get("event_count", 0)) >= 1

        watchpoints = dict(snapshot.get("watchpoints", {}))
        assert int(watchpoints.get("refinement_count", 0)) >= 1
        assert "runtime_adaptive_signal_triggered" in watchpoints

        panel = dict(snapshot.get("portability_panel", {}))
        counts = dict(panel.get("counts", {}))
        assert int(counts.get("total_decisions", 0)) >= 1
        assert "acceptance" in panel
    finally:
        runner.close()


def test_ui_runner_learning_status_respects_disable_flag() -> None:
    cfg = DETMConfig(backend="numpy", device="cpu", width=8, height=8)
    settings = UiRunSettings(
        config=cfg,
        influence_mode="none",
        viz_enabled=False,
        viz_transport="none",
        learning_view_enabled=False,
        learning_window_steps=4,
    )
    runner = DetmUiRunner(settings)
    try:
        assert runner.learning_status_compact() == "learn=off"
        assert "disabled" in runner.learning_status_multiline().lower()
    finally:
        runner.close()


def test_ui_runner_learning_snapshot_includes_nd_projection_metadata() -> None:
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        shape=(2, 11, 11),
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    settings = UiRunSettings(
        config=cfg,
        influence_mode="none",
        viz_enabled=False,
        viz_transport="none",
        learning_view_enabled=True,
        learning_window_steps=4,
    )
    runner = DetmUiRunner(settings)
    try:
        runner.step_once()
        snapshot = runner.learning_snapshot
        projection = dict(snapshot.get("projection", {}))
        assert projection["kind"] == "nd_projection"
        assert list(projection["source_shape"]) == [2, 11, 11]
        assert list(projection["projected_shape"]) == [11, 11]
        assert projection["reduction"] == "mean_leading_axes"
        compact = runner.learning_status_compact(max_len=200)
        assert "proj=2x11x11->11x11" in compact
    finally:
        runner.close()


def test_learning_status_multiline_shows_exploration_horizon_fields() -> None:
    out = learning_status_multiline(
        {
            "tick": 4,
            "event_count": 2,
            "event_types": ["refinement"],
            "projection": {
                "kind": "nd_projection",
                "source_shape": [2, 11, 11],
                "projected_shape": [11, 11],
                "collapsed_axes": [0],
                "collapsed_plane_count": 2,
                "reduction": "mean_leading_axes",
            },
            "portability_panel": {
                "hold_rate": 0.8,
                "operator_reuse": 0.5,
                "transferability": 0.25,
                "torsion_health": 0.9,
                "acceptance": {"passed": False, "failed_signals": ["transferability"]},
                "counts": {
                    "total_decisions": 4,
                    "reuse_decisions": 2,
                    "transferable_reuse_decisions": 1,
                    "compatible_decisions": 3,
                    "torsion_flag_decisions": 1,
                },
            },
            "watchpoints": {
                "runtime_adaptive_profile": "throughput",
                "runtime_adaptive_window_active": True,
                "runtime_adaptive_signal_triggered": True,
                "anti_goodhart_flag": True,
                "anti_goodhart": {
                    "applicability": "runtime_panel",
                    "degraded_signal_count": 2,
                },
                "anti_goodhart_policy_reaction_applied": True,
                "anti_goodhart_runtime_profile_applied": True,
                "exploration_horizon_ticks": 3,
                "horizon_start_tick": 2,
                "horizon_break_reason": "goodhart_flag",
                "horizon_recovery_cost_ticks": 1,
            },
            "window": {
                "steps": 4,
                "event_count": 6,
                "refinement_count": 3,
                "decision_count": 4,
                "reuse_rate": 0.5,
            },
        }
    )
    assert "Exploration horizon:" in out
    assert "ticks=3" in out
    assert "start_tick=2" in out
    assert "break_reason=goodhart_flag" in out
    assert "recovery_cost_ticks=1" in out
    assert "Projection:" in out
    assert "source_shape=[2, 11, 11] -> projected_shape=[11, 11]" in out
    assert "reduction=mean_leading_axes collapsed_axes=[0] planes=2" in out


def test_learning_status_compact_shows_nd_projection_summary() -> None:
    out = learning_status_compact(
        {
            "tick": 3,
            "portability_panel": {
                "hold_rate": 0.4,
                "operator_reuse": 0.25,
                "transferability": 0.1,
                "counts": {"total_decisions": 2},
            },
            "watchpoints": {
                "runtime_adaptive_profile": "manual",
                "runtime_adaptive_window_active": False,
                "anti_goodhart_flag": False,
            },
            "projection": {
                "kind": "nd_projection",
                "source_shape": [3, 9, 7],
                "projected_shape": [9, 7],
            },
        },
        max_len=200,
    )
    assert "proj=3x9x7->9x7" in out
