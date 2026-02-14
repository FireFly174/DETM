"""Level policy models for runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from detm.runtime.level_policy.decision_runtime_adaptive import (
    decide_runtime_adaptive_policy as _decide_runtime_adaptive_policy,
)
from detm.runtime.level_policy.decision_signals import (
    allows_runtime_adaptive_signal as _allows_runtime_adaptive_signal,
    runtime_adaptive_enabled as _runtime_adaptive_enabled,
    runtime_adaptive_profile_for_signal_hits as _runtime_adaptive_profile_for_signal_hits,
    runtime_adaptive_signal_hits as _runtime_adaptive_signal_hits,
    runtime_adaptive_signal_triggered as _runtime_adaptive_signal_triggered,
)
from detm.runtime.level_policy.normalization_build import (
    build_level_policy as _build_level_policy,
    build_observability_profile as _build_observability_profile,
)
from detm.runtime.level_policy.normalization_serialize import (
    serialize_level_policy as _serialize_level_policy,
    serialize_observability_profile as _serialize_observability_profile,
)
from detm.runtime.schemas import DETM_LEVEL_POLICY_V1


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
        return _serialize_observability_profile(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "ObservabilityProfile":
        return _build_observability_profile(payload, profile_cls=cls)


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
        return _build_level_policy(payload, level_policy_cls=cls, observability_cls=ObservabilityProfile)

    def to_dict(self) -> Dict[str, Any]:
        return _serialize_level_policy(self)

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
        return _runtime_adaptive_enabled(self)

    def allows_runtime_adaptive_signal(self, event_type: str) -> bool:
        return _allows_runtime_adaptive_signal(self, event_type=event_type)

    def runtime_adaptive_signal_triggered(
        self,
        events: Tuple[Dict[str, Any], ...] | list[Dict[str, Any]],
        *,
        quality: Dict[str, Any] | None = None,
        cost: Dict[str, Any] | None = None,
        signal_hits: Dict[str, bool] | None = None,
    ) -> bool:
        return _runtime_adaptive_signal_triggered(
            self,
            events=events,
            quality=quality,
            cost=cost,
            signal_hits=signal_hits,
        )

    def runtime_adaptive_signal_hits(
        self,
        events: Tuple[Dict[str, Any], ...] | list[Dict[str, Any]],
        *,
        quality: Dict[str, Any] | None = None,
        cost: Dict[str, Any] | None = None,
    ) -> Dict[str, bool]:
        return _runtime_adaptive_signal_hits(self, events=events, quality=quality, cost=cost)

    def runtime_adaptive_profile_for_signal_hits(self, signal_hits: Dict[str, bool] | None = None) -> str:
        return _runtime_adaptive_profile_for_signal_hits(self, signal_hits=signal_hits)

    def decide_runtime_adaptive(
        self,
        *,
        step_count: int,
        requested_n_ticks: int,
        profile: str = "manual",
    ) -> "PolicyDecision":
        return _decide_runtime_adaptive_policy(
            self,
            step_count=step_count,
            requested_n_ticks=requested_n_ticks,
            profile=profile,
        )


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
