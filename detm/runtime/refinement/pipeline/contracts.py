"""Explicit contracts for refinement pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DetectionContext:
    boundary: str
    energy: np.ndarray
    entropy: np.ndarray
    internal_time: np.ndarray
    lo: float
    hi: float
    overflow_count: int
    overflow_ratio: float
    overflow_mean: float
    overflow_score: np.ndarray
    capacity_ratio_threshold: float
    capacity_mean_threshold: float
    capacity_saturation_band: float
    capacity_min_signals: int
    capacity_autoclamp_enabled: bool
    temporal_ratio_threshold: float
    temporal_window: int
    temporal_required_hits: int
    temporal_hits: int
    temporal_history_len: int
    temporal_signal: bool
    learned_hits_threshold: int
    cross_level_window: int
    cross_level_min_levels: int
    cross_level_unique: list[str]
    cross_level_unique_count: int
    cross_level_signal: bool
    operator_score_threshold: float
    operator_score: float
    operator_signal: bool
    cross_node_min_signals: int
    cross_node_hits: int
    cross_node_signal: bool
    cross_node_replay_failed: bool
    cross_node_delivery_rejected: bool
    cross_node_delivery_pending: bool
    distributed_accepted_min: int
    distributed_accepted: int
    distributed_signal: bool
    signed_acks_min: int
    signed_acks: int
    signed_signal: bool
    consensus_accepted_min: int
    consensus_pending: int
    consensus_rejected: int
    consensus_signal: bool
    crypto_validator_coverage_min: float
    crypto_validator_coverage: float
    cryptographic_signal: bool
    attestation_min_coverage: float
    attestation_coverage: float
    attestation_required_ids: list[str]
    attestation_signal: bool
    byzantine_clean_min: int
    byzantine_signal: bool
    active_level_name: str
    pattern_mode_name: str


@dataclass(frozen=True)
class RoiSelection:
    center_x: int
    center_y: int
    radius: int
    area: int
    mask: np.ndarray
    boundary: str


@dataclass(frozen=True)
class NonfiniteRoiSelection(RoiSelection):
    nonfinite_energy: np.ndarray
    nonfinite_entropy: np.ndarray
    nonfinite_tau: np.ndarray
    nonfinite_total_count: int


@dataclass(frozen=True)
class NonfiniteCorrectionResult:
    energy_l2_delta: float
    nonfinite_total_before: int
    nonfinite_total_after: int


@dataclass(frozen=True)
class OverflowCorrectionResult:
    blend: float
    entropy_before_roi: float
    entropy_after_roi: float
    entropy_delta: float
    energy_l2_delta: float
    overflow_count_before: int
    overflow_count_after: int
    pattern_key: str | None
    operator_id: str
    operator_source: str
    operator_hits_before: int
    operator_hits_after: int
    operator_score: float
    operator_commutator_proxy: float
    operator_torsion_score: float
    operator_torsion_threshold: float
    operator_torsion_flag: bool
    operator_contract_compatible: bool
    operator_scope_changed: bool
    operator_selection_rule: str
    operator_selection_reason: str
    reused: bool
    learned_hits: int
    learned_hits_threshold: int
    capacity_signal_learned: bool
    remembered_hits: int | None


__all__ = [
    "DetectionContext",
    "NonfiniteCorrectionResult",
    "NonfiniteRoiSelection",
    "OverflowCorrectionResult",
    "RoiSelection",
]
