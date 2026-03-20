"""Step-path helpers for runtime API."""

from __future__ import annotations

from typing import Any

from detm.runtime.api.helpers import (
    apply_quality_proxies as _apply_quality_proxies,
    estimate_array_bytes as _estimate_array_bytes,
    to_numpy as _to_numpy,
)
from detm.runtime.api.models import FieldSummaries, Observables
from detm.runtime.config import DETMConfig
from detm.runtime.diagnostics.attractors import detect_attractors
from detm.runtime.influence import DETMInfluence
from detm.runtime.refinement import maybe_apply_refinement
from detm.runtime.signature import describe_field_any, digest_fields_any, project_field_plane_any
from detm.runtime.state import DETMState


def is_override_only_influence(influence: DETMInfluence) -> bool:
    return bool(
        abs(float(influence.amplitude)) < 1e-12
        and influence.mask is None
        and influence.region is None
        and influence.external_features is None
        and influence.seed is None
        and influence.phase is None
        and influence.duration is None
        and bool(influence.dynamics_overrides)
    )


def ensure_refinement_runtime_memory(state: DETMState) -> dict[str, Any]:
    refinement_runtime = getattr(state, "_refinement_runtime", None)
    if not isinstance(refinement_runtime, dict):
        refinement_runtime = {}
        setattr(state, "_refinement_runtime", refinement_runtime)
    operator_signal_score = getattr(state, "_operator_capacity_signal_score", None)
    if operator_signal_score is not None:
        try:
            refinement_runtime["operator_capacity_signal_score"] = float(operator_signal_score)
        except (TypeError, ValueError):
            pass
    fabric_snapshot = getattr(state, "_fabric_quorum_snapshot", None)
    if isinstance(fabric_snapshot, dict):
        refinement_runtime["fabric_quorum_snapshot"] = dict(fabric_snapshot)
    return refinement_runtime


def maybe_refinement_event(
    *,
    state: DETMState,
    config: DETMConfig,
    dynamics: Any,
    pattern_runtime: Any,
    refinement_runtime: dict[str, Any],
) -> dict[str, Any] | None:
    return maybe_apply_refinement(
        field_state=state.field_state,
        dynamics=dynamics,
        allow_refinement=bool(config.level_policy.allow_refinement),
        capacity_overflow_ratio_threshold=float(config.level_policy.refinement_capacity_overflow_ratio_threshold),
        capacity_overflow_mean_threshold=float(config.level_policy.refinement_capacity_overflow_mean_threshold),
        capacity_saturation_band=float(config.level_policy.refinement_capacity_saturation_band),
        capacity_min_signals=int(config.level_policy.refinement_capacity_min_signals),
        capacity_autoclamp_enabled=bool(config.level_policy.refinement_capacity_autoclamp_enabled),
        capacity_temporal_ratio_threshold=float(config.level_policy.refinement_capacity_temporal_ratio_threshold),
        capacity_temporal_window=int(config.level_policy.refinement_capacity_temporal_window),
        capacity_temporal_required_hits=int(config.level_policy.refinement_capacity_temporal_required_hits),
        capacity_learned_hits_threshold=int(config.level_policy.refinement_capacity_learned_hits_threshold),
        capacity_cross_level_window=int(config.level_policy.refinement_capacity_cross_level_window),
        capacity_cross_level_min_levels=int(config.level_policy.refinement_capacity_cross_level_min_levels),
        capacity_operator_score_threshold=float(config.level_policy.refinement_capacity_operator_score_threshold),
        capacity_cross_node_min_signals=int(config.level_policy.refinement_capacity_cross_node_min_signals),
        capacity_distributed_accepted_min=int(config.level_policy.refinement_capacity_distributed_accepted_min),
        capacity_signed_acks_min=int(config.level_policy.refinement_capacity_signed_acks_min),
        capacity_consensus_accepted_min=int(config.level_policy.refinement_capacity_consensus_accepted_min),
        capacity_crypto_validator_coverage_min=float(config.level_policy.refinement_capacity_crypto_validator_coverage_min),
        capacity_attestation_validator_ids=tuple(config.level_policy.refinement_capacity_attestation_validator_ids),
        capacity_attestation_min_coverage=float(config.level_policy.refinement_capacity_attestation_min_coverage),
        capacity_byzantine_clean_min=int(config.level_policy.refinement_capacity_byzantine_clean_min),
        operator_torsion_threshold=float(config.level_policy.refinement_operator_torsion_threshold),
        operator_torsion_guard_enabled=bool(config.level_policy.refinement_operator_torsion_guard_enabled),
        operator_history_limit=int(config.level_policy.refinement_operator_history_limit),
        pattern_runtime=pattern_runtime,
        step_count=int(state.step_count),
        active_level=str(config.level_policy.active_level),
        pattern_mode=str(config.observables_mode),
        runtime_memory=refinement_runtime,
    )


def build_observables(
    *,
    state: DETMState,
    config: DETMConfig,
    n_ticks: int,
    elapsed_s: float,
    refinement_event: dict[str, Any] | None,
    influence_application: Any | None,
) -> Observables:
    full_energy = state.field_state.energy
    full_entropy = state.field_state.entropy
    full_internal_time = state.field_state.internal_time
    energy = project_field_plane_any(state.field_state.energy)
    entropy = project_field_plane_any(state.field_state.entropy)
    internal_time = project_field_plane_any(state.field_state.internal_time)
    energy_np = _to_numpy(energy)

    signature = digest_fields_any(energy, entropy, internal_time)
    summaries = FieldSummaries(
        energy=describe_field_any(energy),
        entropy=describe_field_any(entropy),
        internal_time=describe_field_any(internal_time),
    )

    attractors = []
    if str(config.observables_mode).strip().lower() == "cpu_full":
        attractors = detect_attractors(energy_np)

    cost = {
        "cpu_time_ms": float(elapsed_s) * 1000.0,
        "step_ops_estimate": float(_to_numpy(full_energy).size * max(1, int(n_ticks))),
        "memory_bytes_estimate": _estimate_array_bytes(full_energy)
        + _estimate_array_bytes(full_entropy)
        + _estimate_array_bytes(full_internal_time),
    }
    quality = _apply_quality_proxies(signature.vector)

    events: list[dict[str, object]] = []
    if refinement_event is not None:
        if isinstance(refinement_event, list):
            events.extend(dict(event) for event in refinement_event)
        else:
            events.append(dict(refinement_event))
    events.extend(
        [
            {
                "type": "attractor",
                "position": attr.position,
                "strength": attr.strength,
                "stability_score": attr.stability_score,
                "period_estimate": attr.period_estimate,
            }
            for attr in attractors
        ]
    )
    if influence_application is not None:
        events.append({"type": "influence", **influence_application.__dict__})

    return Observables(
        signature=signature,
        field_summaries=summaries,
        events=events,
        cost=cost,
        quality=quality,
    )


__all__ = [
    "build_observables",
    "ensure_refinement_runtime_memory",
    "is_override_only_influence",
    "maybe_refinement_event",
]
