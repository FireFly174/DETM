"""Public refinement entrypoint for runtime step flow."""

from __future__ import annotations

from typing import Dict

from detm.core.entropy import DynamicsParameters
from detm.runtime.pattern_memory import PatternMemoryRuntime
from detm.runtime.refinement.pipeline import maybe_apply_refinement_pipeline
from detm.runtime.state import DETMFieldState

_DEFAULT_CAPACITY_OVERFLOW_RATIO_THRESHOLD = 0.15


def maybe_apply_refinement(
    *,
    field_state: DETMFieldState,
    dynamics: DynamicsParameters,
    allow_refinement: bool,
    capacity_overflow_ratio_threshold: float = _DEFAULT_CAPACITY_OVERFLOW_RATIO_THRESHOLD,
    capacity_overflow_mean_threshold: float = 0.5,
    capacity_min_signals: int = 1,
    capacity_temporal_ratio_threshold: float = 0.1,
    capacity_temporal_window: int = 4,
    capacity_temporal_required_hits: int = 3,
    capacity_learned_hits_threshold: int = 0,
    capacity_cross_level_window: int = 4,
    capacity_cross_level_min_levels: int = 2,
    capacity_operator_score_threshold: float = 1.0,
    capacity_cross_node_min_signals: int = 1,
    capacity_distributed_accepted_min: int = 0,
    capacity_signed_acks_min: int = 0,
    capacity_consensus_accepted_min: int = 0,
    capacity_crypto_validator_coverage_min: float = 0.0,
    capacity_attestation_validator_ids: tuple[str, ...] = tuple(),
    capacity_attestation_min_coverage: float = 0.0,
    capacity_byzantine_clean_min: int = 0,
    pattern_runtime: PatternMemoryRuntime | None = None,
    step_count: int = 0,
    active_level: str = "L0",
    pattern_mode: str = "minimal",
    runtime_memory: Dict[str, object] | None = None,
) -> Dict[str, object] | None:
    """Detect local overload and apply ROI correction in-place."""

    return maybe_apply_refinement_pipeline(
        field_state=field_state,
        dynamics=dynamics,
        allow_refinement=bool(allow_refinement),
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
        pattern_runtime=pattern_runtime,
        step_count=int(step_count),
        active_level=str(active_level),
        pattern_mode=str(pattern_mode),
        runtime_memory=runtime_memory,
    )


__all__ = ["maybe_apply_refinement"]
