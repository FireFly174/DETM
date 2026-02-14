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
) -> OverflowCorrectionResult | None:
    energy_before = np.asarray(context.energy, dtype=float, copy=True)
    entropy_before = np.asarray(context.entropy, dtype=float, copy=True)

    pattern_key = None
    reused = False
    reused_record_hits = 0
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
            record = pattern_runtime.lookup_with_scope(
                key=str(pattern_key),
                step_count=int(step_count),
                level=context.active_level_name,
                mode=context.pattern_mode_name,
            )
            if record is not None:
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

    return OverflowCorrectionResult(
        blend=float(correction["blend"]),
        entropy_before_roi=float(entropy_before_roi),
        entropy_after_roi=float(entropy_after_roi),
        entropy_delta=float(entropy_delta),
        energy_l2_delta=float(energy_l2_delta),
        overflow_count_before=int(correction["overflow_before_roi"]),
        overflow_count_after=int(correction["overflow_after_roi"]),
        pattern_key=None if pattern_key is None else str(pattern_key),
        reused=bool(reused),
        learned_hits=int(learned_hits),
        learned_hits_threshold=int(learned_hits_threshold),
        capacity_signal_learned=bool(capacity_signal_learned),
        remembered_hits=None if remembered is None else int(remembered.hits),
    )


__all__ = ["apply_nonfinite_correction", "apply_overflow_correction"]
