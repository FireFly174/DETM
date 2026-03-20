from __future__ import annotations

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.refinement.pipeline.correction import apply_nonfinite_correction, apply_overflow_correction
from detm.runtime.refinement.pipeline.detect import detect_refinement_context
from detm.runtime.refinement.pipeline.metrics import build_nonfinite_event, build_overflow_event
from detm.runtime.refinement.pipeline.roi import detect_nonfinite_roi, detect_overflow_roi
from detm.runtime.state import DETMFieldState


def _make_field_state(energy: np.ndarray, *, entropy: np.ndarray | None = None) -> DETMFieldState:
    energy_np = np.asarray(energy, dtype=float)
    h, w = int(energy_np.shape[-2]), int(energy_np.shape[-1])
    lattice = Lattice(width=w, height=h, boundary="periodic")
    if entropy is None:
        clean = np.nan_to_num(energy_np, nan=0.0, posinf=1.0, neginf=0.0)
        if clean.ndim == 2:
            entropy_np = NumpyBackend._compute_entropy(
                clean,
                DynamicsParameters(energy_bounds=None),
                boundary=lattice.boundary,
            )
        else:
            flat = clean.reshape(-1, h, w)
            entropy_np = np.stack(
                [
                    NumpyBackend._compute_entropy(
                        plane,
                        DynamicsParameters(energy_bounds=None),
                        boundary=lattice.boundary,
                    )
                    for plane in flat
                ],
                axis=0,
            ).reshape(clean.shape)
    else:
        entropy_np = np.asarray(entropy, dtype=float)
    return DETMFieldState(
        lattice=lattice,
        energy=energy_np.copy(),
        entropy=entropy_np.copy(),
        internal_time=np.zeros(energy_np.shape, dtype=float),
    )


def _detect(state: DETMFieldState, *, runtime_memory: dict[str, object] | None = None):
    return detect_refinement_context(
        field_state=state,
        capacity_overflow_ratio_threshold=0.15,
        capacity_overflow_mean_threshold=0.5,
        capacity_min_signals=1,
        capacity_temporal_ratio_threshold=0.1,
        capacity_temporal_window=4,
        capacity_temporal_required_hits=3,
        capacity_learned_hits_threshold=0,
        capacity_cross_level_window=4,
        capacity_cross_level_min_levels=2,
        capacity_operator_score_threshold=1.0,
        capacity_cross_node_min_signals=1,
        capacity_distributed_accepted_min=0,
        capacity_signed_acks_min=0,
        capacity_consensus_accepted_min=0,
        capacity_crypto_validator_coverage_min=0.0,
        capacity_attestation_validator_ids=tuple(),
        capacity_attestation_min_coverage=0.0,
        capacity_byzantine_clean_min=0,
        active_level="L0",
        pattern_mode="minimal",
        runtime_memory=runtime_memory,
    )


def test_refinement_pipeline_detect_stage_reports_overflow_and_updates_history():
    energy = np.zeros((7, 7), dtype=float)
    energy[3, 3] = 2.0
    state = _make_field_state(energy)
    runtime_memory: dict[str, object] = {}

    context = _detect(state, runtime_memory=runtime_memory)

    assert int(context.overflow_count) == 1
    assert float(context.overflow_ratio) > 0.0
    assert isinstance(runtime_memory.get("capacity_temporal_history"), list)


def test_refinement_pipeline_detect_stage_projects_nd_field_state():
    energy = np.zeros((2, 7, 7), dtype=float)
    energy[-1, 3, 3] = 3.0
    state = _make_field_state(energy)

    context = _detect(state)

    assert context.energy.shape == (7, 7)
    assert int(context.overflow_count) == 1
    assert float(context.overflow_mean) > 0.0


def test_refinement_pipeline_roi_stage_detects_nonfinite_hotspot():
    energy = np.zeros((7, 7), dtype=float)
    entropy = np.zeros((7, 7), dtype=float)
    energy[3, 3] = np.nan
    state = _make_field_state(energy, entropy=entropy)
    context = _detect(state)

    nonfinite_roi = detect_nonfinite_roi(context)
    overflow_roi = detect_overflow_roi(context)

    assert nonfinite_roi is not None
    assert int(nonfinite_roi.area) > 0
    assert int(nonfinite_roi.nonfinite_total_count) >= 1
    assert overflow_roi is None


def test_refinement_pipeline_correction_and_metrics_for_overflow_path():
    energy = np.zeros((7, 7), dtype=float)
    energy[3, 3] = 2.0
    state = _make_field_state(energy)
    context = _detect(state)
    roi = detect_overflow_roi(context)
    assert roi is not None

    correction = apply_overflow_correction(
        field_state=state,
        dynamics=DynamicsParameters(energy_bounds=None),
        context=context,
        roi=roi,
        pattern_runtime=None,
        step_count=1,
    )

    assert correction is not None
    assert int(correction.overflow_count_after) < int(correction.overflow_count_before)
    event = build_overflow_event(
        context=context,
        roi=roi,
        correction=correction,
        pattern_runtime=None,
    )

    assert str(event.get("type")) == "refinement"
    assert "correction" in event
    assert np.isfinite(np.asarray(state.energy, dtype=float)).all()


def test_refinement_pipeline_correction_and_metrics_for_nonfinite_path():
    energy = np.zeros((7, 7), dtype=float)
    entropy = np.zeros((7, 7), dtype=float)
    energy[3, 3] = np.nan
    state = _make_field_state(energy, entropy=entropy)
    context = _detect(state)
    roi = detect_nonfinite_roi(context)
    assert roi is not None

    correction = apply_nonfinite_correction(
        field_state=state,
        dynamics=DynamicsParameters(energy_bounds=None),
        context=context,
        roi=roi,
    )
    event = build_nonfinite_event(context=context, roi=roi, correction=correction)

    assert str(event.get("detector")) == "state_nonfinite"
    assert int(dict(event.get("correction", {})).get("nonfinite_total_after", 1)) == 0
    assert np.isfinite(np.asarray(state.energy, dtype=float)).all()
