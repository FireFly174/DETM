"""LevelPolicy runtime contract and policy decisions."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Tuple

from detm.runtime.schemas import DETM_LEVEL_POLICY_V1


def _as_positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return int(default)
    return max(1, parsed)


def _normalize_allowed_event_types(value: Any, *, allow_empty: bool = False) -> Tuple[str, ...]:
    if value is None:
        return tuple() if allow_empty else ("*",)
    if isinstance(value, str):
        chunk = value.strip()
        if chunk:
            return (chunk,)
        return tuple() if allow_empty else ("*",)
    if isinstance(value, (list, tuple, set)):
        out = tuple(str(v).strip() for v in value if str(v).strip())
        if out:
            return out
        return tuple() if allow_empty else ("*",)
    return tuple() if allow_empty else ("*",)


def _as_non_negative_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return max(0, int(default))
    return max(0, parsed)


def _as_non_negative_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return max(0.0, float(default))
    return max(0.0, float(parsed))


def _as_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _normalize_string_tuple(value: Any) -> Tuple[str, ...]:
    if value is None:
        return tuple()
    if isinstance(value, str):
        chunk = value.strip()
        return (chunk,) if chunk else tuple()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    return tuple()


@dataclass(frozen=True)
class ObservabilityProfile:
    """Policy-driven observability filter for artifact publishing."""

    allowed_event_types: Tuple[str, ...] = ("*",)
    detail_mode: str = "standard"  # minimal | standard | debug
    adaptive_signal_event_types: Tuple[str, ...] = tuple()
    adaptive_detail_mode: str = "debug"
    adaptive_hold_ticks: int = 0
    adaptive_allowed_event_types: Tuple[str, ...] = ("*",)

    def allows_event_type(self, event_type: str) -> bool:
        if "*" in self.allowed_event_types:
            return True
        return str(event_type) in set(self.allowed_event_types)

    def normalized_detail_mode(self) -> str:
        mode = str(self.detail_mode).strip().lower()
        if mode in {"minimal", "standard", "debug"}:
            return mode
        return "standard"

    def normalized_adaptive_detail_mode(self) -> str:
        mode = str(self.adaptive_detail_mode).strip().lower()
        if mode in {"minimal", "standard", "debug"}:
            return mode
        return "debug"

    def adaptive_enabled(self) -> bool:
        return bool(len(tuple(self.adaptive_signal_event_types)) > 0)

    def allows_adaptive_signal(self, event_type: str) -> bool:
        if "*" in tuple(self.adaptive_signal_event_types):
            return True
        return str(event_type) in set(self.adaptive_signal_event_types)

    def adaptive_signal_triggered(self, events: Tuple[Dict[str, Any], ...] | list[Dict[str, Any]]) -> bool:
        if not self.adaptive_enabled():
            return False
        for event in list(events):
            event_type = str(dict(event).get("type", ""))
            if self.allows_adaptive_signal(event_type):
                return True
        return False

    def adaptive_profile(self) -> "ObservabilityProfile":
        allowed_event_types = (
            tuple(self.adaptive_allowed_event_types)
            if len(tuple(self.adaptive_allowed_event_types)) > 0
            else tuple(self.allowed_event_types)
        )
        return ObservabilityProfile(
            allowed_event_types=allowed_event_types,
            detail_mode=self.normalized_adaptive_detail_mode(),
            adaptive_signal_event_types=tuple(self.adaptive_signal_event_types),
            adaptive_detail_mode=self.normalized_adaptive_detail_mode(),
            adaptive_hold_ticks=max(0, int(self.adaptive_hold_ticks)),
            adaptive_allowed_event_types=allowed_event_types,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed_event_types": list(self.allowed_event_types),
            "detail_mode": self.normalized_detail_mode(),
            "adaptive_signal_event_types": list(self.adaptive_signal_event_types),
            "adaptive_detail_mode": self.normalized_adaptive_detail_mode(),
            "adaptive_hold_ticks": max(0, int(self.adaptive_hold_ticks)),
            "adaptive_allowed_event_types": list(self.adaptive_allowed_event_types),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "ObservabilityProfile":
        data = payload or {}
        return cls(
            allowed_event_types=_normalize_allowed_event_types(data.get("allowed_event_types")),
            detail_mode=str(data.get("detail_mode", "standard")),
            adaptive_signal_event_types=_normalize_allowed_event_types(
                data.get("adaptive_signal_event_types", []),
                allow_empty=True,
            ),
            adaptive_detail_mode=str(data.get("adaptive_detail_mode", "debug")),
            adaptive_hold_ticks=_as_non_negative_int(data.get("adaptive_hold_ticks", 0), default=0),
            adaptive_allowed_event_types=_normalize_allowed_event_types(data.get("adaptive_allowed_event_types", ["*"])),
        )


@dataclass(frozen=True)
class LevelPolicy:
    """Minimal runtime LevelPolicy for microsteps/publish/observability."""

    schema_version: str = DETM_LEVEL_POLICY_V1
    active_level: str = "L0"
    microsteps_per_global_tick: int = 1
    batch_size: int = 1
    commit_stride: int = 1
    audit_commit_enabled: bool = False
    audit_commit_stride: int = 10
    allow_refinement: bool = True
    refinement_capacity_overflow_ratio_threshold: float = 0.15
    refinement_capacity_overflow_mean_threshold: float = 0.5
    refinement_capacity_min_signals: int = 1
    refinement_capacity_temporal_ratio_threshold: float = 0.1
    refinement_capacity_temporal_window: int = 4
    refinement_capacity_temporal_required_hits: int = 3
    refinement_capacity_learned_hits_threshold: int = 0
    refinement_capacity_cross_level_window: int = 4
    refinement_capacity_cross_level_min_levels: int = 2
    refinement_capacity_operator_score_threshold: float = 1.0
    refinement_capacity_cross_node_min_signals: int = 1
    refinement_capacity_distributed_accepted_min: int = 0
    refinement_capacity_signed_acks_min: int = 0
    refinement_capacity_consensus_accepted_min: int = 0
    refinement_capacity_crypto_validator_coverage_min: float = 0.0
    refinement_capacity_attestation_validator_ids: Tuple[str, ...] = tuple()
    refinement_capacity_attestation_min_coverage: float = 0.0
    refinement_capacity_byzantine_clean_min: int = 0
    runtime_adaptive_signal_event_types: Tuple[str, ...] = tuple()
    runtime_adaptive_min_signals: int = 1
    runtime_adaptive_quality_oscillation_threshold: float = 0.0
    runtime_adaptive_quality_jitter_threshold: float = 0.0
    runtime_adaptive_cost_cpu_time_ms_threshold: float = 0.0
    runtime_adaptive_auto_profile: bool = False
    runtime_adaptive_stability_microsteps_delta: int = 1
    runtime_adaptive_stability_batch_size_delta: int = 0
    runtime_adaptive_stability_commit_stride_delta: int = -1
    runtime_adaptive_throughput_microsteps_delta: int = -1
    runtime_adaptive_throughput_batch_size_delta: int = 1
    runtime_adaptive_throughput_commit_stride_delta: int = 1
    runtime_adaptive_cooldown_ticks: int = 0
    runtime_adaptive_telemetry_sample_stride: int = 1
    runtime_adaptive_telemetry_aggregation_window: int = 8
    runtime_adaptive_guard_microsteps_min: int = 1
    runtime_adaptive_guard_microsteps_max: int = 0
    runtime_adaptive_guard_batch_size_min: int = 1
    runtime_adaptive_guard_batch_size_max: int = 0
    runtime_adaptive_guard_commit_stride_min: int = 1
    runtime_adaptive_guard_commit_stride_max: int = 0
    runtime_adaptive_guard_reject_unsafe: bool = False
    runtime_adaptive_use_deltas: bool = False
    runtime_adaptive_microsteps_delta: int = 0
    runtime_adaptive_batch_size_delta: int = 0
    runtime_adaptive_commit_stride_delta: int = 0
    runtime_adaptive_microsteps_per_global_tick: int = 0
    runtime_adaptive_batch_size: int = 0
    runtime_adaptive_commit_stride: int = 0
    runtime_adaptive_hold_ticks: int = 0
    observability_profile: ObservabilityProfile = field(default_factory=ObservabilityProfile)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "LevelPolicy":
        data = payload or {}
        observability_raw = data.get("observability_profile")
        if isinstance(observability_raw, ObservabilityProfile):
            observability = observability_raw
        elif isinstance(observability_raw, dict):
            observability = ObservabilityProfile.from_dict(observability_raw)
        else:
            observability = ObservabilityProfile()

        return cls(
            schema_version=str(data.get("schema_version", DETM_LEVEL_POLICY_V1)),
            active_level=str(data.get("active_level", "L0")),
            microsteps_per_global_tick=_as_positive_int(data.get("microsteps_per_global_tick"), default=1),
            batch_size=_as_positive_int(data.get("batch_size"), default=1),
            commit_stride=_as_positive_int(data.get("commit_stride"), default=1),
            audit_commit_enabled=bool(data.get("audit_commit_enabled", False)),
            audit_commit_stride=_as_positive_int(data.get("audit_commit_stride"), default=10),
            allow_refinement=bool(data.get("allow_refinement", True)),
            refinement_capacity_overflow_ratio_threshold=_as_non_negative_float(
                data.get("refinement_capacity_overflow_ratio_threshold", 0.15),
                default=0.15,
            ),
            refinement_capacity_overflow_mean_threshold=_as_non_negative_float(
                data.get("refinement_capacity_overflow_mean_threshold", 0.5),
                default=0.5,
            ),
            refinement_capacity_min_signals=_as_positive_int(
                data.get("refinement_capacity_min_signals", 1),
                default=1,
            ),
            refinement_capacity_temporal_ratio_threshold=_as_non_negative_float(
                data.get("refinement_capacity_temporal_ratio_threshold", 0.1),
                default=0.1,
            ),
            refinement_capacity_temporal_window=_as_positive_int(
                data.get("refinement_capacity_temporal_window", 4),
                default=4,
            ),
            refinement_capacity_temporal_required_hits=_as_positive_int(
                data.get("refinement_capacity_temporal_required_hits", 3),
                default=3,
            ),
            refinement_capacity_learned_hits_threshold=_as_non_negative_int(
                data.get("refinement_capacity_learned_hits_threshold", 0),
                default=0,
            ),
            refinement_capacity_cross_level_window=_as_positive_int(
                data.get("refinement_capacity_cross_level_window", 4),
                default=4,
            ),
            refinement_capacity_cross_level_min_levels=_as_positive_int(
                data.get("refinement_capacity_cross_level_min_levels", 2),
                default=2,
            ),
            refinement_capacity_operator_score_threshold=_as_non_negative_float(
                data.get("refinement_capacity_operator_score_threshold", 1.0),
                default=1.0,
            ),
            refinement_capacity_cross_node_min_signals=_as_positive_int(
                data.get("refinement_capacity_cross_node_min_signals", 1),
                default=1,
            ),
            refinement_capacity_distributed_accepted_min=_as_non_negative_int(
                data.get("refinement_capacity_distributed_accepted_min", 0),
                default=0,
            ),
            refinement_capacity_signed_acks_min=_as_non_negative_int(
                data.get("refinement_capacity_signed_acks_min", 0),
                default=0,
            ),
            refinement_capacity_consensus_accepted_min=_as_non_negative_int(
                data.get("refinement_capacity_consensus_accepted_min", 0),
                default=0,
            ),
            refinement_capacity_crypto_validator_coverage_min=_as_non_negative_float(
                data.get("refinement_capacity_crypto_validator_coverage_min", 0.0),
                default=0.0,
            ),
            refinement_capacity_attestation_validator_ids=_normalize_string_tuple(
                data.get("refinement_capacity_attestation_validator_ids", [])
            ),
            refinement_capacity_attestation_min_coverage=_as_non_negative_float(
                data.get("refinement_capacity_attestation_min_coverage", 0.0),
                default=0.0,
            ),
            refinement_capacity_byzantine_clean_min=_as_non_negative_int(
                data.get("refinement_capacity_byzantine_clean_min", 0),
                default=0,
            ),
            runtime_adaptive_signal_event_types=_normalize_allowed_event_types(
                data.get("runtime_adaptive_signal_event_types", []),
                allow_empty=True,
            ),
            runtime_adaptive_min_signals=_as_positive_int(
                data.get("runtime_adaptive_min_signals", 1),
                default=1,
            ),
            runtime_adaptive_quality_oscillation_threshold=_as_non_negative_float(
                data.get("runtime_adaptive_quality_oscillation_threshold", 0.0),
                default=0.0,
            ),
            runtime_adaptive_quality_jitter_threshold=_as_non_negative_float(
                data.get("runtime_adaptive_quality_jitter_threshold", 0.0),
                default=0.0,
            ),
            runtime_adaptive_cost_cpu_time_ms_threshold=_as_non_negative_float(
                data.get("runtime_adaptive_cost_cpu_time_ms_threshold", 0.0),
                default=0.0,
            ),
            runtime_adaptive_auto_profile=bool(data.get("runtime_adaptive_auto_profile", False)),
            runtime_adaptive_stability_microsteps_delta=_as_int(
                data.get("runtime_adaptive_stability_microsteps_delta", 1),
                default=1,
            ),
            runtime_adaptive_stability_batch_size_delta=_as_int(
                data.get("runtime_adaptive_stability_batch_size_delta", 0),
                default=0,
            ),
            runtime_adaptive_stability_commit_stride_delta=_as_int(
                data.get("runtime_adaptive_stability_commit_stride_delta", -1),
                default=-1,
            ),
            runtime_adaptive_throughput_microsteps_delta=_as_int(
                data.get("runtime_adaptive_throughput_microsteps_delta", -1),
                default=-1,
            ),
            runtime_adaptive_throughput_batch_size_delta=_as_int(
                data.get("runtime_adaptive_throughput_batch_size_delta", 1),
                default=1,
            ),
            runtime_adaptive_throughput_commit_stride_delta=_as_int(
                data.get("runtime_adaptive_throughput_commit_stride_delta", 1),
                default=1,
            ),
            runtime_adaptive_cooldown_ticks=_as_non_negative_int(
                data.get("runtime_adaptive_cooldown_ticks", 0),
                default=0,
            ),
            runtime_adaptive_telemetry_sample_stride=_as_positive_int(
                data.get("runtime_adaptive_telemetry_sample_stride", 1),
                default=1,
            ),
            runtime_adaptive_telemetry_aggregation_window=_as_positive_int(
                data.get("runtime_adaptive_telemetry_aggregation_window", 8),
                default=8,
            ),
            runtime_adaptive_guard_microsteps_min=_as_positive_int(
                data.get("runtime_adaptive_guard_microsteps_min", 1),
                default=1,
            ),
            runtime_adaptive_guard_microsteps_max=_as_non_negative_int(
                data.get("runtime_adaptive_guard_microsteps_max", 0),
                default=0,
            ),
            runtime_adaptive_guard_batch_size_min=_as_positive_int(
                data.get("runtime_adaptive_guard_batch_size_min", 1),
                default=1,
            ),
            runtime_adaptive_guard_batch_size_max=_as_non_negative_int(
                data.get("runtime_adaptive_guard_batch_size_max", 0),
                default=0,
            ),
            runtime_adaptive_guard_commit_stride_min=_as_positive_int(
                data.get("runtime_adaptive_guard_commit_stride_min", 1),
                default=1,
            ),
            runtime_adaptive_guard_commit_stride_max=_as_non_negative_int(
                data.get("runtime_adaptive_guard_commit_stride_max", 0),
                default=0,
            ),
            runtime_adaptive_guard_reject_unsafe=bool(data.get("runtime_adaptive_guard_reject_unsafe", False)),
            runtime_adaptive_use_deltas=bool(data.get("runtime_adaptive_use_deltas", False)),
            runtime_adaptive_microsteps_delta=_as_int(
                data.get("runtime_adaptive_microsteps_delta", 0),
                default=0,
            ),
            runtime_adaptive_batch_size_delta=_as_int(
                data.get("runtime_adaptive_batch_size_delta", 0),
                default=0,
            ),
            runtime_adaptive_commit_stride_delta=_as_int(
                data.get("runtime_adaptive_commit_stride_delta", 0),
                default=0,
            ),
            runtime_adaptive_microsteps_per_global_tick=_as_non_negative_int(
                data.get("runtime_adaptive_microsteps_per_global_tick", 0),
                default=0,
            ),
            runtime_adaptive_batch_size=_as_non_negative_int(
                data.get("runtime_adaptive_batch_size", 0),
                default=0,
            ),
            runtime_adaptive_commit_stride=_as_non_negative_int(
                data.get("runtime_adaptive_commit_stride", 0),
                default=0,
            ),
            runtime_adaptive_hold_ticks=_as_non_negative_int(
                data.get("runtime_adaptive_hold_ticks", 0),
                default=0,
            ),
            observability_profile=observability,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": str(self.schema_version),
            "active_level": str(self.active_level),
            "microsteps_per_global_tick": int(max(1, self.microsteps_per_global_tick)),
            "batch_size": int(max(1, self.batch_size)),
            "commit_stride": int(max(1, self.commit_stride)),
            "audit_commit_enabled": bool(self.audit_commit_enabled),
            "audit_commit_stride": int(max(1, self.audit_commit_stride)),
            "allow_refinement": bool(self.allow_refinement),
            "refinement_capacity_overflow_ratio_threshold": float(
                max(0.0, self.refinement_capacity_overflow_ratio_threshold)
            ),
            "refinement_capacity_overflow_mean_threshold": float(
                max(0.0, self.refinement_capacity_overflow_mean_threshold)
            ),
            "refinement_capacity_min_signals": int(max(1, self.refinement_capacity_min_signals)),
            "refinement_capacity_temporal_ratio_threshold": float(
                max(0.0, self.refinement_capacity_temporal_ratio_threshold)
            ),
            "refinement_capacity_temporal_window": int(max(1, self.refinement_capacity_temporal_window)),
            "refinement_capacity_temporal_required_hits": int(max(1, self.refinement_capacity_temporal_required_hits)),
            "refinement_capacity_learned_hits_threshold": int(max(0, self.refinement_capacity_learned_hits_threshold)),
            "refinement_capacity_cross_level_window": int(max(1, self.refinement_capacity_cross_level_window)),
            "refinement_capacity_cross_level_min_levels": int(max(1, self.refinement_capacity_cross_level_min_levels)),
            "refinement_capacity_operator_score_threshold": float(
                max(0.0, self.refinement_capacity_operator_score_threshold)
            ),
            "refinement_capacity_cross_node_min_signals": int(max(1, self.refinement_capacity_cross_node_min_signals)),
            "refinement_capacity_distributed_accepted_min": int(max(0, self.refinement_capacity_distributed_accepted_min)),
            "refinement_capacity_signed_acks_min": int(max(0, self.refinement_capacity_signed_acks_min)),
            "refinement_capacity_consensus_accepted_min": int(max(0, self.refinement_capacity_consensus_accepted_min)),
            "refinement_capacity_crypto_validator_coverage_min": float(
                max(0.0, self.refinement_capacity_crypto_validator_coverage_min)
            ),
            "refinement_capacity_attestation_validator_ids": list(
                tuple(self.refinement_capacity_attestation_validator_ids)
            ),
            "refinement_capacity_attestation_min_coverage": float(
                max(0.0, self.refinement_capacity_attestation_min_coverage)
            ),
            "refinement_capacity_byzantine_clean_min": int(max(0, self.refinement_capacity_byzantine_clean_min)),
            "runtime_adaptive_signal_event_types": list(self.runtime_adaptive_signal_event_types),
            "runtime_adaptive_min_signals": int(max(1, self.runtime_adaptive_min_signals)),
            "runtime_adaptive_quality_oscillation_threshold": float(
                max(0.0, self.runtime_adaptive_quality_oscillation_threshold)
            ),
            "runtime_adaptive_quality_jitter_threshold": float(
                max(0.0, self.runtime_adaptive_quality_jitter_threshold)
            ),
            "runtime_adaptive_cost_cpu_time_ms_threshold": float(
                max(0.0, self.runtime_adaptive_cost_cpu_time_ms_threshold)
            ),
            "runtime_adaptive_auto_profile": bool(self.runtime_adaptive_auto_profile),
            "runtime_adaptive_stability_microsteps_delta": int(self.runtime_adaptive_stability_microsteps_delta),
            "runtime_adaptive_stability_batch_size_delta": int(self.runtime_adaptive_stability_batch_size_delta),
            "runtime_adaptive_stability_commit_stride_delta": int(self.runtime_adaptive_stability_commit_stride_delta),
            "runtime_adaptive_throughput_microsteps_delta": int(self.runtime_adaptive_throughput_microsteps_delta),
            "runtime_adaptive_throughput_batch_size_delta": int(self.runtime_adaptive_throughput_batch_size_delta),
            "runtime_adaptive_throughput_commit_stride_delta": int(self.runtime_adaptive_throughput_commit_stride_delta),
            "runtime_adaptive_cooldown_ticks": int(max(0, self.runtime_adaptive_cooldown_ticks)),
            "runtime_adaptive_telemetry_sample_stride": int(max(1, self.runtime_adaptive_telemetry_sample_stride)),
            "runtime_adaptive_telemetry_aggregation_window": int(
                max(1, self.runtime_adaptive_telemetry_aggregation_window)
            ),
            "runtime_adaptive_guard_microsteps_min": int(max(1, self.runtime_adaptive_guard_microsteps_min)),
            "runtime_adaptive_guard_microsteps_max": int(max(0, self.runtime_adaptive_guard_microsteps_max)),
            "runtime_adaptive_guard_batch_size_min": int(max(1, self.runtime_adaptive_guard_batch_size_min)),
            "runtime_adaptive_guard_batch_size_max": int(max(0, self.runtime_adaptive_guard_batch_size_max)),
            "runtime_adaptive_guard_commit_stride_min": int(max(1, self.runtime_adaptive_guard_commit_stride_min)),
            "runtime_adaptive_guard_commit_stride_max": int(max(0, self.runtime_adaptive_guard_commit_stride_max)),
            "runtime_adaptive_guard_reject_unsafe": bool(self.runtime_adaptive_guard_reject_unsafe),
            "runtime_adaptive_use_deltas": bool(self.runtime_adaptive_use_deltas),
            "runtime_adaptive_microsteps_delta": int(self.runtime_adaptive_microsteps_delta),
            "runtime_adaptive_batch_size_delta": int(self.runtime_adaptive_batch_size_delta),
            "runtime_adaptive_commit_stride_delta": int(self.runtime_adaptive_commit_stride_delta),
            "runtime_adaptive_microsteps_per_global_tick": int(
                max(0, self.runtime_adaptive_microsteps_per_global_tick)
            ),
            "runtime_adaptive_batch_size": int(max(0, self.runtime_adaptive_batch_size)),
            "runtime_adaptive_commit_stride": int(max(0, self.runtime_adaptive_commit_stride)),
            "runtime_adaptive_hold_ticks": int(max(0, self.runtime_adaptive_hold_ticks)),
            "observability_profile": self.observability_profile.to_dict(),
        }

    def _decide_with_values(
        self,
        *,
        step_count: int,
        requested_n_ticks: int,
        microsteps_per_global_tick: int,
        batch_size: int,
        commit_stride: int,
    ) -> "PolicyDecision":
        requested = max(0, int(requested_n_ticks))
        microsteps = max(1, int(microsteps_per_global_tick))
        effective = int(requested * microsteps)
        before = int(step_count)
        after = before + effective
        stride = max(1, int(commit_stride))
        commit_boundary_crossed = effective > 0 and (before // stride) != (after // stride)
        return PolicyDecision(
            active_level=str(self.active_level),
            requested_n_ticks=requested,
            effective_n_ticks=effective,
            batch_size=max(1, int(batch_size)),
            commit_stride=stride,
            audit_commit_enabled=bool(self.audit_commit_enabled),
            audit_commit_stride=max(1, int(self.audit_commit_stride)),
            commit_boundary_crossed=bool(commit_boundary_crossed),
            allow_refinement=bool(self.allow_refinement),
            observability_profile=self.observability_profile,
        )

    def decide(self, *, step_count: int, requested_n_ticks: int) -> "PolicyDecision":
        return self._decide_with_values(
            step_count=step_count,
            requested_n_ticks=requested_n_ticks,
            microsteps_per_global_tick=max(1, int(self.microsteps_per_global_tick)),
            batch_size=max(1, int(self.batch_size)),
            commit_stride=max(1, int(self.commit_stride)),
        )

    def runtime_adaptive_enabled(self) -> bool:
        has_signal_criteria = bool(
            len(tuple(self.runtime_adaptive_signal_event_types)) > 0
            or float(self.runtime_adaptive_quality_oscillation_threshold) > 0.0
            or float(self.runtime_adaptive_quality_jitter_threshold) > 0.0
            or float(self.runtime_adaptive_cost_cpu_time_ms_threshold) > 0.0
        )
        has_profile_deltas = bool(
            bool(self.runtime_adaptive_auto_profile)
            and (
                int(self.runtime_adaptive_stability_microsteps_delta) != 0
                or int(self.runtime_adaptive_stability_batch_size_delta) != 0
                or int(self.runtime_adaptive_stability_commit_stride_delta) != 0
                or int(self.runtime_adaptive_throughput_microsteps_delta) != 0
                or int(self.runtime_adaptive_throughput_batch_size_delta) != 0
                or int(self.runtime_adaptive_throughput_commit_stride_delta) != 0
            )
        )
        has_delta_overrides = bool(
            bool(self.runtime_adaptive_use_deltas)
            and (
                int(self.runtime_adaptive_microsteps_delta) != 0
                or int(self.runtime_adaptive_batch_size_delta) != 0
                or int(self.runtime_adaptive_commit_stride_delta) != 0
            )
        )
        has_absolute_overrides = bool(
            int(self.runtime_adaptive_microsteps_per_global_tick) > 0
            or int(self.runtime_adaptive_batch_size) > 0
            or int(self.runtime_adaptive_commit_stride) > 0
        )
        return bool(
            has_signal_criteria
            and (has_profile_deltas or has_delta_overrides or has_absolute_overrides)
        )

    def allows_runtime_adaptive_signal(self, event_type: str) -> bool:
        if "*" in tuple(self.runtime_adaptive_signal_event_types):
            return True
        return str(event_type) in set(self.runtime_adaptive_signal_event_types)

    def runtime_adaptive_signal_triggered(
        self,
        events: Tuple[Dict[str, Any], ...] | list[Dict[str, Any]],
        *,
        quality: Dict[str, Any] | None = None,
        cost: Dict[str, Any] | None = None,
        signal_hits: Dict[str, bool] | None = None,
    ) -> bool:
        if not self.runtime_adaptive_enabled():
            return False
        hits = dict(signal_hits or {})
        if len(hits) == 0:
            hits = self.runtime_adaptive_signal_hits(events, quality=quality, cost=cost)

        configured_hits = []
        if len(tuple(self.runtime_adaptive_signal_event_types)) > 0:
            configured_hits.append(bool(hits.get("event", False)))
        if float(self.runtime_adaptive_quality_oscillation_threshold) > 0.0:
            configured_hits.append(bool(hits.get("quality_oscillation", False)))
        if float(self.runtime_adaptive_quality_jitter_threshold) > 0.0:
            configured_hits.append(bool(hits.get("quality_jitter", False)))
        if float(self.runtime_adaptive_cost_cpu_time_ms_threshold) > 0.0:
            configured_hits.append(bool(hits.get("cost_cpu_time", False)))

        if len(configured_hits) == 0:
            return False
        min_signals = max(1, int(self.runtime_adaptive_min_signals))
        return int(sum(1 for hit in configured_hits if bool(hit))) >= min_signals

    def runtime_adaptive_signal_hits(
        self,
        events: Tuple[Dict[str, Any], ...] | list[Dict[str, Any]],
        *,
        quality: Dict[str, Any] | None = None,
        cost: Dict[str, Any] | None = None,
    ) -> Dict[str, bool]:
        quality = dict(quality or {})
        cost = dict(cost or {})
        event_types = [str(dict(event).get("type", "")) for event in list(events)]

        event_hit = False
        if len(tuple(self.runtime_adaptive_signal_event_types)) > 0:
            event_hit = any(self.allows_runtime_adaptive_signal(event_type) for event_type in event_types)
        oscillation_hit = False
        if float(self.runtime_adaptive_quality_oscillation_threshold) > 0.0:
            oscillation = float(quality.get("oscillation_score", 0.0) or 0.0)
            oscillation_hit = bool(oscillation >= float(self.runtime_adaptive_quality_oscillation_threshold))
        jitter_hit = False
        if float(self.runtime_adaptive_quality_jitter_threshold) > 0.0:
            jitter = float(quality.get("jitter_signature", 0.0) or 0.0)
            jitter_hit = bool(jitter >= float(self.runtime_adaptive_quality_jitter_threshold))
        cpu_time_hit = False
        if float(self.runtime_adaptive_cost_cpu_time_ms_threshold) > 0.0:
            cpu_time_ms = float(cost.get("cpu_time_ms", 0.0) or 0.0)
            cpu_time_hit = bool(cpu_time_ms >= float(self.runtime_adaptive_cost_cpu_time_ms_threshold))

        return {
            "event": bool(event_hit),
            "quality_oscillation": bool(oscillation_hit),
            "quality_jitter": bool(jitter_hit),
            "quality": bool(oscillation_hit or jitter_hit),
            "cost_cpu_time": bool(cpu_time_hit),
        }

    def runtime_adaptive_profile_for_signal_hits(self, signal_hits: Dict[str, bool] | None = None) -> str:
        if not bool(self.runtime_adaptive_auto_profile):
            return "manual"
        hits = dict(signal_hits or {})
        if bool(hits.get("cost_cpu_time", False)):
            return "throughput"
        if bool(hits.get("event", False)) or bool(hits.get("quality", False)):
            return "stability"
        return "manual"

    def _runtime_adaptive_guard_bounds(self) -> Dict[str, tuple[int, int | None]]:
        micro_min = max(1, int(self.runtime_adaptive_guard_microsteps_min))
        batch_min = max(1, int(self.runtime_adaptive_guard_batch_size_min))
        commit_min = max(1, int(self.runtime_adaptive_guard_commit_stride_min))
        micro_max_raw = max(0, int(self.runtime_adaptive_guard_microsteps_max))
        batch_max_raw = max(0, int(self.runtime_adaptive_guard_batch_size_max))
        commit_max_raw = max(0, int(self.runtime_adaptive_guard_commit_stride_max))
        micro_max = None if micro_max_raw <= 0 else max(micro_min, micro_max_raw)
        batch_max = None if batch_max_raw <= 0 else max(batch_min, batch_max_raw)
        commit_max = None if commit_max_raw <= 0 else max(commit_min, commit_max_raw)
        return {
            "microsteps_per_global_tick": (micro_min, micro_max),
            "batch_size": (batch_min, batch_max),
            "commit_stride": (commit_min, commit_max),
        }

    def _apply_runtime_adaptive_guards(
        self,
        *,
        microsteps_per_global_tick: int,
        batch_size: int,
        commit_stride: int,
    ) -> tuple[int, int, int, Dict[str, Any]]:
        requested = {
            "microsteps_per_global_tick": max(1, int(microsteps_per_global_tick)),
            "batch_size": max(1, int(batch_size)),
            "commit_stride": max(1, int(commit_stride)),
        }
        bounds = self._runtime_adaptive_guard_bounds()
        violations: list[str] = []
        for key, value in requested.items():
            low, high = bounds[str(key)]
            if int(value) < int(low):
                violations.append(f"{key}<min")
            if high is not None and int(value) > int(high):
                violations.append(f"{key}>max")

        reject = bool(self.runtime_adaptive_guard_reject_unsafe) and len(violations) > 0
        if reject:
            applied = {
                "microsteps_per_global_tick": max(1, int(self.microsteps_per_global_tick)),
                "batch_size": max(1, int(self.batch_size)),
                "commit_stride": max(1, int(self.commit_stride)),
            }
            return (
                int(applied["microsteps_per_global_tick"]),
                int(applied["batch_size"]),
                int(applied["commit_stride"]),
                {
                    "enabled": True,
                    "rejected": True,
                    "violations": list(violations),
                    "requested": dict(requested),
                    "applied": dict(applied),
                    "clamped": {},
                },
            )

        clamped: Dict[str, int] = {}
        applied = dict(requested)
        for key, value in requested.items():
            low, high = bounds[str(key)]
            out = max(int(low), int(value))
            if high is not None:
                out = min(int(high), int(out))
            applied[str(key)] = int(out)
            if int(out) != int(value):
                clamped[str(key)] = int(out)

        return (
            int(applied["microsteps_per_global_tick"]),
            int(applied["batch_size"]),
            int(applied["commit_stride"]),
            {
                "enabled": True,
                "rejected": False,
                "violations": list(violations),
                "requested": dict(requested),
                "applied": dict(applied),
                "clamped": dict(clamped),
            },
        )

    def decide_runtime_adaptive(
        self,
        *,
        step_count: int,
        requested_n_ticks: int,
        profile: str = "manual",
    ) -> "PolicyDecision":
        profile_name = str(profile).strip().lower()
        if bool(self.runtime_adaptive_auto_profile) and profile_name in {"stability", "throughput"}:
            if profile_name == "stability":
                microsteps_delta = int(self.runtime_adaptive_stability_microsteps_delta)
                batch_delta = int(self.runtime_adaptive_stability_batch_size_delta)
                commit_stride_delta = int(self.runtime_adaptive_stability_commit_stride_delta)
            else:
                microsteps_delta = int(self.runtime_adaptive_throughput_microsteps_delta)
                batch_delta = int(self.runtime_adaptive_throughput_batch_size_delta)
                commit_stride_delta = int(self.runtime_adaptive_throughput_commit_stride_delta)
            if microsteps_delta != 0 or batch_delta != 0 or commit_stride_delta != 0:
                microsteps = max(1, int(self.microsteps_per_global_tick) + microsteps_delta)
                batch_size = max(1, int(self.batch_size) + batch_delta)
                commit_stride = max(1, int(self.commit_stride) + commit_stride_delta)
                guarded_microsteps, guarded_batch, guarded_stride, guard_meta = self._apply_runtime_adaptive_guards(
                    microsteps_per_global_tick=int(microsteps),
                    batch_size=int(batch_size),
                    commit_stride=int(commit_stride),
                )
                decision = self._decide_with_values(
                    step_count=step_count,
                    requested_n_ticks=requested_n_ticks,
                    microsteps_per_global_tick=int(guarded_microsteps),
                    batch_size=int(guarded_batch),
                    commit_stride=int(guarded_stride),
                )
                return replace(decision, runtime_adaptive_guard=dict(guard_meta))

        use_deltas = bool(self.runtime_adaptive_use_deltas) and (
            int(self.runtime_adaptive_microsteps_delta) != 0
            or int(self.runtime_adaptive_batch_size_delta) != 0
            or int(self.runtime_adaptive_commit_stride_delta) != 0
        )
        if use_deltas:
            microsteps = max(1, int(self.microsteps_per_global_tick) + int(self.runtime_adaptive_microsteps_delta))
            batch_size = max(1, int(self.batch_size) + int(self.runtime_adaptive_batch_size_delta))
            commit_stride = max(1, int(self.commit_stride) + int(self.runtime_adaptive_commit_stride_delta))
            guarded_microsteps, guarded_batch, guarded_stride, guard_meta = self._apply_runtime_adaptive_guards(
                microsteps_per_global_tick=int(microsteps),
                batch_size=int(batch_size),
                commit_stride=int(commit_stride),
            )
            decision = self._decide_with_values(
                step_count=step_count,
                requested_n_ticks=requested_n_ticks,
                microsteps_per_global_tick=int(guarded_microsteps),
                batch_size=int(guarded_batch),
                commit_stride=int(guarded_stride),
            )
            return replace(decision, runtime_adaptive_guard=dict(guard_meta))

        guarded_microsteps, guarded_batch, guarded_stride, guard_meta = self._apply_runtime_adaptive_guards(
            microsteps_per_global_tick=(
                int(self.runtime_adaptive_microsteps_per_global_tick)
                if int(self.runtime_adaptive_microsteps_per_global_tick) > 0
                else int(self.microsteps_per_global_tick)
            ),
            batch_size=(
                int(self.runtime_adaptive_batch_size)
                if int(self.runtime_adaptive_batch_size) > 0
                else int(self.batch_size)
            ),
            commit_stride=(
                int(self.runtime_adaptive_commit_stride)
                if int(self.runtime_adaptive_commit_stride) > 0
                else int(self.commit_stride)
            ),
        )
        decision = self._decide_with_values(
            step_count=step_count,
            requested_n_ticks=requested_n_ticks,
            microsteps_per_global_tick=int(guarded_microsteps),
            batch_size=int(guarded_batch),
            commit_stride=int(guarded_stride),
        )
        return replace(decision, runtime_adaptive_guard=dict(guard_meta))


@dataclass(frozen=True)
class PolicyDecision:
    """Resolved decision for one requested session step."""

    active_level: str
    requested_n_ticks: int
    effective_n_ticks: int
    batch_size: int
    commit_stride: int
    audit_commit_enabled: bool
    audit_commit_stride: int
    commit_boundary_crossed: bool
    allow_refinement: bool
    observability_profile: ObservabilityProfile
    runtime_adaptive_window_active: bool = False
    runtime_adaptive_profile: str = "manual"
    runtime_adaptive_signal_triggered: bool = False
    runtime_adaptive_signal_hits: Dict[str, bool] = field(default_factory=dict)
    runtime_adaptive_signal_hits_sampled: bool = False
    runtime_adaptive_aggregate: Dict[str, Any] = field(default_factory=dict)
    runtime_adaptive_guard: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_level": str(self.active_level),
            "requested_n_ticks": int(self.requested_n_ticks),
            "effective_n_ticks": int(self.effective_n_ticks),
            "batch_size": int(self.batch_size),
            "commit_stride": int(self.commit_stride),
            "audit_commit_enabled": bool(self.audit_commit_enabled),
            "audit_commit_stride": int(self.audit_commit_stride),
            "commit_boundary_crossed": bool(self.commit_boundary_crossed),
            "allow_refinement": bool(self.allow_refinement),
            "observability_profile": self.observability_profile.to_dict(),
            "runtime_adaptive_window_active": bool(self.runtime_adaptive_window_active),
            "runtime_adaptive_profile": str(self.runtime_adaptive_profile),
            "runtime_adaptive_signal_triggered": bool(self.runtime_adaptive_signal_triggered),
            "runtime_adaptive_signal_hits": {
                str(k): bool(v) for k, v in dict(self.runtime_adaptive_signal_hits).items()
            },
            "runtime_adaptive_signal_hits_sampled": bool(self.runtime_adaptive_signal_hits_sampled),
            "runtime_adaptive_aggregate": dict(self.runtime_adaptive_aggregate),
            "runtime_adaptive_guard": dict(self.runtime_adaptive_guard),
        }


__all__ = ["LevelPolicy", "ObservabilityProfile", "PolicyDecision"]
