"""Metrics/event stage for refinement pipeline."""

from __future__ import annotations

from typing import Dict

from detm.runtime.pattern_memory import PatternMemoryRuntime
from detm.runtime.refinement.pipeline.contracts import (
    DetectionContext,
    NonfiniteCorrectionResult,
    NonfiniteRoiSelection,
    OverflowCorrectionResult,
    RoiSelection,
)


def build_nonfinite_event(
    *,
    context: DetectionContext,
    roi: NonfiniteRoiSelection,
    correction: NonfiniteCorrectionResult,
) -> Dict[str, object]:
    return {
        "type": "refinement",
        "detector": "state_nonfinite",
        "roi": {
            "center_x": int(roi.center_x),
            "center_y": int(roi.center_y),
            "radius": int(roi.radius),
            "area": int(roi.area),
            "boundary": context.boundary,
        },
        "detector_nonfinite_counts": {
            "energy": int(roi.nonfinite_energy.sum()),
            "entropy": int(roi.nonfinite_entropy.sum()),
            "internal_time": int(roi.nonfinite_tau.sum()),
            "total": int(roi.nonfinite_total_count),
        },
        "correction": {
            "mode": "sanitize_nonfinite",
            "energy_l2_delta": float(correction.energy_l2_delta),
            "nonfinite_total_before": int(correction.nonfinite_total_before),
            "nonfinite_total_after": int(correction.nonfinite_total_after),
        },
    }


def build_overflow_event(
    *,
    context: DetectionContext,
    roi: RoiSelection,
    correction: OverflowCorrectionResult,
    pattern_runtime: PatternMemoryRuntime | None,
) -> Dict[str, object]:
    capacity_signal_ratio = bool(context.overflow_ratio >= float(context.capacity_ratio_threshold))
    capacity_signal_mean = bool(context.overflow_mean >= float(context.capacity_mean_threshold))
    secondary_required = max(0, int(max(1, int(context.capacity_min_signals)) - 1))
    secondary_hits = (
        int(1 if capacity_signal_mean else 0)
        + int(1 if context.temporal_signal else 0)
        + int(1 if correction.capacity_signal_learned else 0)
        + int(1 if context.cross_level_signal else 0)
        + int(1 if context.operator_signal else 0)
        + int(1 if context.cross_node_signal else 0)
        + int(1 if context.distributed_signal else 0)
        + int(1 if context.signed_signal else 0)
        + int(1 if context.consensus_signal else 0)
        + int(1 if context.cryptographic_signal else 0)
        + int(1 if context.attestation_signal else 0)
        + int(1 if context.byzantine_signal else 0)
    )
    capacity_triggered = bool(capacity_signal_ratio and secondary_hits >= secondary_required)

    event: Dict[str, object] = {
        "type": "refinement",
        "detector": "capacity_pressure" if capacity_triggered else "energy_overflow",
        "roi": {
            "center_x": int(roi.center_x),
            "center_y": int(roi.center_y),
            "radius": int(roi.radius),
            "area": int(roi.area),
            "boundary": context.boundary,
        },
        "detector_overflow_count": int(context.overflow_count),
        "detector_overflow_ratio": float(context.overflow_ratio),
        "detector_capacity_ratio_threshold": float(context.capacity_ratio_threshold),
        "detector_overflow_mean": float(context.overflow_mean),
        "detector_capacity_mean_threshold": float(context.capacity_mean_threshold),
        "detector_capacity_min_signals": int(context.capacity_min_signals),
        "detector_capacity_secondary_required": int(secondary_required),
        "detector_capacity_secondary_hits": int(secondary_hits),
        "detector_capacity_learned_hits_threshold": int(correction.learned_hits_threshold),
        "detector_capacity_learned_hits": int(correction.learned_hits),
        "detector_capacity_cross_level_window": int(context.cross_level_window),
        "detector_capacity_cross_level_min_levels": int(context.cross_level_min_levels),
        "detector_capacity_cross_level_unique_count": int(context.cross_level_unique_count),
        "detector_capacity_cross_level_levels": list(context.cross_level_unique),
        "detector_capacity_operator_score_threshold": float(context.operator_score_threshold),
        "detector_capacity_operator_score": float(context.operator_score),
        "detector_capacity_cross_node_min_signals": int(context.cross_node_min_signals),
        "detector_capacity_cross_node_hits": int(context.cross_node_hits),
        "detector_capacity_distributed_accepted_min": int(context.distributed_accepted_min),
        "detector_capacity_distributed_accepted": int(context.distributed_accepted),
        "detector_capacity_signed_acks_min": int(context.signed_acks_min),
        "detector_capacity_signed_acks": int(context.signed_acks),
        "detector_capacity_consensus_accepted_min": int(context.consensus_accepted_min),
        "detector_capacity_consensus_pending": int(context.consensus_pending),
        "detector_capacity_consensus_rejected": int(context.consensus_rejected),
        "detector_capacity_crypto_validator_coverage_min": float(context.crypto_validator_coverage_min),
        "detector_capacity_crypto_validator_coverage": float(context.crypto_validator_coverage),
        "detector_capacity_attestation_min_coverage": float(context.attestation_min_coverage),
        "detector_capacity_attestation_coverage": float(context.attestation_coverage),
        "detector_capacity_attestation_validator_ids": list(context.attestation_required_ids),
        "detector_capacity_byzantine_clean_min": int(context.byzantine_clean_min),
        "detector_capacity_triggered": bool(capacity_triggered),
        "detector_capacity_signals": {
            "overflow_ratio": {
                "value": float(context.overflow_ratio),
                "threshold": float(context.capacity_ratio_threshold),
                "passed": bool(capacity_signal_ratio),
            },
            "overflow_mean": {
                "value": float(context.overflow_mean),
                "threshold": float(context.capacity_mean_threshold),
                "passed": bool(capacity_signal_mean),
            },
            "temporal_sustained": {
                "value": int(context.temporal_hits),
                "threshold": int(context.temporal_required_hits),
                "window": int(context.temporal_window),
                "history_length": int(context.temporal_history_len),
                "ratio_threshold": float(context.temporal_ratio_threshold),
                "passed": bool(context.temporal_signal),
            },
            "learned_reuse": {
                "value": int(correction.learned_hits),
                "threshold": int(correction.learned_hits_threshold),
                "passed": bool(correction.capacity_signal_learned),
                "reused": bool(correction.reused),
            },
            "cross_level": {
                "value": int(context.cross_level_unique_count),
                "threshold": int(context.cross_level_min_levels),
                "window": int(context.cross_level_window),
                "levels": list(context.cross_level_unique),
                "passed": bool(context.cross_level_signal),
            },
            "operator_signal": {
                "value": float(context.operator_score),
                "threshold": float(context.operator_score_threshold),
                "passed": bool(context.operator_signal),
            },
            "cross_node": {
                "value": int(context.cross_node_hits),
                "threshold": int(context.cross_node_min_signals),
                "replay_failed": bool(context.cross_node_replay_failed),
                "delivery_rejected": bool(context.cross_node_delivery_rejected),
                "delivery_pending": bool(context.cross_node_delivery_pending),
                "passed": bool(context.cross_node_signal),
            },
            "distributed_quorum": {
                "value": int(context.distributed_accepted),
                "threshold": int(context.distributed_accepted_min),
                "passed": bool(context.distributed_signal),
            },
            "signed_ack_evidence": {
                "value": int(context.signed_acks),
                "threshold": int(context.signed_acks_min),
                "passed": bool(context.signed_signal),
            },
            "consensus_grade": {
                "value": int(context.distributed_accepted),
                "threshold": int(context.consensus_accepted_min),
                "pending_count": int(context.consensus_pending),
                "rejected_count": int(context.consensus_rejected),
                "passed": bool(context.consensus_signal),
            },
            "cryptographic_grade": {
                "value": float(context.crypto_validator_coverage),
                "threshold": float(context.crypto_validator_coverage_min),
                "passed": bool(context.cryptographic_signal),
            },
            "attestation_grade": {
                "value": float(context.attestation_coverage),
                "threshold": float(context.attestation_min_coverage),
                "validator_ids": list(context.attestation_required_ids),
                "passed": bool(context.attestation_signal),
            },
            "byzantine_grade": {
                "value": int(context.distributed_accepted),
                "threshold": int(context.byzantine_clean_min),
                "pending_count": int(context.consensus_pending),
                "rejected_count": int(context.consensus_rejected),
                "replay_failed": bool(context.cross_node_replay_failed),
                "delivery_rejected": bool(context.cross_node_delivery_rejected),
                "passed": bool(context.byzantine_signal),
            },
        },
        "detector_bounds": {"min": float(context.lo), "max": float(context.hi)},
        "correction": {
            "blend": float(correction.blend),
            "entropy_mean_before": float(correction.entropy_before_roi),
            "entropy_mean_after": float(correction.entropy_after_roi),
            "entropy_delta": float(correction.entropy_delta),
            "energy_l2_delta": float(correction.energy_l2_delta),
            "overflow_count_before": int(correction.overflow_count_before),
            "overflow_count_after": int(correction.overflow_count_after),
        },
    }

    if correction.remembered_hits is not None and correction.pattern_key is not None:
        event["pattern"] = {
            "key": str(correction.pattern_key),
            "reused": bool(correction.reused),
            "hits": int(correction.remembered_hits),
            "cache_size": int(pattern_runtime.cache_size()) if pattern_runtime is not None else 0,
        }

    return event


__all__ = ["build_nonfinite_event", "build_overflow_event"]
