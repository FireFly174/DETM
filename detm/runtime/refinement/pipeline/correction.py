"""Correction stage for refinement pipeline."""

from __future__ import annotations

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.pattern_memory import PatternMemoryRuntime
from detm.runtime.refinement.correction import select_correction as _select_correction
from detm.runtime.refinement.numpy_utils import apply_field_state as _apply_field_state
from detm.runtime.refinement.pipeline.contracts import (
    DetectionContext,
    NonfiniteCorrectionResult,
    NonfiniteRoiSelection,
    OverflowCorrectionResult,
    RoiSelection,
)
from detm.runtime.refinement.pipeline.operator_contract import assess_discrete_torsion
from detm.runtime.state import DETMFieldState


def apply_nonfinite_correction(
    *,
    field_state: DETMFieldState,
    dynamics: DynamicsParameters,
    context: DetectionContext,
    roi: NonfiniteRoiSelection,
) -> NonfiniteCorrectionResult:
    energy_sanitized = np.nan_to_num(
        np.asarray(context.energy, dtype=float),
        nan=0.5 * (float(context.lo) + float(context.hi)),
        posinf=float(context.hi),
        neginf=float(context.lo),
    )
    energy_sanitized = np.clip(energy_sanitized, float(context.lo), float(context.hi))
    entropy_sanitized = NumpyBackend._compute_entropy(energy_sanitized, dynamics, boundary=context.boundary)
    tau_sanitized = np.nan_to_num(np.asarray(context.internal_time, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)

    _apply_field_state(
        field_state,
        energy_np=energy_sanitized,
        entropy_np=entropy_sanitized,
        internal_time_np=tau_sanitized,
    )

    energy_reference = np.nan_to_num(
        np.asarray(context.energy, dtype=float),
        nan=0.5 * (float(context.lo) + float(context.hi)),
        posinf=float(context.hi),
        neginf=float(context.lo),
    )
    energy_l2_delta = float(np.sqrt(np.mean((energy_sanitized - energy_reference) ** 2)))
    nonfinite_after = int((~np.isfinite(energy_sanitized)).sum()) + int((~np.isfinite(entropy_sanitized)).sum()) + int(
        (~np.isfinite(tau_sanitized)).sum()
    )

    return NonfiniteCorrectionResult(
        energy_l2_delta=float(energy_l2_delta),
        nonfinite_total_before=int(roi.nonfinite_total_count),
        nonfinite_total_after=int(nonfinite_after),
    )


def apply_overflow_correction(
    *,
    field_state: DETMFieldState,
    dynamics: DynamicsParameters,
    context: DetectionContext,
    roi: RoiSelection,
    pattern_runtime: PatternMemoryRuntime | None,
    step_count: int,
    torsion_threshold: float = 1.0,
    torsion_guard_enabled: bool = True,
    operator_history_limit: int = 256,
    runtime_memory: dict[str, object] | None = None,
) -> OverflowCorrectionResult | None:
    energy_before = np.asarray(context.energy, dtype=float, copy=True)
    entropy_before = np.asarray(context.entropy, dtype=float, copy=True)

    pattern_key = None
    reused = False
    reused_record_hits = 0
    selection_rule = "torsion_guard_v1"
    selection_reason = "search_fallback"
    learned_hits = 0
    learned_hits_threshold = int(context.learned_hits_threshold)
    capacity_signal_learned = False
    correction = None
    if pattern_runtime is not None:
        pattern_key = pattern_runtime.make_key(
            energy=energy_before,
            center_x=int(roi.center_x),
            center_y=int(roi.center_y),
            radius=int(roi.radius),
            boundary=context.boundary,
        )
        if bool(pattern_runtime.reuse_enabled):
            reuse_blocked_by_torsion = False
            if runtime_memory is not None and isinstance(runtime_memory.get("operator_contract_last"), dict):
                prev_contract = dict(runtime_memory.get("operator_contract_last", {}))
                same_scope = bool(
                    str(prev_contract.get("level", "")) == str(context.active_level_name)
                    and str(prev_contract.get("mode", "")) == str(context.pattern_mode_name)
                )
                reuse_blocked_by_torsion = bool(
                    bool(torsion_guard_enabled) and same_scope and bool(prev_contract.get("torsion_flag"))
                )
            record = pattern_runtime.lookup_with_scope(
                key=str(pattern_key),
                step_count=int(step_count),
                level=context.active_level_name,
                mode=context.pattern_mode_name,
            )
            if record is not None and not reuse_blocked_by_torsion:
                correction = _select_correction(
                    energy_before=energy_before,
                    entropy_before=entropy_before,
                    mask=roi.mask,
                    boundary=context.boundary,
                    dynamics=dynamics,
                    lo=float(context.lo),
                    hi=float(context.hi),
                    blend_candidates=(float(record.blend),),
                )
                if correction is not None:
                    reused = True
                    reused_record_hits = int(record.hits)
                    learned_hits = int(reused_record_hits)
                    capacity_signal_learned = bool(
                        learned_hits_threshold > 0 and learned_hits >= learned_hits_threshold
                    )
                    selection_reason = "reuse_candidate"
            elif record is not None and reuse_blocked_by_torsion:
                selection_reason = "torsion_guard_blocked"
            else:
                selection_reason = "no_reuse_candidate"

    if correction is None:
        correction = _select_correction(
            energy_before=energy_before,
            entropy_before=entropy_before,
            mask=roi.mask,
            boundary=context.boundary,
            dynamics=dynamics,
            lo=float(context.lo),
            hi=float(context.hi),
            blend_candidates=(0.5, 0.75, 1.0),
        )

    if correction is None and float(context.capacity_saturation_band) > 0.0:
        # Fallback for clamped regimes: nudge ROI toward midpoint to release
        # soft-cap pressure when neighbour smoothing yields no strict gain.
        candidate = np.asarray(energy_before, dtype=float, copy=True)
        midpoint = 0.5 * (float(context.lo) + float(context.hi))
        candidate[roi.mask] = np.clip(
            0.75 * energy_before[roi.mask] + 0.25 * midpoint,
            float(context.lo),
            float(context.hi),
        )
        candidate_entropy = NumpyBackend._compute_entropy(candidate, dynamics, boundary=context.boundary)
        pressure_before_roi = int((np.asarray(context.overflow_score, dtype=float)[roi.mask] > 0.0).sum())
        correction = {
            "blend": 0.25,
            "energy": candidate,
            "entropy": candidate_entropy,
            "entropy_before_roi": float(entropy_before[roi.mask].mean()),
            "entropy_after_roi": float(candidate_entropy[roi.mask].mean()),
            "overflow_before_roi": int(pressure_before_roi),
            "overflow_after_roi": int(
                (
                    np.maximum(
                        np.maximum(float(context.lo) - candidate, 0.0),
                        np.maximum(candidate - float(context.hi), 0.0),
                    )[roi.mask]
                    > 0.0
                ).sum()
            ),
        }

    if correction is None:
        return None

    corrected_energy = np.asarray(correction["energy"], dtype=float)
    corrected_entropy = np.asarray(correction["entropy"], dtype=float)
    _apply_field_state(field_state, energy_np=corrected_energy, entropy_np=corrected_entropy)

    energy_l2_delta = float(np.sqrt(np.mean((corrected_energy - energy_before) ** 2)))
    entropy_before_roi = float(correction["entropy_before_roi"])
    entropy_after_roi = float(correction["entropy_after_roi"])
    entropy_delta = float(entropy_after_roi - entropy_before_roi)

    if pattern_runtime is not None and pattern_key is not None:
        error = max(0.0, float(entropy_delta))
        remembered = pattern_runtime.remember(
            key=str(pattern_key),
            blend=float(correction["blend"]),
            error=float(error),
            deviation=float(energy_l2_delta),
            step_count=int(step_count),
            base_hits=int(reused_record_hits if reused else 0),
            level=context.active_level_name,
            mode=context.pattern_mode_name,
        )
    else:
        remembered = None

    operator_hits_before = int(reused_record_hits if reused else 0)
    operator_hits_after = (
        int(remembered.hits)
        if remembered is not None
        else max(1, int(operator_hits_before) + 1)
    )
    operator_score = float(max(0, int(operator_hits_after) - 1))
    operator_id = str(pattern_key) if pattern_key is not None else f"overflow_blend:{float(correction['blend']):.3f}"
    operator_source = "reuse" if bool(reused) else "search"
    if bool(reused):
        selection_reason = "reuse_candidate"
    elif selection_reason == "search_fallback":
        selection_reason = "search_selected"
    previous_contract = None
    if runtime_memory is not None and isinstance(runtime_memory.get("operator_contract_last"), dict):
        previous_contract = dict(runtime_memory.get("operator_contract_last", {}))
    contract = assess_discrete_torsion(
        previous_decision=previous_contract,
        active_level=str(context.active_level_name),
        pattern_mode=str(context.pattern_mode_name),
        operator_source=str(operator_source),
        operator_hits_before=int(operator_hits_before),
        overflow_count_before=int(correction["overflow_before_roi"]),
        overflow_count_after=int(correction["overflow_after_roi"]),
        entropy_delta=float(entropy_delta),
        energy_l2_delta=float(energy_l2_delta),
        torsion_threshold=float(torsion_threshold),
    )

    if runtime_memory is not None:
        runtime_memory["operator_capacity_signal_score"] = float(operator_score)
        runtime_memory["operator_last_decision"] = {
            "id": str(operator_id),
            "source": str(operator_source),
            "selection_rule": str(selection_rule),
            "selection_reason": str(selection_reason),
            "hits_before": int(operator_hits_before),
            "hits_after": int(operator_hits_after),
            "score": float(operator_score),
        }
        runtime_memory["operator_contract_last"] = {
            "id": str(operator_id),
            "source": str(operator_source),
            "level": str(context.active_level_name),
            "mode": str(context.pattern_mode_name),
            "hits_after": int(operator_hits_after),
            "overflow_count_before": int(correction["overflow_before_roi"]),
            "overflow_count_after": int(correction["overflow_after_roi"]),
            "entropy_delta": float(entropy_delta),
            "energy_l2_delta": float(energy_l2_delta),
            "commutator_proxy": float(contract.commutator_proxy),
            "torsion_score": float(contract.torsion_score),
            "torsion_threshold": float(contract.torsion_threshold),
            "torsion_flag": bool(contract.torsion_flag),
            "compatible": bool(contract.compatible),
            "scope_changed": bool(contract.scope_changed),
        }
        history = runtime_memory.get("operator_decision_history", [])
        history_rows = list(history) if isinstance(history, list) else []
        history_rows.append(
            {
                "id": str(operator_id),
                "source": str(operator_source),
                "selection_rule": str(selection_rule),
                "selection_reason": str(selection_reason),
                "level": str(context.active_level_name),
                "mode": str(context.pattern_mode_name),
                "hits_after": int(operator_hits_after),
                "score": float(operator_score),
                "torsion_flag": bool(contract.torsion_flag),
                "torsion_score": float(contract.torsion_score),
            }
        )
        history_limit = max(1, int(operator_history_limit))
        if len(history_rows) > history_limit:
            history_rows = history_rows[-history_limit:]
        runtime_memory["operator_decision_history"] = history_rows

    return OverflowCorrectionResult(
        blend=float(correction["blend"]),
        entropy_before_roi=float(entropy_before_roi),
        entropy_after_roi=float(entropy_after_roi),
        entropy_delta=float(entropy_delta),
        energy_l2_delta=float(energy_l2_delta),
        overflow_count_before=int(correction["overflow_before_roi"]),
        overflow_count_after=int(correction["overflow_after_roi"]),
        pattern_key=None if pattern_key is None else str(pattern_key),
        operator_id=str(operator_id),
        operator_source=str(operator_source),
        operator_hits_before=int(operator_hits_before),
        operator_hits_after=int(operator_hits_after),
        operator_score=float(operator_score),
        operator_commutator_proxy=float(contract.commutator_proxy),
        operator_torsion_score=float(contract.torsion_score),
        operator_torsion_threshold=float(contract.torsion_threshold),
        operator_torsion_flag=bool(contract.torsion_flag),
        operator_contract_compatible=bool(contract.compatible),
        operator_scope_changed=bool(contract.scope_changed),
        operator_selection_rule=str(selection_rule),
        operator_selection_reason=str(selection_reason),
        reused=bool(reused),
        learned_hits=int(learned_hits),
        learned_hits_threshold=int(learned_hits_threshold),
        capacity_signal_learned=bool(capacity_signal_learned),
        remembered_hits=None if remembered is None else int(remembered.hits),
    )


__all__ = ["apply_nonfinite_correction", "apply_overflow_correction"]
