from __future__ import annotations

import json
import numpy as np

from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import JsonlTraceWriter, WatchTraceWriter
from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy


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


def test_system_and_watch_trace_linkage(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=21)
    system_path = tmp_path / "trace.jsonl"
    watch_path = tmp_path / "watch_trace.jsonl"

    JsonlTraceWriter.attach(session.bus, system_path, metric_plugins=[])
    WatchTraceWriter.attach(session.bus, watch_path)

    for _ in range(4):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    system_entries = _read_jsonl(system_path)
    watch_entries = _read_jsonl(watch_path)
    assert [entry["tick"] for entry in system_entries] == [1, 2, 3, 4]
    assert [entry["tick"] for entry in watch_entries] == [1, 2, 3, 4]
    assert [entry["trace_ref"] for entry in watch_entries] == [entry["trace_ref"] for entry in system_entries]
    assert all(str(entry["trace_ref"]).startswith("trace://") for entry in watch_entries)
    assert all(isinstance(entry.get("watchpoints"), dict) for entry in watch_entries)
    assert all("runtime_adaptive_window_active" in dict(entry.get("watchpoints", {})) for entry in watch_entries)
    assert all("runtime_adaptive_profile" in dict(entry.get("watchpoints", {})) for entry in watch_entries)
    assert all("runtime_adaptive_signal_triggered" in dict(entry.get("watchpoints", {})) for entry in watch_entries)
    assert all("anti_goodhart" in dict(entry.get("watchpoints", {})) for entry in watch_entries)
    assert all("anti_goodhart_flag" in dict(entry.get("watchpoints", {})) for entry in watch_entries)
    assert all("runtime_adaptive_window_active" in dict(entry.get("policy", {})) for entry in watch_entries)
    assert all("anti_goodhart" in dict(entry.get("policy", {})) for entry in watch_entries)


def test_trace_storage_policy_limits(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=22)
    system_path = tmp_path / "trace.jsonl"
    watch_path = tmp_path / "watch_trace.jsonl"

    JsonlTraceWriter.attach(session.bus, system_path, metric_plugins=[], retention_window=2)
    WatchTraceWriter.attach(session.bus, watch_path, retention_window=5, compaction_budget=3)

    for _ in range(6):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    system_entries = _read_jsonl(system_path)
    watch_entries = _read_jsonl(watch_path)
    assert [entry["tick"] for entry in system_entries] == [5, 6]
    assert [entry["tick"] for entry in watch_entries] == [4, 5, 6]


def test_watch_trace_runtime_adaptive_telemetry_switches_when_window_active(tmp_path):
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
            microsteps_per_global_tick=1,
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_microsteps_per_global_tick=2,
            runtime_adaptive_hold_ticks=1,
        ),
    )
    session = DetmSession.create(cfg, seed=23)
    watch_path = tmp_path / "watch_trace.jsonl"
    WatchTraceWriter.attach(session.bus, watch_path)

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())
    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    watch_entries = _read_jsonl(watch_path)
    assert len(watch_entries) >= 3
    assert bool(dict(watch_entries[0].get("policy", {})).get("runtime_adaptive_window_active")) is False
    assert any(bool(dict(entry.get("policy", {})).get("runtime_adaptive_window_active")) for entry in watch_entries[1:])

