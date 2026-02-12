from __future__ import annotations

import json

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm_app.session import DetmSession


def _seed_overflow_hotspot(session: DetmSession, *, center_y: int | None = None, center_x: int | None = None) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.zeros((h, w), dtype=float)
    cy = (h // 2) if center_y is None else int(center_y) % max(1, h)
    cx = (w // 2) if center_x is None else int(center_x) % max(1, w)
    energy[cy, cx] = 3.0
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)


def _first_refinement_event(obs) -> dict:
    events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(events) == 1
    return dict(events[0])


def test_pattern_reuse_hits_cache_and_store(tmp_path):
    store_path = tmp_path / "patterns.json"
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
        pattern_reuse_enabled=True,
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=1024,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
    )
    session = DetmSession.create(cfg, seed=3)

    _seed_overflow_hotspot(session)
    first = _first_refinement_event(session.step(None, 1, rng=session.state.restore_rng()))
    _seed_overflow_hotspot(session)
    second = _first_refinement_event(session.step(None, 1, rng=session.state.restore_rng()))
    session.close()

    assert bool(dict(first.get("pattern", {})).get("reused")) is False
    assert bool(dict(second.get("pattern", {})).get("reused")) is True
    assert int(dict(second.get("pattern", {})).get("hits", 0)) >= 2

    payload = json.loads(store_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert len(payload) >= 1


def test_pattern_pruning_removes_unstable_records(tmp_path):
    store_path = tmp_path / "patterns.json"
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
        pattern_reuse_enabled=True,
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=1024,
        pattern_prune_error_threshold=0.0,
        pattern_prune_deviation_threshold=1e-12,
    )
    session = DetmSession.create(cfg, seed=4)

    _seed_overflow_hotspot(session)
    first = _first_refinement_event(session.step(None, 1, rng=session.state.restore_rng()))
    _seed_overflow_hotspot(session)
    second = _first_refinement_event(session.step(None, 1, rng=session.state.restore_rng()))
    session.close()

    assert bool(dict(first.get("pattern", {})).get("reused")) is False
    assert bool(dict(second.get("pattern", {})).get("reused")) is False
    assert int(dict(second.get("pattern", {})).get("hits", 0)) == 1


def test_pattern_pruning_long_series_keeps_store_bounded_under_strict_thresholds(tmp_path):
    store_path = tmp_path / "patterns.json"
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
        pattern_reuse_enabled=True,
        pattern_store_path=str(store_path),
        pattern_cache_capacity=8,
        pattern_cache_ttl_steps=64,
        pattern_prune_error_threshold=0.0,
        pattern_prune_deviation_threshold=1e-12,
    )
    session = DetmSession.create(cfg, seed=14)
    for step in range(24):
        _seed_overflow_hotspot(session, center_y=(step % 9) + 1, center_x=((step * 3) % 9) + 1)
        obs = session.step(None, 1, rng=session.state.restore_rng())
        event = _first_refinement_event(obs)
        assert bool(dict(event.get("pattern", {})).get("reused")) is False
    runtime = getattr(session.state, "_pattern_runtime", None)
    session.close()

    payload = json.loads(store_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert len(payload) <= 1
    if runtime is not None:
        assert int(runtime.cache_size()) <= 1


def test_pattern_long_series_reuse_accumulates_hits_for_stable_hotspot(tmp_path):
    store_path = tmp_path / "patterns.json"
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
        pattern_reuse_enabled=True,
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=256,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
    )
    session = DetmSession.create(cfg, seed=15)
    events: list[dict] = []
    for _ in range(10):
        _seed_overflow_hotspot(session)
        events.append(_first_refinement_event(session.step(None, 1, rng=session.state.restore_rng())))
    session.close()

    assert bool(dict(events[0].get("pattern", {})).get("reused")) is False
    assert all(bool(dict(event.get("pattern", {})).get("reused")) is True for event in events[1:])
    assert int(dict(events[-1].get("pattern", {})).get("hits", 0)) >= 10

    payload = json.loads(store_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert len(payload) == 1


def test_pattern_reuse_quality_gate_blocks_out_of_policy_record_between_sessions(tmp_path):
    store_path = tmp_path / "patterns.json"

    warm_cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
        pattern_reuse_enabled=True,
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=256,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
    )
    warm_session = DetmSession.create(warm_cfg, seed=16)
    _seed_overflow_hotspot(warm_session)
    _first_refinement_event(warm_session.step(None, 1, rng=warm_session.state.restore_rng()))
    warm_session.close()

    strict_cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
        pattern_reuse_enabled=True,
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=256,
        pattern_prune_error_threshold=0.0,
        pattern_prune_deviation_threshold=1e-12,
    )
    strict_session = DetmSession.create(strict_cfg, seed=16)
    _seed_overflow_hotspot(strict_session)
    event = _first_refinement_event(strict_session.step(None, 1, rng=strict_session.state.restore_rng()))
    strict_session.close()

    pattern = dict(event.get("pattern", {}))
    assert bool(pattern.get("reused")) is False
    assert int(pattern.get("hits", 0)) == 1


def test_pattern_reuse_scope_portable_allows_cross_level_and_mode_reuse(tmp_path):
    store_path = tmp_path / "patterns.json"

    warm_cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        observables_mode="minimal",
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1, active_level="L0"),
        pattern_reuse_enabled=True,
        pattern_reuse_scope="portable",
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=256,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
    )
    warm_session = DetmSession.create(warm_cfg, seed=17)
    _seed_overflow_hotspot(warm_session)
    _first_refinement_event(warm_session.step(None, 1, rng=warm_session.state.restore_rng()))
    warm_session.close()

    portable_cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        observables_mode="cpu_full",
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1, active_level="L2"),
        pattern_reuse_enabled=True,
        pattern_reuse_scope="portable",
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=256,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
    )
    portable_session = DetmSession.create(portable_cfg, seed=17)
    _seed_overflow_hotspot(portable_session)
    event = _first_refinement_event(portable_session.step(None, 1, rng=portable_session.state.restore_rng()))
    portable_session.close()

    pattern = dict(event.get("pattern", {}))
    assert bool(pattern.get("reused")) is True
    assert int(pattern.get("hits", 0)) >= 2


def test_pattern_reuse_scope_strict_blocks_cross_level_reuse(tmp_path):
    store_path = tmp_path / "patterns.json"

    warm_cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        observables_mode="minimal",
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1, active_level="L0"),
        pattern_reuse_enabled=True,
        pattern_reuse_scope="strict",
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=256,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
    )
    warm_session = DetmSession.create(warm_cfg, seed=18)
    _seed_overflow_hotspot(warm_session)
    _first_refinement_event(warm_session.step(None, 1, rng=warm_session.state.restore_rng()))
    warm_session.close()

    strict_cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        observables_mode="cpu_full",
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1, active_level="L1"),
        pattern_reuse_enabled=True,
        pattern_reuse_scope="strict",
        pattern_store_path=str(store_path),
        pattern_cache_capacity=16,
        pattern_cache_ttl_steps=256,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
    )
    strict_session = DetmSession.create(strict_cfg, seed=18)
    _seed_overflow_hotspot(strict_session)
    event = _first_refinement_event(strict_session.step(None, 1, rng=strict_session.state.restore_rng()))
    strict_session.close()

    pattern = dict(event.get("pattern", {}))
    assert bool(pattern.get("reused")) is False
    assert int(pattern.get("hits", 0)) == 1
