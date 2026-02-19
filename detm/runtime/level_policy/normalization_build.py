"""Builders for level policy contracts from raw payload dictionaries."""

from __future__ import annotations

from typing import Any

from detm.runtime.level_policy.normalization_inputs import (
    as_int,
    as_non_negative_float,
    as_non_negative_int,
    as_positive_int,
    normalize_allowed_event_types,
    normalize_string_tuple,
)
from detm.runtime.schemas import DETM_LEVEL_POLICY_V1


def build_observability_profile(payload: dict[str, Any] | None, *, profile_cls: Any):
    data = payload or {}
    return profile_cls(
        allowed_event_types=normalize_allowed_event_types(data.get("allowed_event_types")),
        detail_mode=str(data.get("detail_mode", "standard")),
        adaptive_signal_event_types=normalize_allowed_event_types(
            data.get("adaptive_signal_event_types", []),
            allow_empty=True,
        ),
        adaptive_detail_mode=str(data.get("adaptive_detail_mode", "debug")),
        adaptive_hold_ticks=as_non_negative_int(data.get("adaptive_hold_ticks", 0), default=0),
        adaptive_allowed_event_types=normalize_allowed_event_types(data.get("adaptive_allowed_event_types", ["*"])),
    )


def build_level_policy(payload: dict[str, Any] | None, *, level_policy_cls: Any, observability_cls: Any):
    data = payload or {}
    observability_raw = data.get("observability_profile")
    if isinstance(observability_raw, observability_cls):
        observability = observability_raw
    elif isinstance(observability_raw, dict):
        observability = build_observability_profile(observability_raw, profile_cls=observability_cls)
    else:
        observability = observability_cls()

    return level_policy_cls(
        schema_version=str(data.get("schema_version", DETM_LEVEL_POLICY_V1)),
        active_level=str(data.get("active_level", "L0")),
        microsteps_per_global_tick=as_positive_int(data.get("microsteps_per_global_tick"), default=1),
        batch_size=as_positive_int(data.get("batch_size"), default=1),
        commit_stride=as_positive_int(data.get("commit_stride"), default=1),
        audit_commit_enabled=bool(data.get("audit_commit_enabled", False)),
        audit_commit_stride=as_positive_int(data.get("audit_commit_stride"), default=10),
        allow_refinement=bool(data.get("allow_refinement", True)),
        refinement_capacity_overflow_ratio_threshold=as_non_negative_float(
            data.get("refinement_capacity_overflow_ratio_threshold", 0.15),
            default=0.15,
        ),
        refinement_capacity_overflow_mean_threshold=as_non_negative_float(
            data.get("refinement_capacity_overflow_mean_threshold", 0.5),
            default=0.5,
        ),
        refinement_capacity_saturation_band=as_non_negative_float(
            data.get("refinement_capacity_saturation_band", 0.0),
            default=0.0,
        ),
        refinement_capacity_min_signals=as_positive_int(
            data.get("refinement_capacity_min_signals", 1),
            default=1,
        ),
        refinement_capacity_autoclamp_enabled=bool(
            data.get("refinement_capacity_autoclamp_enabled", False)
        ),
        refinement_capacity_temporal_ratio_threshold=as_non_negative_float(
            data.get("refinement_capacity_temporal_ratio_threshold", 0.1),
            default=0.1,
        ),
        refinement_capacity_temporal_window=as_positive_int(
            data.get("refinement_capacity_temporal_window", 4),
            default=4,
        ),
        refinement_capacity_temporal_required_hits=as_positive_int(
            data.get("refinement_capacity_temporal_required_hits", 3),
            default=3,
        ),
        refinement_capacity_learned_hits_threshold=as_non_negative_int(
            data.get("refinement_capacity_learned_hits_threshold", 0),
            default=0,
        ),
        refinement_capacity_cross_level_window=as_positive_int(
            data.get("refinement_capacity_cross_level_window", 4),
            default=4,
        ),
        refinement_capacity_cross_level_min_levels=as_positive_int(
            data.get("refinement_capacity_cross_level_min_levels", 2),
            default=2,
        ),
        refinement_capacity_operator_score_threshold=as_non_negative_float(
            data.get("refinement_capacity_operator_score_threshold", 1.0),
            default=1.0,
        ),
        refinement_capacity_cross_node_min_signals=as_positive_int(
            data.get("refinement_capacity_cross_node_min_signals", 1),
            default=1,
        ),
        refinement_capacity_distributed_accepted_min=as_non_negative_int(
            data.get("refinement_capacity_distributed_accepted_min", 0),
            default=0,
        ),
        refinement_capacity_signed_acks_min=as_non_negative_int(
            data.get("refinement_capacity_signed_acks_min", 0),
            default=0,
        ),
        refinement_capacity_consensus_accepted_min=as_non_negative_int(
            data.get("refinement_capacity_consensus_accepted_min", 0),
            default=0,
        ),
        refinement_capacity_crypto_validator_coverage_min=as_non_negative_float(
            data.get("refinement_capacity_crypto_validator_coverage_min", 0.0),
            default=0.0,
        ),
        refinement_capacity_attestation_validator_ids=normalize_string_tuple(
            data.get("refinement_capacity_attestation_validator_ids", [])
        ),
        refinement_capacity_attestation_min_coverage=as_non_negative_float(
            data.get("refinement_capacity_attestation_min_coverage", 0.0),
            default=0.0,
        ),
        refinement_capacity_byzantine_clean_min=as_non_negative_int(
            data.get("refinement_capacity_byzantine_clean_min", 0),
            default=0,
        ),
        refinement_operator_torsion_threshold=as_non_negative_float(
            data.get("refinement_operator_torsion_threshold", 1.0),
            default=1.0,
        ),
        refinement_operator_torsion_guard_enabled=bool(data.get("refinement_operator_torsion_guard_enabled", True)),
        refinement_operator_history_limit=as_positive_int(
            data.get("refinement_operator_history_limit", 256),
            default=256,
        ),
        anti_goodhart_enabled=bool(data.get("anti_goodhart_enabled", True)),
        anti_goodhart_target_signal=str(data.get("anti_goodhart_target_signal", "operator_reuse")),
        anti_goodhart_min_target_delta=as_non_negative_float(
            data.get("anti_goodhart_min_target_delta", 0.0),
            default=0.0,
        ),
        anti_goodhart_min_degraded_signals=as_positive_int(
            data.get("anti_goodhart_min_degraded_signals", 2),
            default=2,
        ),
        anti_goodhart_degradation_epsilon=as_non_negative_float(
            data.get("anti_goodhart_degradation_epsilon", 0.0),
            default=0.0,
        ),
        anti_goodhart_policy_reaction_enabled=bool(data.get("anti_goodhart_policy_reaction_enabled", True)),
        anti_goodhart_prefer_runtime_profile=str(
            data.get("anti_goodhart_prefer_runtime_profile", "stability")
        ),
        runtime_adaptive_signal_event_types=normalize_allowed_event_types(
            data.get("runtime_adaptive_signal_event_types", []),
            allow_empty=True,
        ),
        runtime_adaptive_min_signals=as_positive_int(
            data.get("runtime_adaptive_min_signals", 1),
            default=1,
        ),
        runtime_adaptive_quality_oscillation_threshold=as_non_negative_float(
            data.get("runtime_adaptive_quality_oscillation_threshold", 0.0),
            default=0.0,
        ),
        runtime_adaptive_quality_jitter_threshold=as_non_negative_float(
            data.get("runtime_adaptive_quality_jitter_threshold", 0.0),
            default=0.0,
        ),
        runtime_adaptive_cost_cpu_time_ms_threshold=as_non_negative_float(
            data.get("runtime_adaptive_cost_cpu_time_ms_threshold", 0.0),
            default=0.0,
        ),
        runtime_adaptive_auto_profile=bool(data.get("runtime_adaptive_auto_profile", False)),
        runtime_adaptive_stability_microsteps_delta=as_int(
            data.get("runtime_adaptive_stability_microsteps_delta", 1),
            default=1,
        ),
        runtime_adaptive_stability_batch_size_delta=as_int(
            data.get("runtime_adaptive_stability_batch_size_delta", 0),
            default=0,
        ),
        runtime_adaptive_stability_commit_stride_delta=as_int(
            data.get("runtime_adaptive_stability_commit_stride_delta", -1),
            default=-1,
        ),
        runtime_adaptive_throughput_microsteps_delta=as_int(
            data.get("runtime_adaptive_throughput_microsteps_delta", -1),
            default=-1,
        ),
        runtime_adaptive_throughput_batch_size_delta=as_int(
            data.get("runtime_adaptive_throughput_batch_size_delta", 1),
            default=1,
        ),
        runtime_adaptive_throughput_commit_stride_delta=as_int(
            data.get("runtime_adaptive_throughput_commit_stride_delta", 1),
            default=1,
        ),
        runtime_adaptive_cooldown_ticks=as_non_negative_int(
            data.get("runtime_adaptive_cooldown_ticks", 0),
            default=0,
        ),
        runtime_adaptive_telemetry_sample_stride=as_positive_int(
            data.get("runtime_adaptive_telemetry_sample_stride", 1),
            default=1,
        ),
        runtime_adaptive_telemetry_aggregation_window=as_positive_int(
            data.get("runtime_adaptive_telemetry_aggregation_window", 8),
            default=8,
        ),
        runtime_adaptive_guard_microsteps_min=as_positive_int(
            data.get("runtime_adaptive_guard_microsteps_min", 1),
            default=1,
        ),
        runtime_adaptive_guard_microsteps_max=as_non_negative_int(
            data.get("runtime_adaptive_guard_microsteps_max", 0),
            default=0,
        ),
        runtime_adaptive_guard_batch_size_min=as_positive_int(
            data.get("runtime_adaptive_guard_batch_size_min", 1),
            default=1,
        ),
        runtime_adaptive_guard_batch_size_max=as_non_negative_int(
            data.get("runtime_adaptive_guard_batch_size_max", 0),
            default=0,
        ),
        runtime_adaptive_guard_commit_stride_min=as_positive_int(
            data.get("runtime_adaptive_guard_commit_stride_min", 1),
            default=1,
        ),
        runtime_adaptive_guard_commit_stride_max=as_non_negative_int(
            data.get("runtime_adaptive_guard_commit_stride_max", 0),
            default=0,
        ),
        runtime_adaptive_guard_reject_unsafe=bool(data.get("runtime_adaptive_guard_reject_unsafe", False)),
        runtime_adaptive_use_deltas=bool(data.get("runtime_adaptive_use_deltas", False)),
        runtime_adaptive_microsteps_delta=as_int(
            data.get("runtime_adaptive_microsteps_delta", 0),
            default=0,
        ),
        runtime_adaptive_batch_size_delta=as_int(
            data.get("runtime_adaptive_batch_size_delta", 0),
            default=0,
        ),
        runtime_adaptive_commit_stride_delta=as_int(
            data.get("runtime_adaptive_commit_stride_delta", 0),
            default=0,
        ),
        runtime_adaptive_microsteps_per_global_tick=as_non_negative_int(
            data.get("runtime_adaptive_microsteps_per_global_tick", 0),
            default=0,
        ),
        runtime_adaptive_batch_size=as_non_negative_int(
            data.get("runtime_adaptive_batch_size", 0),
            default=0,
        ),
        runtime_adaptive_commit_stride=as_non_negative_int(
            data.get("runtime_adaptive_commit_stride", 0),
            default=0,
        ),
        runtime_adaptive_hold_ticks=as_non_negative_int(
            data.get("runtime_adaptive_hold_ticks", 0),
            default=0,
        ),
        observability_profile=observability,
    )


__all__ = ["build_level_policy", "build_observability_profile"]
