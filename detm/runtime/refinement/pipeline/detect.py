"""Detect stage for refinement pipeline."""

from __future__ import annotations

from typing import Dict

import numpy as np

from detm.runtime.signature import project_field_plane_any
from detm.runtime.refinement.numpy_utils import to_numpy as _to_numpy
from detm.runtime.refinement.pipeline.contracts import DetectionContext
from detm.runtime.state import DETMFieldState


def detect_refinement_context(
    *,
    field_state: DETMFieldState,
    capacity_overflow_ratio_threshold: float,
    capacity_overflow_mean_threshold: float,
    capacity_saturation_band: float = 0.0,
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
    active_level: str,
    pattern_mode: str,
    runtime_memory: Dict[str, object] | None,
    capacity_autoclamp_enabled: bool = False,
) -> DetectionContext:
    lattice = field_state.lattice
    boundary = str(lattice.boundary)
    energy = _to_numpy(project_field_plane_any(field_state.energy)).astype(float, copy=False)
    entropy = _to_numpy(project_field_plane_any(field_state.entropy)).astype(float, copy=False)
    internal_time = _to_numpy(project_field_plane_any(field_state.internal_time)).astype(float, copy=False)

    lo, hi = (0.0, 1.0)
    overflow_score = np.maximum(np.maximum(float(lo) - energy, 0.0), np.maximum(energy - float(hi), 0.0))
    overflow = overflow_score > 0.0
    saturation_band = max(0.0, float(capacity_saturation_band))
    if saturation_band > 0.0:
        # Soft-cap pressure enables refinement under clamped dynamics where hard
        # overflow may remain zero but field mass accumulates near bounds.
        distance_to_bound = np.minimum(energy - float(lo), float(hi) - energy)
        saturation_score = np.maximum(0.0, saturation_band - distance_to_bound) / float(saturation_band)
        saturation_score = np.where(np.isfinite(saturation_score), saturation_score, 0.0)
        overflow_score = np.maximum(overflow_score, saturation_score)
        overflow = overflow | (saturation_score > 0.0)
    overflow_count = int(overflow.sum())
    overflow_ratio = float(overflow_count) / float(max(1, lattice.height * lattice.width))
    overflow_mean = float(overflow_score[overflow].mean()) if overflow_count > 0 else 0.0

    capacity_ratio_threshold = max(0.0, float(capacity_overflow_ratio_threshold))
    capacity_mean_threshold = max(0.0, float(capacity_overflow_mean_threshold))
    capacity_min_signals_value = max(1, int(capacity_min_signals))
    capacity_autoclamp_enabled_value = bool(capacity_autoclamp_enabled)
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

    return DetectionContext(
        boundary=boundary,
        energy=energy,
        entropy=entropy,
        internal_time=internal_time,
        lo=float(lo),
        hi=float(hi),
        overflow_count=int(overflow_count),
        overflow_ratio=float(overflow_ratio),
        overflow_mean=float(overflow_mean),
        overflow_score=overflow_score,
        capacity_ratio_threshold=float(capacity_ratio_threshold),
        capacity_mean_threshold=float(capacity_mean_threshold),
        capacity_saturation_band=float(saturation_band),
        capacity_min_signals=int(capacity_min_signals_value),
        capacity_autoclamp_enabled=bool(capacity_autoclamp_enabled_value),
        temporal_ratio_threshold=float(temporal_ratio_threshold),
        temporal_window=int(temporal_window),
        temporal_required_hits=int(temporal_required_hits),
        temporal_hits=int(temporal_hits),
        temporal_history_len=int(temporal_history_len),
        temporal_signal=bool(temporal_signal),
        learned_hits_threshold=max(0, int(capacity_learned_hits_threshold)),
        cross_level_window=int(cross_level_window),
        cross_level_min_levels=int(cross_level_min_levels),
        cross_level_unique=list(cross_level_unique),
        cross_level_unique_count=int(cross_level_unique_count),
        cross_level_signal=bool(cross_level_signal),
        operator_score_threshold=float(operator_score_threshold),
        operator_score=float(operator_score),
        operator_signal=bool(operator_signal),
        cross_node_min_signals=int(cross_node_min_signals),
        cross_node_hits=int(cross_node_hits),
        cross_node_signal=bool(cross_node_signal),
        cross_node_replay_failed=bool(cross_node_replay_failed),
        cross_node_delivery_rejected=bool(cross_node_delivery_rejected),
        cross_node_delivery_pending=bool(cross_node_delivery_pending),
        distributed_accepted_min=int(distributed_accepted_min),
        distributed_accepted=int(distributed_accepted),
        distributed_signal=bool(distributed_signal),
        signed_acks_min=int(signed_acks_min),
        signed_acks=int(signed_acks),
        signed_signal=bool(signed_signal),
        consensus_accepted_min=int(consensus_accepted_min),
        consensus_pending=int(consensus_pending),
        consensus_rejected=int(consensus_rejected),
        consensus_signal=bool(consensus_signal),
        crypto_validator_coverage_min=float(crypto_validator_coverage_min),
        crypto_validator_coverage=float(crypto_validator_coverage),
        cryptographic_signal=bool(cryptographic_signal),
        attestation_min_coverage=float(attestation_min_coverage),
        attestation_coverage=float(attestation_coverage),
        attestation_required_ids=list(attestation_required_ids),
        attestation_signal=bool(attestation_signal),
        byzantine_clean_min=int(byzantine_clean_min),
        byzantine_signal=bool(byzantine_signal),
        active_level_name=active_level_name,
        pattern_mode_name=pattern_mode_name,
    )


__all__ = ["detect_refinement_context"]
