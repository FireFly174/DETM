"""Serialization helpers for level policy contracts."""

from __future__ import annotations

from typing import Any


def serialize_observability_profile(profile: Any) -> dict[str, Any]:
    return {
        "allowed_event_types": list(profile.allowed_event_types),
        "detail_mode": profile.normalized_detail_mode(),
        "adaptive_signal_event_types": list(profile.adaptive_signal_event_types),
        "adaptive_detail_mode": profile.normalized_adaptive_detail_mode(),
        "adaptive_hold_ticks": max(0, int(profile.adaptive_hold_ticks)),
        "adaptive_allowed_event_types": list(profile.adaptive_allowed_event_types),
    }


def serialize_level_policy(policy: Any) -> dict[str, Any]:
    return {
        "schema_version": str(policy.schema_version),
        "active_level": str(policy.active_level),
        "microsteps_per_global_tick": int(max(1, policy.microsteps_per_global_tick)),
        "batch_size": int(max(1, policy.batch_size)),
        "commit_stride": int(max(1, policy.commit_stride)),
        "audit_commit_enabled": bool(policy.audit_commit_enabled),
        "audit_commit_stride": int(max(1, policy.audit_commit_stride)),
        "allow_refinement": bool(policy.allow_refinement),
        "refinement_capacity_overflow_ratio_threshold": float(max(0.0, policy.refinement_capacity_overflow_ratio_threshold)),
        "refinement_capacity_overflow_mean_threshold": float(max(0.0, policy.refinement_capacity_overflow_mean_threshold)),
        "refinement_capacity_min_signals": int(max(1, policy.refinement_capacity_min_signals)),
        "refinement_capacity_temporal_ratio_threshold": float(max(0.0, policy.refinement_capacity_temporal_ratio_threshold)),
        "refinement_capacity_temporal_window": int(max(1, policy.refinement_capacity_temporal_window)),
        "refinement_capacity_temporal_required_hits": int(max(1, policy.refinement_capacity_temporal_required_hits)),
        "refinement_capacity_learned_hits_threshold": int(max(0, policy.refinement_capacity_learned_hits_threshold)),
        "refinement_capacity_cross_level_window": int(max(1, policy.refinement_capacity_cross_level_window)),
        "refinement_capacity_cross_level_min_levels": int(max(1, policy.refinement_capacity_cross_level_min_levels)),
        "refinement_capacity_operator_score_threshold": float(max(0.0, policy.refinement_capacity_operator_score_threshold)),
        "refinement_capacity_cross_node_min_signals": int(max(1, policy.refinement_capacity_cross_node_min_signals)),
        "refinement_capacity_distributed_accepted_min": int(max(0, policy.refinement_capacity_distributed_accepted_min)),
        "refinement_capacity_signed_acks_min": int(max(0, policy.refinement_capacity_signed_acks_min)),
        "refinement_capacity_consensus_accepted_min": int(max(0, policy.refinement_capacity_consensus_accepted_min)),
        "refinement_capacity_crypto_validator_coverage_min": float(max(0.0, policy.refinement_capacity_crypto_validator_coverage_min)),
        "refinement_capacity_attestation_validator_ids": list(tuple(policy.refinement_capacity_attestation_validator_ids)),
        "refinement_capacity_attestation_min_coverage": float(max(0.0, policy.refinement_capacity_attestation_min_coverage)),
        "refinement_capacity_byzantine_clean_min": int(max(0, policy.refinement_capacity_byzantine_clean_min)),
        "runtime_adaptive_signal_event_types": list(policy.runtime_adaptive_signal_event_types),
        "runtime_adaptive_min_signals": int(max(1, policy.runtime_adaptive_min_signals)),
        "runtime_adaptive_quality_oscillation_threshold": float(max(0.0, policy.runtime_adaptive_quality_oscillation_threshold)),
        "runtime_adaptive_quality_jitter_threshold": float(max(0.0, policy.runtime_adaptive_quality_jitter_threshold)),
        "runtime_adaptive_cost_cpu_time_ms_threshold": float(max(0.0, policy.runtime_adaptive_cost_cpu_time_ms_threshold)),
        "runtime_adaptive_auto_profile": bool(policy.runtime_adaptive_auto_profile),
        "runtime_adaptive_stability_microsteps_delta": int(policy.runtime_adaptive_stability_microsteps_delta),
        "runtime_adaptive_stability_batch_size_delta": int(policy.runtime_adaptive_stability_batch_size_delta),
        "runtime_adaptive_stability_commit_stride_delta": int(policy.runtime_adaptive_stability_commit_stride_delta),
        "runtime_adaptive_throughput_microsteps_delta": int(policy.runtime_adaptive_throughput_microsteps_delta),
        "runtime_adaptive_throughput_batch_size_delta": int(policy.runtime_adaptive_throughput_batch_size_delta),
        "runtime_adaptive_throughput_commit_stride_delta": int(policy.runtime_adaptive_throughput_commit_stride_delta),
        "runtime_adaptive_cooldown_ticks": int(max(0, policy.runtime_adaptive_cooldown_ticks)),
        "runtime_adaptive_telemetry_sample_stride": int(max(1, policy.runtime_adaptive_telemetry_sample_stride)),
        "runtime_adaptive_telemetry_aggregation_window": int(max(1, policy.runtime_adaptive_telemetry_aggregation_window)),
        "runtime_adaptive_guard_microsteps_min": int(max(1, policy.runtime_adaptive_guard_microsteps_min)),
        "runtime_adaptive_guard_microsteps_max": int(max(0, policy.runtime_adaptive_guard_microsteps_max)),
        "runtime_adaptive_guard_batch_size_min": int(max(1, policy.runtime_adaptive_guard_batch_size_min)),
        "runtime_adaptive_guard_batch_size_max": int(max(0, policy.runtime_adaptive_guard_batch_size_max)),
        "runtime_adaptive_guard_commit_stride_min": int(max(1, policy.runtime_adaptive_guard_commit_stride_min)),
        "runtime_adaptive_guard_commit_stride_max": int(max(0, policy.runtime_adaptive_guard_commit_stride_max)),
        "runtime_adaptive_guard_reject_unsafe": bool(policy.runtime_adaptive_guard_reject_unsafe),
        "runtime_adaptive_use_deltas": bool(policy.runtime_adaptive_use_deltas),
        "runtime_adaptive_microsteps_delta": int(policy.runtime_adaptive_microsteps_delta),
        "runtime_adaptive_batch_size_delta": int(policy.runtime_adaptive_batch_size_delta),
        "runtime_adaptive_commit_stride_delta": int(policy.runtime_adaptive_commit_stride_delta),
        "runtime_adaptive_microsteps_per_global_tick": int(max(0, policy.runtime_adaptive_microsteps_per_global_tick)),
        "runtime_adaptive_batch_size": int(max(0, policy.runtime_adaptive_batch_size)),
        "runtime_adaptive_commit_stride": int(max(0, policy.runtime_adaptive_commit_stride)),
        "runtime_adaptive_hold_ticks": int(max(0, policy.runtime_adaptive_hold_ticks)),
        "observability_profile": serialize_observability_profile(policy.observability_profile),
    }


__all__ = ["serialize_level_policy", "serialize_observability_profile"]
