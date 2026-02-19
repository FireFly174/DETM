from __future__ import annotations

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm_app.config.ui_models import UiRunSettings
from detm_app.runtime.ui_runtime import DetmUiRunner


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
