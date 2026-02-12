"""Refinement MVP: overflow detector + ROI correction + pattern reuse."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.pattern_memory import PatternMemoryRuntime
from detm.runtime.state import DETMFieldState

_DEFAULT_CAPACITY_OVERFLOW_RATIO_THRESHOLD = 0.15


def _to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def _is_torch_tensor(array: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(array, torch.Tensor)


def _roi_mask(shape: tuple[int, int], *, center_y: int, center_x: int, radius: int, boundary: str) -> np.ndarray:
    h, w = int(shape[0]), int(shape[1])
    yy = np.arange(h, dtype=np.int32).reshape(h, 1)
    xx = np.arange(w, dtype=np.int32).reshape(1, w)
    if str(boundary) == "periodic":
        dy = np.minimum((yy - center_y) % h, (center_y - yy) % h)
        dx = np.minimum((xx - center_x) % w, (center_x - xx) % w)
    else:
        dy = np.abs(yy - center_y)
        dx = np.abs(xx - center_x)
    return (dy * dy + dx * dx) <= int(radius) * int(radius)


def _neighbor_average(energy: np.ndarray, *, boundary: str) -> np.ndarray:
    if str(boundary) == "periodic":
        return (
            np.roll(energy, shift=1, axis=0)
            + np.roll(energy, shift=-1, axis=0)
            + np.roll(energy, shift=1, axis=1)
            + np.roll(energy, shift=-1, axis=1)
        ) / 4.0
    padded = np.pad(energy, ((1, 1), (1, 1)), mode="edge")
    up = padded[:-2, 1:-1]
    down = padded[2:, 1:-1]
    left = padded[1:-1, :-2]
    right = padded[1:-1, 2:]
    return (up + down + left + right) / 4.0


def _apply_field_state(
    field_state: DETMFieldState,
    *,
    energy_np: np.ndarray,
    entropy_np: np.ndarray,
    internal_time_np: np.ndarray | None = None,
) -> None:
    if _is_torch_tensor(field_state.energy):
        import torch  # type: ignore

        energy_t = field_state.energy
        entropy_t = field_state.entropy
        tau_t = field_state.internal_time
        field_state.energy = torch.tensor(energy_np, device=energy_t.device, dtype=energy_t.dtype)
        field_state.entropy = torch.tensor(entropy_np, device=entropy_t.device, dtype=entropy_t.dtype)
        if internal_time_np is not None:
            field_state.internal_time = torch.tensor(internal_time_np, device=tau_t.device, dtype=tau_t.dtype)
        return
    field_state.energy = np.asarray(energy_np, dtype=float)
    field_state.entropy = np.asarray(entropy_np, dtype=float)
    if internal_time_np is not None:
        field_state.internal_time = np.asarray(internal_time_np, dtype=float)


def _candidate_score(
    *,
    candidate_energy: np.ndarray,
    candidate_entropy_roi: float,
    mask: np.ndarray,
    lo: float,
    hi: float,
) -> tuple[int, float]:
    overflow_after = (candidate_energy < float(lo)) | (candidate_energy > float(hi))
    overflow_count = int(overflow_after[mask].sum())
    return int(overflow_count), float(candidate_entropy_roi)


def _select_correction(
    *,
    energy_before: np.ndarray,
    entropy_before: np.ndarray,
    mask: np.ndarray,
    boundary: str,
    dynamics: DynamicsParameters,
    lo: float,
    hi: float,
    blend_candidates: tuple[float, ...],
) -> Dict[str, Any] | None:
    entropy_before_roi = float(entropy_before[mask].mean())
    overflow_before = int((((energy_before < lo) | (energy_before > hi))[mask]).sum())
    baseline_score = (overflow_before, float(entropy_before_roi))

    neighbor = _neighbor_average(energy_before, boundary=boundary)
    best: Dict[str, Any] | None = None
    for blend in blend_candidates:
        candidate = np.asarray(energy_before, dtype=float, copy=True)
        candidate[mask] = (1.0 - float(blend)) * energy_before[mask] + float(blend) * neighbor[mask]
        candidate[mask] = np.clip(candidate[mask], float(lo), float(hi))

        candidate_entropy = NumpyBackend._compute_entropy(candidate, dynamics, boundary=boundary)
        candidate_entropy_roi = float(candidate_entropy[mask].mean())
        score = _candidate_score(
            candidate_energy=candidate,
            candidate_entropy_roi=float(candidate_entropy_roi),
            mask=mask,
            lo=float(lo),
            hi=float(hi),
        )
        if score >= baseline_score:
            continue
        if best is None or score < best["score"]:
            best = {
                "blend": float(blend),
                "energy": candidate,
                "entropy": candidate_entropy,
                "entropy_roi": float(candidate_entropy_roi),
                "score": score,
            }

    if best is None:
        return None
    return {
        "blend": float(best["blend"]),
        "energy": best["energy"],
        "entropy": best["entropy"],
        "entropy_before_roi": float(entropy_before_roi),
        "entropy_after_roi": float(best["entropy_roi"]),
        "overflow_before_roi": int(baseline_score[0]),
        "overflow_after_roi": int(best["score"][0]),
    }


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
    """Detect local overload and run ROI correction in-place.

    MVP semantics:
    - detector: local energy overflow against canonical bounds E in [0,1]
    - local downgrade: circular ROI around hotspot
    - correction: neighbor-averaging blend with pattern reuse before search
    """

    if not bool(allow_refinement):
        return None

    lattice = field_state.lattice
    boundary = str(lattice.boundary)
    energy = _to_numpy(field_state.energy).astype(float, copy=False).reshape(lattice.height, lattice.width)
    entropy = _to_numpy(field_state.entropy).astype(float, copy=False).reshape(lattice.height, lattice.width)
    internal_time = _to_numpy(field_state.internal_time).astype(float, copy=False).reshape(lattice.height, lattice.width)

    lo, hi = (0.0, 1.0)
    overflow = (energy < float(lo)) | (energy > float(hi))
    overflow_count = int(overflow.sum())
    overflow_score = np.maximum(np.maximum(float(lo) - energy, 0.0), np.maximum(energy - float(hi), 0.0))
    overflow_ratio = float(overflow_count) / float(max(1, lattice.height * lattice.width))
    overflow_mean = float(overflow_score[overflow].mean()) if overflow_count > 0 else 0.0

    capacity_ratio_threshold = max(0.0, float(capacity_overflow_ratio_threshold))
    temporal_ratio_threshold = max(0.0, float(capacity_temporal_ratio_threshold))
    temporal_window = max(1, int(capacity_temporal_window))
    temporal_required_hits = max(1, int(capacity_temporal_required_hits))
    temporal_now = bool(overflow_ratio >= float(temporal_ratio_threshold))
    if runtime_memory is not None:
        history_raw = runtime_memory.get("capacity_temporal_history", [])
        history = [bool(v) for v in list(history_raw)] if isinstance(history_raw, (list, tuple)) else []
        history.append(bool(temporal_now))
        if len(history) > temporal_window:
            history = history[-temporal_window:]
        runtime_memory["capacity_temporal_history"] = list(history)
    else:
        history = [bool(temporal_now)]
    temporal_hits = int(sum(1 for flag in history if bool(flag)))
    temporal_history_len = int(len(history))
    temporal_signal = bool(temporal_hits >= temporal_required_hits)

    cross_level_window = max(1, int(capacity_cross_level_window))
    cross_level_min_levels = max(1, int(capacity_cross_level_min_levels))
    active_level_name = str(active_level or "").strip() or "L0"
    pattern_mode_name = str(pattern_mode or "").strip() or "minimal"
    cross_level_now = bool(overflow_ratio >= float(capacity_ratio_threshold))
    if runtime_memory is not None:
        cross_levels_raw = runtime_memory.get("capacity_cross_level_history", [])
        cross_levels = [str(v) for v in list(cross_levels_raw)] if isinstance(cross_levels_raw, (list, tuple)) else []
        cross_levels.append(active_level_name if cross_level_now else "")
        if len(cross_levels) > cross_level_window:
            cross_levels = cross_levels[-cross_level_window:]
        runtime_memory["capacity_cross_level_history"] = list(cross_levels)
    else:
        cross_levels = [active_level_name if cross_level_now else ""]
    cross_level_values = [level for level in cross_levels if str(level).strip()]
    cross_level_unique = sorted(set(cross_level_values))
    cross_level_unique_count = int(len(cross_level_unique))
    cross_level_signal = bool(cross_level_unique_count >= cross_level_min_levels)

    operator_score_threshold = max(0.0, float(capacity_operator_score_threshold))
    operator_score = 0.0
    if runtime_memory is not None:
        try:
            operator_score = float(runtime_memory.get("operator_capacity_signal_score", 0.0))
        except (TypeError, ValueError):
            operator_score = 0.0
    operator_signal = bool(operator_score >= operator_score_threshold)

    cross_node_min_signals = max(1, int(capacity_cross_node_min_signals))
    cross_node_replay_failed = False
    cross_node_delivery_rejected = False
    cross_node_delivery_pending = False
    if runtime_memory is not None and isinstance(runtime_memory.get("fabric_quorum_snapshot", None), dict):
        snapshot = dict(runtime_memory.get("fabric_quorum_snapshot", {}))
        replay_failed = snapshot.get("replay_checks_failed", snapshot.get("replay_failed", 0))
        try:
            cross_node_replay_failed = int(replay_failed) > 0
        except (TypeError, ValueError):
            cross_node_replay_failed = False

        delivery = snapshot.get("delivery_receipts")
        if isinstance(delivery, dict):
            rejected = delivery.get("rejected_count", 0)
            pending = delivery.get("pending_count", 0)
        else:
            rejected = snapshot.get("delivery_rejected_count", 0)
            pending = snapshot.get("delivery_pending_count", 0)
        try:
            cross_node_delivery_rejected = int(rejected) > 0
        except (TypeError, ValueError):
            cross_node_delivery_rejected = False
        try:
            cross_node_delivery_pending = int(pending) > 0
        except (TypeError, ValueError):
            cross_node_delivery_pending = False
    cross_node_hits = int(cross_node_replay_failed) + int(cross_node_delivery_rejected) + int(cross_node_delivery_pending)
    cross_node_signal = bool(cross_node_hits >= cross_node_min_signals)

    distributed_accepted_min = max(0, int(capacity_distributed_accepted_min))
    signed_acks_min = max(0, int(capacity_signed_acks_min))
    consensus_accepted_min = max(0, int(capacity_consensus_accepted_min))
    crypto_validator_coverage_min = max(0.0, float(capacity_crypto_validator_coverage_min))
    distributed_accepted = 0
    signed_acks = 0
    consensus_pending = 0
    consensus_rejected = 0
    crypto_validator_coverage = 0.0
    byzantine_clean_min = max(0, int(capacity_byzantine_clean_min))
    byzantine_signal = False
    attestation_min_coverage = max(0.0, float(capacity_attestation_min_coverage))
    attestation_coverage = 0.0
    attestation_required_ids = [str(v).strip() for v in tuple(capacity_attestation_validator_ids) if str(v).strip()]
    attestation_signal = False
    if runtime_memory is not None and isinstance(runtime_memory.get("fabric_quorum_snapshot", None), dict):
        snapshot = dict(runtime_memory.get("fabric_quorum_snapshot", {}))
        try:
            distributed_accepted = int(snapshot.get("accepted_count", 0))
        except (TypeError, ValueError):
            distributed_accepted = 0
        try:
            consensus_pending = int(snapshot.get("pending_count", 0))
        except (TypeError, ValueError):
            consensus_pending = 0
        try:
            consensus_rejected = int(snapshot.get("rejected_count", 0))
        except (TypeError, ValueError):
            consensus_rejected = 0
        registry = snapshot.get("validator_registry")
        validator_ids: list[str] = []
        if isinstance(registry, dict):
            validator_ids = [str(v).strip() for v in list(registry.get("validators", [])) if str(v).strip()]
        if not attestation_required_ids:
            attestation_required_ids = list(validator_ids)
        evaluations = snapshot.get("evaluations", [])
        attestation_proof_union: set[str] = set()
        attestation_trust_union: set[str] = set()
        if isinstance(evaluations, list):
            for row in list(evaluations):
                if not isinstance(row, dict):
                    continue
                proof = row.get("proof")
                trust = row.get("trust")
                proof_accepted = int(dict(proof).get("accepted", 0)) if isinstance(proof, dict) else 0
                trust_accepted = int(dict(trust).get("accepted", 0)) if isinstance(trust, dict) else 0
                signed_acks += max(0, proof_accepted) + max(0, trust_accepted)
                if validator_ids and str(row.get("status", "")).strip().lower() == "accepted":
                    proof_validators = (
                        [str(v).strip() for v in list(dict(proof).get("unique_accepted_validators", [])) if str(v).strip()]
                        if isinstance(proof, dict)
                        else []
                    )
                    trust_validators = (
                        [str(v).strip() for v in list(dict(trust).get("unique_accepted_validators", [])) if str(v).strip()]
                        if isinstance(trust, dict)
                        else []
                    )
                    denom = max(1, len(validator_ids))
                    proof_cov = float(len(set(proof_validators).intersection(set(validator_ids)))) / float(denom)
                    trust_cov = float(len(set(trust_validators).intersection(set(validator_ids)))) / float(denom)
                    row_cov = min(proof_cov, trust_cov)
                    if row_cov > crypto_validator_coverage:
                        crypto_validator_coverage = float(row_cov)
                if str(row.get("status", "")).strip().lower() == "accepted":
                    if isinstance(proof, dict):
                        attestation_proof_union.update(
                            str(v).strip()
                            for v in list(dict(proof).get("unique_accepted_validators", []))
                            if str(v).strip()
                        )
                    if isinstance(trust, dict):
                        attestation_trust_union.update(
                            str(v).strip()
                            for v in list(dict(trust).get("unique_accepted_validators", []))
                            if str(v).strip()
                        )
        if attestation_required_ids and attestation_min_coverage > 0.0:
            required = set(attestation_required_ids)
            denom = max(1, len(required))
            proof_cov = float(len(required.intersection(attestation_proof_union))) / float(denom)
            trust_cov = float(len(required.intersection(attestation_trust_union))) / float(denom)
            attestation_coverage = min(proof_cov, trust_cov)
            attestation_signal = bool(attestation_coverage >= attestation_min_coverage)
        byzantine_signal = bool(
            byzantine_clean_min > 0
            and distributed_accepted >= byzantine_clean_min
            and consensus_pending == 0
            and consensus_rejected == 0
            and not cross_node_replay_failed
            and not cross_node_delivery_rejected
        )
    distributed_signal = bool(distributed_accepted_min > 0 and distributed_accepted >= distributed_accepted_min)
    signed_signal = bool(signed_acks_min > 0 and signed_acks >= signed_acks_min)
    consensus_signal = bool(
        consensus_accepted_min > 0
        and distributed_accepted >= consensus_accepted_min
        and consensus_pending == 0
        and consensus_rejected == 0
    )
    cryptographic_signal = bool(
        crypto_validator_coverage_min > 0.0 and crypto_validator_coverage >= crypto_validator_coverage_min
    )

    if overflow_count <= 0:
        nonfinite_energy = ~np.isfinite(energy)
        nonfinite_entropy = ~np.isfinite(entropy)
        nonfinite_tau = ~np.isfinite(internal_time)
        nonfinite_total_mask = nonfinite_energy | nonfinite_entropy | nonfinite_tau
        nonfinite_count = int(nonfinite_total_mask.sum())
        if nonfinite_count <= 0:
            return None

        center_y, center_x = np.unravel_index(int(np.argmax(nonfinite_total_mask.astype(np.int32))), nonfinite_total_mask.shape)
        radius = min(3, 1 + int(np.sqrt(max(1, nonfinite_count)) // 2))
        mask = _roi_mask(
            entropy.shape,
            center_y=int(center_y),
            center_x=int(center_x),
            radius=int(radius),
            boundary=boundary,
        )
        area = int(mask.sum())
        if area <= 0:
            return None

        energy_sanitized = np.nan_to_num(np.asarray(energy, dtype=float), nan=0.5 * (float(lo) + float(hi)), posinf=float(hi), neginf=float(lo))
        energy_sanitized = np.clip(energy_sanitized, float(lo), float(hi))
        entropy_sanitized = NumpyBackend._compute_entropy(energy_sanitized, dynamics, boundary=boundary)
        tau_sanitized = np.nan_to_num(np.asarray(internal_time, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)

        _apply_field_state(
            field_state,
            energy_np=energy_sanitized,
            entropy_np=entropy_sanitized,
            internal_time_np=tau_sanitized,
        )

        energy_reference = np.nan_to_num(np.asarray(energy, dtype=float), nan=0.5 * (float(lo) + float(hi)), posinf=float(hi), neginf=float(lo))
        energy_l2_delta = float(np.sqrt(np.mean((energy_sanitized - energy_reference) ** 2)))
        nonfinite_after = int((~np.isfinite(energy_sanitized)).sum()) + int((~np.isfinite(entropy_sanitized)).sum()) + int(
            (~np.isfinite(tau_sanitized)).sum()
        )

        return {
            "type": "refinement",
            "detector": "state_nonfinite",
            "roi": {
                "center_x": int(center_x),
                "center_y": int(center_y),
                "radius": int(radius),
                "area": int(area),
                "boundary": boundary,
            },
            "detector_nonfinite_counts": {
                "energy": int(nonfinite_energy.sum()),
                "entropy": int(nonfinite_entropy.sum()),
                "internal_time": int(nonfinite_tau.sum()),
                "total": int(nonfinite_count),
            },
            "correction": {
                "mode": "sanitize_nonfinite",
                "energy_l2_delta": float(energy_l2_delta),
                "nonfinite_total_before": int(nonfinite_count),
                "nonfinite_total_after": int(nonfinite_after),
            },
        }

    center_y, center_x = np.unravel_index(int(np.argmax(overflow_score)), overflow_score.shape)
    radius = min(3, 1 + int(np.sqrt(max(1, overflow_count)) // 2))
    mask = _roi_mask(
        entropy.shape,
        center_y=int(center_y),
        center_x=int(center_x),
        radius=int(radius),
        boundary=boundary,
    )
    area = int(mask.sum())
    if area <= 0:
        return None

    energy_before = np.asarray(energy, dtype=float, copy=True)
    entropy_before = np.asarray(entropy, dtype=float, copy=True)

    pattern_key = None
    reused = False
    reused_record_hits = 0
    learned_hits_threshold = max(0, int(capacity_learned_hits_threshold))
    learned_hits = 0
    capacity_signal_learned = False
    correction = None
    if pattern_runtime is not None:
        pattern_key = pattern_runtime.make_key(
            energy=energy_before,
            center_x=int(center_x),
            center_y=int(center_y),
            radius=int(radius),
            boundary=boundary,
        )
        if bool(pattern_runtime.reuse_enabled):
            record = pattern_runtime.lookup_with_scope(
                key=str(pattern_key),
                step_count=int(step_count),
                level=active_level_name,
                mode=pattern_mode_name,
            )
            if record is not None:
                correction = _select_correction(
                    energy_before=energy_before,
                    entropy_before=entropy_before,
                    mask=mask,
                    boundary=boundary,
                    dynamics=dynamics,
                    lo=float(lo),
                    hi=float(hi),
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
            mask=mask,
            boundary=boundary,
            dynamics=dynamics,
            lo=float(lo),
            hi=float(hi),
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
            level=active_level_name,
            mode=pattern_mode_name,
        )
    else:
        remembered = None

    capacity_mean_threshold = max(0.0, float(capacity_overflow_mean_threshold))
    capacity_signal_ratio = bool(overflow_ratio >= float(capacity_ratio_threshold))
    capacity_signal_mean = bool(overflow_mean >= float(capacity_mean_threshold))
    secondary_required = max(0, int(max(1, int(capacity_min_signals)) - 1))
    secondary_hits = (
        int(1 if capacity_signal_mean else 0)
        + int(1 if temporal_signal else 0)
        + int(1 if capacity_signal_learned else 0)
        + int(1 if cross_level_signal else 0)
        + int(1 if operator_signal else 0)
        + int(1 if cross_node_signal else 0)
        + int(1 if distributed_signal else 0)
        + int(1 if signed_signal else 0)
        + int(1 if consensus_signal else 0)
        + int(1 if cryptographic_signal else 0)
        + int(1 if attestation_signal else 0)
        + int(1 if byzantine_signal else 0)
    )
    capacity_triggered = bool(capacity_signal_ratio and secondary_hits >= secondary_required)

    event: Dict[str, object] = {
        "type": "refinement",
        "detector": "capacity_pressure" if capacity_triggered else "energy_overflow",
        "roi": {
            "center_x": int(center_x),
            "center_y": int(center_y),
            "radius": int(radius),
            "area": int(area),
            "boundary": boundary,
        },
        "detector_overflow_count": int(overflow_count),
        "detector_overflow_ratio": float(overflow_ratio),
        "detector_capacity_ratio_threshold": float(capacity_ratio_threshold),
        "detector_overflow_mean": float(overflow_mean),
        "detector_capacity_mean_threshold": float(capacity_mean_threshold),
        "detector_capacity_min_signals": int(max(1, int(capacity_min_signals))),
        "detector_capacity_secondary_required": int(secondary_required),
        "detector_capacity_secondary_hits": int(secondary_hits),
        "detector_capacity_learned_hits_threshold": int(learned_hits_threshold),
        "detector_capacity_learned_hits": int(learned_hits),
        "detector_capacity_cross_level_window": int(cross_level_window),
        "detector_capacity_cross_level_min_levels": int(cross_level_min_levels),
        "detector_capacity_cross_level_unique_count": int(cross_level_unique_count),
        "detector_capacity_cross_level_levels": list(cross_level_unique),
        "detector_capacity_operator_score_threshold": float(operator_score_threshold),
        "detector_capacity_operator_score": float(operator_score),
        "detector_capacity_cross_node_min_signals": int(cross_node_min_signals),
        "detector_capacity_cross_node_hits": int(cross_node_hits),
        "detector_capacity_distributed_accepted_min": int(distributed_accepted_min),
        "detector_capacity_distributed_accepted": int(distributed_accepted),
        "detector_capacity_signed_acks_min": int(signed_acks_min),
        "detector_capacity_signed_acks": int(signed_acks),
        "detector_capacity_consensus_accepted_min": int(consensus_accepted_min),
        "detector_capacity_consensus_pending": int(consensus_pending),
        "detector_capacity_consensus_rejected": int(consensus_rejected),
        "detector_capacity_crypto_validator_coverage_min": float(crypto_validator_coverage_min),
        "detector_capacity_crypto_validator_coverage": float(crypto_validator_coverage),
        "detector_capacity_attestation_min_coverage": float(attestation_min_coverage),
        "detector_capacity_attestation_coverage": float(attestation_coverage),
        "detector_capacity_attestation_validator_ids": list(attestation_required_ids),
        "detector_capacity_byzantine_clean_min": int(byzantine_clean_min),
        "detector_capacity_triggered": bool(capacity_triggered),
        "detector_capacity_signals": {
            "overflow_ratio": {
                "value": float(overflow_ratio),
                "threshold": float(capacity_ratio_threshold),
                "passed": bool(capacity_signal_ratio),
            },
            "overflow_mean": {
                "value": float(overflow_mean),
                "threshold": float(capacity_mean_threshold),
                "passed": bool(capacity_signal_mean),
            },
            "temporal_sustained": {
                "value": int(temporal_hits),
                "threshold": int(temporal_required_hits),
                "window": int(temporal_window),
                "history_length": int(temporal_history_len),
                "ratio_threshold": float(temporal_ratio_threshold),
                "passed": bool(temporal_signal),
            },
            "learned_reuse": {
                "value": int(learned_hits),
                "threshold": int(learned_hits_threshold),
                "passed": bool(capacity_signal_learned),
                "reused": bool(reused),
            },
            "cross_level": {
                "value": int(cross_level_unique_count),
                "threshold": int(cross_level_min_levels),
                "window": int(cross_level_window),
                "levels": list(cross_level_unique),
                "passed": bool(cross_level_signal),
            },
            "operator_signal": {
                "value": float(operator_score),
                "threshold": float(operator_score_threshold),
                "passed": bool(operator_signal),
            },
            "cross_node": {
                "value": int(cross_node_hits),
                "threshold": int(cross_node_min_signals),
                "replay_failed": bool(cross_node_replay_failed),
                "delivery_rejected": bool(cross_node_delivery_rejected),
                "delivery_pending": bool(cross_node_delivery_pending),
                "passed": bool(cross_node_signal),
            },
            "distributed_quorum": {
                "value": int(distributed_accepted),
                "threshold": int(distributed_accepted_min),
                "passed": bool(distributed_signal),
            },
            "signed_ack_evidence": {
                "value": int(signed_acks),
                "threshold": int(signed_acks_min),
                "passed": bool(signed_signal),
            },
            "consensus_grade": {
                "value": int(distributed_accepted),
                "threshold": int(consensus_accepted_min),
                "pending_count": int(consensus_pending),
                "rejected_count": int(consensus_rejected),
                "passed": bool(consensus_signal),
            },
            "cryptographic_grade": {
                "value": float(crypto_validator_coverage),
                "threshold": float(crypto_validator_coverage_min),
                "passed": bool(cryptographic_signal),
            },
            "attestation_grade": {
                "value": float(attestation_coverage),
                "threshold": float(attestation_min_coverage),
                "validator_ids": list(attestation_required_ids),
                "passed": bool(attestation_signal),
            },
            "byzantine_grade": {
                "value": int(distributed_accepted),
                "threshold": int(byzantine_clean_min),
                "pending_count": int(consensus_pending),
                "rejected_count": int(consensus_rejected),
                "replay_failed": bool(cross_node_replay_failed),
                "delivery_rejected": bool(cross_node_delivery_rejected),
                "passed": bool(byzantine_signal),
            },
        },
        "detector_bounds": {"min": float(lo), "max": float(hi)},
        "correction": {
            "blend": float(correction["blend"]),
            "entropy_mean_before": float(entropy_before_roi),
            "entropy_mean_after": float(entropy_after_roi),
            "entropy_delta": float(entropy_delta),
            "energy_l2_delta": float(energy_l2_delta),
            "overflow_count_before": int(correction["overflow_before_roi"]),
            "overflow_count_after": int(correction["overflow_after_roi"]),
        },
    }

    if remembered is not None and pattern_key is not None:
        event["pattern"] = {
            "key": str(pattern_key),
            "reused": bool(reused),
            "hits": int(remembered.hits),
            "cache_size": int(pattern_runtime.cache_size()) if pattern_runtime is not None else 0,
        }

    return event


__all__ = ["maybe_apply_refinement"]
