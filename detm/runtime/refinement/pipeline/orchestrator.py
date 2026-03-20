"""Pipeline orchestrator for refinement runtime."""

from __future__ import annotations

import copy
from typing import Dict

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.pattern_memory import PatternMemoryRuntime
from detm.runtime.refinement.numpy_utils import apply_field_plane_state as _apply_field_plane_state
from detm.runtime.refinement.numpy_utils import to_numpy as _to_numpy
from detm.runtime.refinement.pipeline.correction import apply_nonfinite_correction, apply_overflow_correction
from detm.runtime.refinement.pipeline.detect import detect_refinement_context
from detm.runtime.refinement.pipeline.metrics import build_nonfinite_event, build_overflow_event
from detm.runtime.refinement.pipeline.roi import detect_nonfinite_roi, detect_overflow_roi
from detm.runtime.state import DETMFieldState


def _maybe_apply_refinement_single_plane(
    *,
    field_state: DETMFieldState,
    dynamics: DynamicsParameters,
    capacity_overflow_ratio_threshold: float,
    capacity_overflow_mean_threshold: float,
    capacity_saturation_band: float,
    capacity_min_signals: int,
    capacity_autoclamp_enabled: bool,
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
    operator_torsion_threshold: float,
    operator_torsion_guard_enabled: bool,
    operator_history_limit: int,
    pattern_runtime: PatternMemoryRuntime | None,
    step_count: int,
    active_level: str,
    pattern_mode: str,
    runtime_memory: Dict[str, object] | None,
) -> Dict[str, object] | None:
    context = detect_refinement_context(
        field_state=field_state,
        capacity_overflow_ratio_threshold=float(capacity_overflow_ratio_threshold),
        capacity_overflow_mean_threshold=float(capacity_overflow_mean_threshold),
        capacity_saturation_band=float(capacity_saturation_band),
        capacity_min_signals=int(capacity_min_signals),
        capacity_autoclamp_enabled=bool(capacity_autoclamp_enabled),
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
        torsion_threshold=float(operator_torsion_threshold),
        torsion_guard_enabled=bool(operator_torsion_guard_enabled),
        operator_history_limit=int(operator_history_limit),
        runtime_memory=runtime_memory,
    )
    if correction is None:
        return None

    return build_overflow_event(
        context=context,
        roi=overflow_roi,
        correction=correction,
        pattern_runtime=pattern_runtime,
    )


def maybe_apply_refinement_pipeline(
    *,
    field_state: DETMFieldState,
    dynamics: DynamicsParameters,
    allow_refinement: bool,
    capacity_overflow_ratio_threshold: float,
    capacity_overflow_mean_threshold: float,
    capacity_saturation_band: float,
    capacity_min_signals: int,
    capacity_autoclamp_enabled: bool,
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
    operator_torsion_threshold: float,
    operator_torsion_guard_enabled: bool,
    operator_history_limit: int,
    pattern_runtime: PatternMemoryRuntime | None,
    step_count: int,
    active_level: str,
    pattern_mode: str,
    runtime_memory: Dict[str, object] | None,
) -> Dict[str, object] | None:
    if not bool(allow_refinement):
        return None

    if len(field_state.shape) <= 2:
        return _maybe_apply_refinement_single_plane(
            field_state=field_state,
            dynamics=dynamics,
            capacity_overflow_ratio_threshold=float(capacity_overflow_ratio_threshold),
            capacity_overflow_mean_threshold=float(capacity_overflow_mean_threshold),
            capacity_saturation_band=float(capacity_saturation_band),
            capacity_min_signals=int(capacity_min_signals),
            capacity_autoclamp_enabled=bool(capacity_autoclamp_enabled),
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
            operator_torsion_threshold=float(operator_torsion_threshold),
            operator_torsion_guard_enabled=bool(operator_torsion_guard_enabled),
            operator_history_limit=int(operator_history_limit),
            pattern_runtime=pattern_runtime,
            step_count=int(step_count),
            active_level=str(active_level),
            pattern_mode=str(pattern_mode),
            runtime_memory=runtime_memory,
        )

    plane_shape = tuple(int(dim) for dim in field_state.shape[-2:])
    base_temporal_history = (
        list(runtime_memory.get("capacity_temporal_history", []))
        if isinstance(runtime_memory, dict) and isinstance(runtime_memory.get("capacity_temporal_history", []), list)
        else []
    )
    base_cross_level_history = (
        list(runtime_memory.get("capacity_cross_level_history", []))
        if isinstance(runtime_memory, dict) and isinstance(runtime_memory.get("capacity_cross_level_history", []), list)
        else []
    )
    base_operator_decision_history = (
        list(runtime_memory.get("operator_decision_history", []))
        if isinstance(runtime_memory, dict) and isinstance(runtime_memory.get("operator_decision_history", []), list)
        else []
    )
    parent_energy = _to_numpy(field_state.energy)
    parent_entropy = _to_numpy(field_state.entropy)
    parent_internal_time = _to_numpy(field_state.internal_time)
    events: list[Dict[str, object]] = []
    temporal_flags: list[bool] = []
    cross_level_flags: list[str] = []
    operator_scores: list[float] = []
    operator_last_decision: dict[str, object] | None = None
    operator_contract_last: dict[str, object] | None = None
    operator_history_rows: list[dict[str, object]] = []
    for plane_index in np.ndindex(*tuple(int(dim) for dim in field_state.shape[:-2])):
        plane_state = DETMFieldState(
            lattice=field_state.lattice,
            energy=np.asarray(parent_energy[plane_index], dtype=float).copy(),
            entropy=np.asarray(parent_entropy[plane_index], dtype=float).copy(),
            internal_time=np.asarray(parent_internal_time[plane_index], dtype=float).copy(),
            shape=plane_shape,
        )
        plane_runtime_memory = copy.deepcopy(runtime_memory) if isinstance(runtime_memory, dict) else None
        event = _maybe_apply_refinement_single_plane(
            field_state=plane_state,
            dynamics=dynamics,
            capacity_overflow_ratio_threshold=float(capacity_overflow_ratio_threshold),
            capacity_overflow_mean_threshold=float(capacity_overflow_mean_threshold),
            capacity_saturation_band=float(capacity_saturation_band),
            capacity_min_signals=int(capacity_min_signals),
            capacity_autoclamp_enabled=bool(capacity_autoclamp_enabled),
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
            operator_torsion_threshold=float(operator_torsion_threshold),
            operator_torsion_guard_enabled=bool(operator_torsion_guard_enabled),
            operator_history_limit=int(operator_history_limit),
            pattern_runtime=pattern_runtime,
            step_count=int(step_count),
            active_level=str(active_level),
            pattern_mode=str(pattern_mode),
            runtime_memory=plane_runtime_memory,
        )
        if isinstance(plane_runtime_memory, dict):
            plane_temporal_history = plane_runtime_memory.get("capacity_temporal_history", [])
            if isinstance(plane_temporal_history, list) and len(plane_temporal_history) > 0:
                temporal_flags.append(bool(plane_temporal_history[-1]))
            plane_cross_level_history = plane_runtime_memory.get("capacity_cross_level_history", [])
            if isinstance(plane_cross_level_history, list) and len(plane_cross_level_history) > 0:
                cross_level_flags.append(str(plane_cross_level_history[-1]))
            try:
                operator_scores.append(float(plane_runtime_memory.get("operator_capacity_signal_score", 0.0)))
            except (TypeError, ValueError):
                pass
            if isinstance(plane_runtime_memory.get("operator_last_decision"), dict):
                operator_last_decision = dict(plane_runtime_memory.get("operator_last_decision", {}))
            if isinstance(plane_runtime_memory.get("operator_contract_last"), dict):
                operator_contract_last = dict(plane_runtime_memory.get("operator_contract_last", {}))
            plane_operator_history = plane_runtime_memory.get("operator_decision_history", [])
            if isinstance(plane_operator_history, list) and len(plane_operator_history) > len(base_operator_decision_history):
                operator_history_rows.extend(
                    dict(row) for row in plane_operator_history[len(base_operator_decision_history) :] if isinstance(row, dict)
                )
        if event is None:
            continue
        _apply_field_plane_state(
            field_state,
            plane_index=tuple(int(v) for v in plane_index),
            energy_np=np.asarray(_to_numpy(plane_state.energy), dtype=float),
            entropy_np=np.asarray(_to_numpy(plane_state.entropy), dtype=float),
            internal_time_np=np.asarray(_to_numpy(plane_state.internal_time), dtype=float),
        )
        plane_event = dict(event)
        plane_event["plane_index"] = [int(v) for v in plane_index]
        events.append(plane_event)

    if len(events) == 0:
        return None
    if isinstance(runtime_memory, dict):
        temporal_history = list(base_temporal_history)
        temporal_history.append(any(bool(flag) for flag in temporal_flags))
        if len(temporal_history) > int(max(1, capacity_temporal_window)):
            temporal_history = temporal_history[-int(max(1, capacity_temporal_window)) :]
        runtime_memory["capacity_temporal_history"] = temporal_history

        cross_level_history = list(base_cross_level_history)
        cross_level_history.append(
            str(active_level) if any(bool(str(flag).strip()) for flag in cross_level_flags) else ""
        )
        if len(cross_level_history) > int(max(1, capacity_cross_level_window)):
            cross_level_history = cross_level_history[-int(max(1, capacity_cross_level_window)) :]
        runtime_memory["capacity_cross_level_history"] = cross_level_history

        if len(operator_scores) > 0:
            runtime_memory["operator_capacity_signal_score"] = float(max(operator_scores))
        if operator_last_decision is not None:
            runtime_memory["operator_last_decision"] = dict(operator_last_decision)
        if operator_contract_last is not None:
            runtime_memory["operator_contract_last"] = dict(operator_contract_last)
        if len(operator_history_rows) > 0:
            merged_operator_history = list(base_operator_decision_history) + list(operator_history_rows)
            history_limit = int(max(1, operator_history_limit))
            if len(merged_operator_history) > history_limit:
                merged_operator_history = merged_operator_history[-history_limit:]
            runtime_memory["operator_decision_history"] = merged_operator_history
    return events


__all__ = ["maybe_apply_refinement_pipeline"]
