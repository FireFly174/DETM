"""Pipeline orchestrator for refinement runtime."""

from __future__ import annotations

from typing import Dict

from detm.core.entropy import DynamicsParameters
from detm.runtime.pattern_memory import PatternMemoryRuntime
from detm.runtime.refinement.pipeline.correction import apply_nonfinite_correction, apply_overflow_correction
from detm.runtime.refinement.pipeline.detect import detect_refinement_context
from detm.runtime.refinement.pipeline.metrics import build_nonfinite_event, build_overflow_event
from detm.runtime.refinement.pipeline.roi import detect_nonfinite_roi, detect_overflow_roi
from detm.runtime.state import DETMFieldState


def maybe_apply_refinement_pipeline(
    *,
    field_state: DETMFieldState,
    dynamics: DynamicsParameters,
    allow_refinement: bool,
    capacity_overflow_ratio_threshold: float,
    capacity_overflow_mean_threshold: float,
    capacity_min_signals: int,
    capacity_temporal_ratio_threshold: float,
    capacity_temporal_window: int,
    capacity_temporal_required_hits: int,
    capacity_learned_hits_threshold: int,
    capacity_cross_level_window: int,
    capacity_cross_level_min_levels: int,
    capacity_operator_score_threshold: float,
    capacity_cross_node_min_signals: int,
    capacity_distributed_accepted_min: int,
    capacity_signed_acks_min: int,
    capacity_consensus_accepted_min: int,
    capacity_crypto_validator_coverage_min: float,
    capacity_attestation_validator_ids: tuple[str, ...],
    capacity_attestation_min_coverage: float,
    capacity_byzantine_clean_min: int,
    pattern_runtime: PatternMemoryRuntime | None,
    step_count: int,
    active_level: str,
    pattern_mode: str,
    runtime_memory: Dict[str, object] | None,
) -> Dict[str, object] | None:
    if not bool(allow_refinement):
        return None

    context = detect_refinement_context(
        field_state=field_state,
        capacity_overflow_ratio_threshold=float(capacity_overflow_ratio_threshold),
        capacity_overflow_mean_threshold=float(capacity_overflow_mean_threshold),
        capacity_min_signals=int(capacity_min_signals),
        capacity_temporal_ratio_threshold=float(capacity_temporal_ratio_threshold),
        capacity_temporal_window=int(capacity_temporal_window),
        capacity_temporal_required_hits=int(capacity_temporal_required_hits),
        capacity_learned_hits_threshold=int(capacity_learned_hits_threshold),
        capacity_cross_level_window=int(capacity_cross_level_window),
        capacity_cross_level_min_levels=int(capacity_cross_level_min_levels),
        capacity_operator_score_threshold=float(capacity_operator_score_threshold),
        capacity_cross_node_min_signals=int(capacity_cross_node_min_signals),
        capacity_distributed_accepted_min=int(capacity_distributed_accepted_min),
        capacity_signed_acks_min=int(capacity_signed_acks_min),
        capacity_consensus_accepted_min=int(capacity_consensus_accepted_min),
        capacity_crypto_validator_coverage_min=float(capacity_crypto_validator_coverage_min),
        capacity_attestation_validator_ids=tuple(capacity_attestation_validator_ids),
        capacity_attestation_min_coverage=float(capacity_attestation_min_coverage),
        capacity_byzantine_clean_min=int(capacity_byzantine_clean_min),
        active_level=str(active_level),
        pattern_mode=str(pattern_mode),
        runtime_memory=runtime_memory,
    )

    nonfinite_roi = detect_nonfinite_roi(context)
    if nonfinite_roi is not None:
        correction = apply_nonfinite_correction(
            field_state=field_state,
            dynamics=dynamics,
            context=context,
            roi=nonfinite_roi,
        )
        return build_nonfinite_event(context=context, roi=nonfinite_roi, correction=correction)

    overflow_roi = detect_overflow_roi(context)
    if overflow_roi is None:
        return None

    correction = apply_overflow_correction(
        field_state=field_state,
        dynamics=dynamics,
        context=context,
        roi=overflow_roi,
        pattern_runtime=pattern_runtime,
        step_count=int(step_count),
    )
    if correction is None:
        return None

    return build_overflow_event(
        context=context,
        roi=overflow_roi,
        correction=correction,
        pattern_runtime=pattern_runtime,
    )


__all__ = ["maybe_apply_refinement_pipeline"]
