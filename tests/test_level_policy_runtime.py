from __future__ import annotations

import json

import numpy as np

from detm_app.runtime.session import DetmSession
from detm_app.runtime.scheduler import TickRunner, TickScheduler
from detm_app.runtime.subscribers import JsonlTraceWriter
from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import LevelPolicy, ObservabilityProfile
from detm.runtime.schemas import DETM_CONFIG_V1, DETM_LEVEL_POLICY_V1, get_schema_versions


def test_level_policy_roundtrip_and_schema_registry():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        pattern_reuse_enabled=True,
        pattern_store_path="runs/out/patterns.json",
        pattern_cache_capacity=64,
        pattern_cache_ttl_steps=1024,
        pattern_prune_error_threshold=0.1,
        pattern_prune_deviation_threshold=0.25,
        pattern_reuse_scope="strict",
        watch_trace_enabled=True,
        trace_system_retention_window=32,
        trace_watch_retention_window=16,
        trace_watch_compaction_budget=8,
        artifact_storage_policy={
            "L0": {
                "trace": {"retention_window": 5, "compaction_budget": 3},
                "commits": {"retention_window": 7, "compaction_budget": 0},
            },
            "L1": {
                "trace": {"retention_window": 9, "compaction_budget": 1},
            },
            "default": {
                "fabric_acks": {"retention_window": 4, "compaction_budget": 2},
            },
        },
        level_policy=LevelPolicy(
            schema_version=DETM_LEVEL_POLICY_V1,
            active_level="L0",
            microsteps_per_global_tick=2,
            batch_size=4,
            commit_stride=3,
            audit_commit_enabled=True,
            audit_commit_stride=9,
            allow_refinement=True,
            refinement_capacity_overflow_ratio_threshold=0.2,
            refinement_capacity_overflow_mean_threshold=0.35,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=0.12,
            refinement_capacity_temporal_window=5,
            refinement_capacity_temporal_required_hits=3,
            refinement_capacity_learned_hits_threshold=4,
            refinement_capacity_cross_level_window=6,
            refinement_capacity_cross_level_min_levels=2,
            refinement_capacity_operator_score_threshold=1.25,
            refinement_capacity_cross_node_min_signals=2,
            refinement_capacity_distributed_accepted_min=1,
            refinement_capacity_signed_acks_min=3,
            refinement_capacity_consensus_accepted_min=2,
            refinement_capacity_crypto_validator_coverage_min=0.75,
            refinement_capacity_attestation_validator_ids=("validator-1", "validator-2"),
            refinement_capacity_attestation_min_coverage=1.0,
            refinement_capacity_byzantine_clean_min=2,
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_min_signals=2,
            runtime_adaptive_quality_oscillation_threshold=0.2,
            runtime_adaptive_quality_jitter_threshold=0.1,
            runtime_adaptive_cost_cpu_time_ms_threshold=1.5,
            runtime_adaptive_auto_profile=True,
            runtime_adaptive_stability_microsteps_delta=1,
            runtime_adaptive_stability_batch_size_delta=-1,
            runtime_adaptive_stability_commit_stride_delta=-1,
            runtime_adaptive_throughput_microsteps_delta=-2,
            runtime_adaptive_throughput_batch_size_delta=3,
            runtime_adaptive_throughput_commit_stride_delta=2,
            runtime_adaptive_cooldown_ticks=4,
            runtime_adaptive_telemetry_sample_stride=3,
            runtime_adaptive_telemetry_aggregation_window=6,
            runtime_adaptive_guard_microsteps_min=1,
            runtime_adaptive_guard_microsteps_max=3,
            runtime_adaptive_guard_batch_size_min=1,
            runtime_adaptive_guard_batch_size_max=5,
            runtime_adaptive_guard_commit_stride_min=1,
            runtime_adaptive_guard_commit_stride_max=7,
            runtime_adaptive_guard_reject_unsafe=True,
            runtime_adaptive_use_deltas=True,
            runtime_adaptive_microsteps_delta=2,
            runtime_adaptive_batch_size_delta=1,
            runtime_adaptive_commit_stride_delta=-2,
            runtime_adaptive_microsteps_per_global_tick=3,
            runtime_adaptive_batch_size=2,
            runtime_adaptive_commit_stride=1,
            runtime_adaptive_hold_ticks=2,
            observability_profile=ObservabilityProfile(
                allowed_event_types=("influence",),
                detail_mode="debug",
                adaptive_signal_event_types=("refinement",),
                adaptive_detail_mode="debug",
                adaptive_hold_ticks=2,
                adaptive_allowed_event_types=("refinement", "attractor"),
            ),
        ),
    )

    restored = DETMConfig.from_dict(cfg.to_dict())
    assert restored.config_version == DETM_CONFIG_V1
    assert restored.level_policy.microsteps_per_global_tick == 2
    assert restored.level_policy.batch_size == 4
    assert restored.level_policy.commit_stride == 3
    assert restored.level_policy.audit_commit_enabled is True
    assert restored.level_policy.audit_commit_stride == 9
    assert restored.level_policy.refinement_capacity_overflow_ratio_threshold == 0.2
    assert restored.level_policy.refinement_capacity_overflow_mean_threshold == 0.35
    assert restored.level_policy.refinement_capacity_min_signals == 2
    assert restored.level_policy.refinement_capacity_temporal_ratio_threshold == 0.12
    assert restored.level_policy.refinement_capacity_temporal_window == 5
    assert restored.level_policy.refinement_capacity_temporal_required_hits == 3
    assert restored.level_policy.refinement_capacity_learned_hits_threshold == 4
    assert restored.level_policy.refinement_capacity_cross_level_window == 6
    assert restored.level_policy.refinement_capacity_cross_level_min_levels == 2
    assert restored.level_policy.refinement_capacity_operator_score_threshold == 1.25
    assert restored.level_policy.refinement_capacity_cross_node_min_signals == 2
    assert restored.level_policy.refinement_capacity_distributed_accepted_min == 1
    assert restored.level_policy.refinement_capacity_signed_acks_min == 3
    assert restored.level_policy.refinement_capacity_consensus_accepted_min == 2
    assert restored.level_policy.refinement_capacity_crypto_validator_coverage_min == 0.75
    assert restored.level_policy.refinement_capacity_attestation_validator_ids == ("validator-1", "validator-2")
    assert restored.level_policy.refinement_capacity_attestation_min_coverage == 1.0
    assert restored.level_policy.refinement_capacity_byzantine_clean_min == 2
    assert restored.level_policy.runtime_adaptive_signal_event_types == ("refinement",)
    assert restored.level_policy.runtime_adaptive_min_signals == 2
    assert restored.level_policy.runtime_adaptive_quality_oscillation_threshold == 0.2
    assert restored.level_policy.runtime_adaptive_quality_jitter_threshold == 0.1
    assert restored.level_policy.runtime_adaptive_cost_cpu_time_ms_threshold == 1.5
    assert restored.level_policy.runtime_adaptive_auto_profile is True
    assert restored.level_policy.runtime_adaptive_stability_microsteps_delta == 1
    assert restored.level_policy.runtime_adaptive_stability_batch_size_delta == -1
    assert restored.level_policy.runtime_adaptive_stability_commit_stride_delta == -1
    assert restored.level_policy.runtime_adaptive_throughput_microsteps_delta == -2
    assert restored.level_policy.runtime_adaptive_throughput_batch_size_delta == 3
    assert restored.level_policy.runtime_adaptive_throughput_commit_stride_delta == 2
    assert restored.level_policy.runtime_adaptive_cooldown_ticks == 4
    assert restored.level_policy.runtime_adaptive_telemetry_sample_stride == 3
    assert restored.level_policy.runtime_adaptive_telemetry_aggregation_window == 6
    assert restored.level_policy.runtime_adaptive_guard_microsteps_min == 1
    assert restored.level_policy.runtime_adaptive_guard_microsteps_max == 3
    assert restored.level_policy.runtime_adaptive_guard_batch_size_min == 1
    assert restored.level_policy.runtime_adaptive_guard_batch_size_max == 5
    assert restored.level_policy.runtime_adaptive_guard_commit_stride_min == 1
    assert restored.level_policy.runtime_adaptive_guard_commit_stride_max == 7
    assert restored.level_policy.runtime_adaptive_guard_reject_unsafe is True
    assert restored.level_policy.runtime_adaptive_use_deltas is True
    assert restored.level_policy.runtime_adaptive_microsteps_delta == 2
    assert restored.level_policy.runtime_adaptive_batch_size_delta == 1
    assert restored.level_policy.runtime_adaptive_commit_stride_delta == -2
    assert restored.level_policy.runtime_adaptive_microsteps_per_global_tick == 3
    assert restored.level_policy.runtime_adaptive_batch_size == 2
    assert restored.level_policy.runtime_adaptive_commit_stride == 1
    assert restored.level_policy.runtime_adaptive_hold_ticks == 2
    assert restored.level_policy.observability_profile.allowed_event_types == ("influence",)
    assert restored.level_policy.observability_profile.normalized_detail_mode() == "debug"
    assert restored.level_policy.observability_profile.adaptive_signal_event_types == ("refinement",)
    assert restored.level_policy.observability_profile.normalized_adaptive_detail_mode() == "debug"
    assert restored.level_policy.observability_profile.adaptive_hold_ticks == 2
    assert restored.level_policy.observability_profile.adaptive_allowed_event_types == ("refinement", "attractor")
    assert restored.pattern_reuse_enabled is True
    assert restored.pattern_store_path == "runs/out/patterns.json"
    assert restored.pattern_cache_capacity == 64
    assert restored.pattern_cache_ttl_steps == 1024
    assert restored.pattern_prune_error_threshold == 0.1
    assert restored.pattern_prune_deviation_threshold == 0.25
    assert restored.pattern_reuse_scope == "strict"
    assert restored.watch_trace_enabled is True
    assert restored.trace_system_retention_window == 32
    assert restored.trace_watch_retention_window == 16
    assert restored.trace_watch_compaction_budget == 8
    trace_policy = restored.resolve_artifact_storage_policy(artifact="trace", level="L0")
    commits_policy = restored.resolve_artifact_storage_policy(artifact="commits", level="L0")
    trace_l2_policy = restored.resolve_artifact_storage_policy(artifact="trace", level="L2")
    commits_l2_policy = restored.resolve_artifact_storage_policy(artifact="commits", level="L2")
    default_policy = restored.resolve_artifact_storage_policy(artifact="fabric_acks", level="L3")
    fallback_policy = restored.resolve_artifact_storage_policy(artifact="watch_trace", level="L0")
    assert trace_policy == {"retention_window": 5, "compaction_budget": 3}
    assert commits_policy == {"retention_window": 7, "compaction_budget": 0}
    assert trace_l2_policy == {"retention_window": 9, "compaction_budget": 1}
    assert commits_l2_policy == {"retention_window": 7, "compaction_budget": 0}
    assert default_policy == {"retention_window": 4, "compaction_budget": 2}
    assert fallback_policy == {"retention_window": 16, "compaction_budget": 8}
    assert get_schema_versions()["level_policy"] == DETM_LEVEL_POLICY_V1


def test_level_policy_controls_trace_commit_and_event_filter(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(
            microsteps_per_global_tick=2,
            commit_stride=3,
            observability_profile=ObservabilityProfile(
                allowed_event_types=("attractor",),
                detail_mode="minimal",
            ),
        ),
    )
    session = DetmSession.create(cfg, seed=42)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    influence = DETMInfluence(symbol_id="pulse", amplitude=0.05, region=(3, 3, 1))
    for _ in range(3):
        session.step(influence, 1, rng=session.state.restore_rng())

    assert int(session.state.step_count) == 6
    session.close()

    lines = [line for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries = [json.loads(line) for line in lines]

    assert len(entries) == 2  # commit boundaries crossed on ticks 4 and 6
    assert [entry["tick"] for entry in entries] == [4, 6]
    assert all(entry["n_ticks"] == 2 for entry in entries)
    assert all(entry["chunk_n_ticks"] == 2 for entry in entries)
    assert all(entry["requested_n_ticks"] == 1 for entry in entries)
    assert all(entry["step_requested_n_ticks"] == 1 for entry in entries)
    assert all(entry["step_effective_n_ticks"] == 2 for entry in entries)
    assert all(entry["detail_mode"] == "minimal" for entry in entries)
    assert all(entry["event_count"] == 0 for entry in entries)
    assert all(entry["event_types"] == [] for entry in entries)
    assert all(entry["policy"]["commit_stride"] == 3 for entry in entries)
    assert all(entry["policy"]["effective_n_ticks"] == 2 for entry in entries)


def test_level_policy_trace_exposes_chunk_vs_step_tick_counts(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(
            microsteps_per_global_tick=1,
            batch_size=1,
            commit_stride=1,
        ),
    )
    session = DetmSession.create(cfg, seed=43)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    session.step(None, 3, rng=session.state.restore_rng())
    session.close()

    lines = [line for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries = [json.loads(line) for line in lines]

    assert [int(entry["tick"]) for entry in entries] == [1, 2, 3]
    assert all(int(entry["n_ticks"]) == 1 for entry in entries)
    assert all(int(entry["chunk_n_ticks"]) == 1 for entry in entries)
    assert all(int(entry["requested_n_ticks"]) == 3 for entry in entries)
    assert all(int(entry["step_requested_n_ticks"]) == 3 for entry in entries)
    assert all(int(entry["step_effective_n_ticks"]) == 3 for entry in entries)
    assert all(int(dict(entry.get("policy", {})).get("effective_n_ticks", 0)) == 1 for entry in entries)


def _seed_overflow_hotspot(session: DetmSession) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.zeros((h, w), dtype=float)
    energy[h // 2, w // 2] = 3.0
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(energy, session.config.dynamics, boundary=state.lattice.boundary)


def test_level_policy_adaptive_observability_switches_to_debug_on_signal(tmp_path):
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
            observability_profile=ObservabilityProfile(
                allowed_event_types=("attractor",),
                detail_mode="minimal",
                adaptive_signal_event_types=("refinement",),
                adaptive_detail_mode="debug",
                adaptive_hold_ticks=1,
                adaptive_allowed_event_types=("*",),
            ),
        ),
    )
    session = DetmSession.create(cfg, seed=52)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # trigger refinement -> adaptive debug
    session.step(None, 1, rng=session.state.restore_rng())  # held debug tick
    session.step(None, 1, rng=session.state.restore_rng())  # fallback to minimal profile
    session.close()

    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(entries) == 3
    assert [str(entry["detail_mode"]) for entry in entries] == ["debug", "debug", "minimal"]

    first_events = list(entries[0].get("events", []))
    assert any(str(event.get("type")) == "refinement" for event in first_events)
    assert list(entries[2].get("events", [])) == []
    assert entries[2].get("field_summaries") is None


def test_level_policy_runtime_adaptive_tuning_applies_after_signal(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=10,
            microsteps_per_global_tick=1,
            batch_size=1,
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_min_signals=2,
            runtime_adaptive_cost_cpu_time_ms_threshold=0.000001,
            runtime_adaptive_microsteps_per_global_tick=2,
            runtime_adaptive_commit_stride=1,
            runtime_adaptive_hold_ticks=1,
        ),
    )
    session = DetmSession.create(cfg, seed=53)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # trigger refinement -> arm runtime adaptive window
    assert int(session.state.step_count) == 1
    session.step(None, 1, rng=session.state.restore_rng())  # runtime adaptive: microsteps=2, commit_stride=1
    assert int(session.state.step_count) == 3
    session.close()

    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [int(entry["tick"]) for entry in entries] == [2, 3]
    assert all(int(entry["n_ticks"]) == 1 for entry in entries)
    assert all(int(entry["policy"]["effective_n_ticks"]) == 1 for entry in entries)
    assert all(int(entry["policy"]["commit_stride"]) == 1 for entry in entries)


def test_level_policy_runtime_adaptive_telemetry_visible_in_trace_policy(tmp_path):
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
    session = DetmSession.create(cfg, seed=58)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # trigger refinement, arm adaptive window
    session.step(None, 1, rng=session.state.restore_rng())  # adaptive window active
    session.close()

    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(entries) >= 3

    first_policy = dict(entries[0]["policy"])
    assert bool(first_policy.get("runtime_adaptive_window_active")) is False
    assert str(first_policy.get("runtime_adaptive_profile")) == "manual"
    assert bool(first_policy.get("runtime_adaptive_signal_triggered")) is True
    first_hits = dict(first_policy.get("runtime_adaptive_signal_hits", {}))
    assert bool(first_hits.get("event")) is True

    second_policy = dict(entries[1]["policy"])
    assert bool(second_policy.get("runtime_adaptive_window_active")) is True


def test_level_policy_runtime_adaptive_telemetry_sampling_and_aggregation(tmp_path):
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
            runtime_adaptive_telemetry_sample_stride=10,
            runtime_adaptive_telemetry_aggregation_window=3,
        ),
    )
    session = DetmSession.create(cfg, seed=59)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # signal trigger, hits must be sampled
    session.step(None, 1, rng=session.state.restore_rng())  # no trigger, hits should be omitted by stride
    session.step(None, 1, rng=session.state.restore_rng())  # keep aggregation rolling
    session.close()

    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(entries) >= 3
    first_policy = dict(entries[0]["policy"])
    assert bool(first_policy.get("runtime_adaptive_signal_hits_sampled")) is True
    assert bool(dict(first_policy.get("runtime_adaptive_signal_hits", {})).get("event")) is True
    first_agg = dict(first_policy.get("runtime_adaptive_aggregate", {}))
    assert int(first_agg.get("window_size", 0)) == 1
    assert int(first_agg.get("triggered_count", 0)) == 1

    second_policy = dict(entries[1]["policy"])
    assert bool(second_policy.get("runtime_adaptive_signal_hits_sampled")) is False
    assert dict(second_policy.get("runtime_adaptive_signal_hits", {})) == {}
    second_agg = dict(second_policy.get("runtime_adaptive_aggregate", {}))
    assert int(second_agg.get("window_size", 0)) >= 2


def test_level_policy_runtime_adaptive_respects_min_signal_threshold():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=10,
            microsteps_per_global_tick=1,
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_min_signals=2,
            runtime_adaptive_microsteps_per_global_tick=2,
            runtime_adaptive_commit_stride=1,
            runtime_adaptive_hold_ticks=1,
        ),
    )
    session = DetmSession.create(cfg, seed=54)

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # only event signal hit; min_signals=2
    session.step(None, 1, rng=session.state.restore_rng())  # should stay on base microsteps_per_global_tick=1
    session.close()

    assert int(session.state.step_count) == 2


def test_level_policy_runtime_adaptive_delta_mode_applies_relative_overrides(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            microsteps_per_global_tick=1,
            batch_size=1,
            commit_stride=5,
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_use_deltas=True,
            runtime_adaptive_microsteps_delta=2,
            runtime_adaptive_batch_size_delta=2,
            runtime_adaptive_commit_stride_delta=-4,
            runtime_adaptive_hold_ticks=1,
        ),
    )
    session = DetmSession.create(cfg, seed=55)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # trigger refinement -> arm runtime adaptive window
    assert int(session.state.step_count) == 1
    session.step(None, 1, rng=session.state.restore_rng())  # delta adaptive: microsteps=3, batch=3, commit_stride=1
    assert int(session.state.step_count) == 4
    session.close()

    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [int(entry["tick"]) for entry in entries] == [2, 3, 4]
    assert all(int(entry["policy"]["batch_size"]) == 3 for entry in entries)
    assert all(int(entry["policy"]["commit_stride"]) == 1 for entry in entries)


def test_level_policy_runtime_adaptive_auto_profile_prefers_throughput_on_cost_signal():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=False,
            microsteps_per_global_tick=2,
            batch_size=2,
            commit_stride=2,
            runtime_adaptive_signal_event_types=(),
            runtime_adaptive_min_signals=1,
            runtime_adaptive_cost_cpu_time_ms_threshold=0.000001,
            runtime_adaptive_auto_profile=True,
            runtime_adaptive_stability_microsteps_delta=2,
            runtime_adaptive_stability_batch_size_delta=-1,
            runtime_adaptive_stability_commit_stride_delta=-1,
            runtime_adaptive_throughput_microsteps_delta=-1,
            runtime_adaptive_throughput_batch_size_delta=2,
            runtime_adaptive_throughput_commit_stride_delta=1,
            runtime_adaptive_hold_ticks=1,
        ),
    )
    session = DetmSession.create(cfg, seed=56)

    session.step(None, 1, rng=session.state.restore_rng())  # trigger by cost signal
    assert int(session.state.step_count) == 2
    session.step(None, 1, rng=session.state.restore_rng())  # auto-profile should pick throughput deltas
    session.close()

    assert int(session.state.step_count) == 3


def test_level_policy_runtime_adaptive_cooldown_prevents_immediate_rearm():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            microsteps_per_global_tick=1,
            commit_stride=1,
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_microsteps_per_global_tick=2,
            runtime_adaptive_hold_ticks=1,
            runtime_adaptive_cooldown_ticks=3,
        ),
    )
    session = DetmSession.create(cfg, seed=57)

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # trigger arm
    assert int(session.state.step_count) == 1

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # adaptive window from step1 -> +2
    assert int(session.state.step_count) == 3

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # cooldown blocks immediate rearm -> +1
    assert int(session.state.step_count) == 4

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # cooldown still active at boundary -> +1
    assert int(session.state.step_count) == 5

    session.step(None, 1, rng=session.state.restore_rng())  # trigger from step4 should arm; now adaptive -> +2
    session.close()
    assert int(session.state.step_count) == 7


def test_level_policy_runtime_adaptive_guard_clamps_candidate_values(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            microsteps_per_global_tick=1,
            batch_size=1,
            commit_stride=1,
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_microsteps_per_global_tick=5,
            runtime_adaptive_batch_size=5,
            runtime_adaptive_commit_stride=1,
            runtime_adaptive_hold_ticks=1,
            runtime_adaptive_guard_microsteps_max=2,
            runtime_adaptive_guard_batch_size_max=2,
            runtime_adaptive_guard_reject_unsafe=False,
        ),
    )
    session = DetmSession.create(cfg, seed=60)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # arm adaptive window
    session.step(None, 1, rng=session.state.restore_rng())  # guarded adaptive step
    session.close()

    assert int(session.state.step_count) == 3
    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    adaptive_entries = [dict(entry.get("policy", {})) for entry in entries if bool(dict(entry.get("policy", {})).get("runtime_adaptive_window_active"))]
    assert len(adaptive_entries) >= 1
    guard = dict(adaptive_entries[0].get("runtime_adaptive_guard", {}))
    assert bool(guard.get("rejected")) is False
    assert int(dict(guard.get("applied", {})).get("microsteps_per_global_tick", 0)) == 2
    assert int(dict(guard.get("applied", {})).get("batch_size", 0)) == 2


def test_level_policy_runtime_adaptive_guard_rejects_unsafe_transition(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            microsteps_per_global_tick=1,
            batch_size=1,
            commit_stride=1,
            runtime_adaptive_signal_event_types=("refinement",),
            runtime_adaptive_microsteps_per_global_tick=5,
            runtime_adaptive_batch_size=5,
            runtime_adaptive_commit_stride=1,
            runtime_adaptive_hold_ticks=1,
            runtime_adaptive_guard_microsteps_max=2,
            runtime_adaptive_guard_batch_size_max=2,
            runtime_adaptive_guard_reject_unsafe=True,
        ),
    )
    session = DetmSession.create(cfg, seed=61)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    _seed_overflow_hotspot(session)
    session.step(None, 1, rng=session.state.restore_rng())  # arm adaptive window
    session.step(None, 1, rng=session.state.restore_rng())  # rejected adaptive transition -> fallback base
    session.close()

    assert int(session.state.step_count) == 2
    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    adaptive_entries = [dict(entry.get("policy", {})) for entry in entries if bool(dict(entry.get("policy", {})).get("runtime_adaptive_window_active"))]
    assert len(adaptive_entries) >= 1
    guard = dict(adaptive_entries[0].get("runtime_adaptive_guard", {}))
    assert bool(guard.get("rejected")) is True
    assert int(dict(guard.get("applied", {})).get("microsteps_per_global_tick", 0)) == 1


def test_tickrunner_scheduler_clock_keeps_global_ticks_with_microsteps():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(microsteps_per_global_tick=2, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=1)
    scheduler = TickScheduler(bus=session.bus, tick0=0)
    runner = TickRunner(session, scheduler)

    fired_ticks: list[int] = []
    session.bus.add_event_listener("signal", lambda **payload: fired_ticks.append(int(payload["tick"])))
    scheduler.schedule_influence(1, DETMInfluence(symbol_id="pulse", amplitude=0.02, region=(3, 3, 1)))

    runner.run(2)

    assert fired_ticks == [1]
    assert int(scheduler.tick) == 2
    assert int(session.state.step_count) == 4


def test_level_policy_batch_size_wiring_preserves_single_influence_apply():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(
            microsteps_per_global_tick=1,
            batch_size=2,
            commit_stride=1,
        ),
    )
    session = DetmSession.create(cfg, seed=7)

    influence = DETMInfluence(symbol_id="pulse", amplitude=0.05, region=(3, 3, 1))
    obs = session.step(influence, 5, rng=session.state.restore_rng())
    session.close()

    assert int(session.state.step_count) == 5
    influence_events = [event for event in list(obs.events) if str(event.get("type")) == "influence"]
    assert len(influence_events) == 1
    assert float(obs.cost["step_ops_estimate"]) == float(6 * 6 * 5)

