"""Discrete operator-contract checks for refinement pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class OperatorContractAssessment:
    commutator_proxy: float
    torsion_score: float
    torsion_threshold: float
    torsion_flag: bool
    compatible: bool
    scope_changed: bool


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def assess_discrete_torsion(
    *,
    previous_decision: Mapping[str, object] | None,
    active_level: str,
    pattern_mode: str,
    operator_source: str,
    operator_hits_before: int,
    overflow_count_before: int,
    overflow_count_after: int,
    entropy_delta: float,
    energy_l2_delta: float,
    torsion_threshold: float = 1.0,
) -> OperatorContractAssessment:
    """Assess local operator compatibility via a discrete torsion proxy.

    The proxy is intentionally lightweight: it compares adjacent operator
    effects in the same scope and raises a flag when correction geometry
    diverges sharply while overflow reduction regresses or jumps.
    """

    threshold = max(0.0, float(torsion_threshold))
    if previous_decision is None or len(dict(previous_decision)) == 0:
        compatible = bool(int(overflow_count_after) <= int(overflow_count_before))
        return OperatorContractAssessment(
            commutator_proxy=0.0,
            torsion_score=0.0,
            torsion_threshold=threshold,
            torsion_flag=False,
            compatible=compatible,
            scope_changed=False,
        )

    prev = dict(previous_decision)
    prev_level = str(prev.get("level", ""))
    prev_mode = str(prev.get("mode", ""))
    scope_changed = bool(prev_level != str(active_level) or prev_mode != str(pattern_mode))

    prev_entropy_delta = _as_float(prev.get("entropy_delta"), 0.0)
    prev_energy_l2_delta = _as_float(prev.get("energy_l2_delta"), 0.0)
    prev_overflow_before = _as_int(prev.get("overflow_count_before"), 0)
    prev_overflow_after = _as_int(prev.get("overflow_count_after"), 0)
    prev_overflow_gain = max(0, int(prev_overflow_before) - int(prev_overflow_after))
    now_overflow_gain = max(0, int(overflow_count_before) - int(overflow_count_after))

    delta_entropy = abs(abs(float(entropy_delta)) - abs(float(prev_entropy_delta)))
    delta_energy = abs(float(energy_l2_delta) - float(prev_energy_l2_delta))
    delta_gain = abs(float(now_overflow_gain) - float(prev_overflow_gain))
    commutator_proxy = float(delta_entropy + delta_energy + 0.25 * delta_gain)

    regression_penalty = 0.5 if int(overflow_count_after) > int(overflow_count_before) else 0.0
    prev_hits_after = _as_int(prev.get("hits_after"), 0)
    novelty_penalty = 0.0
    if (
        not scope_changed
        and str(operator_source) == "search"
        and int(operator_hits_before) <= 0
        and int(prev_hits_after) >= 2
    ):
        novelty_penalty = 0.25

    torsion_score = float(commutator_proxy + regression_penalty + novelty_penalty)
    torsion_flag = bool((not scope_changed) and torsion_score >= threshold)
    compatible = bool((not torsion_flag) and int(overflow_count_after) <= int(overflow_count_before))
    return OperatorContractAssessment(
        commutator_proxy=float(commutator_proxy),
        torsion_score=float(torsion_score),
        torsion_threshold=float(threshold),
        torsion_flag=bool(torsion_flag),
        compatible=bool(compatible),
        scope_changed=bool(scope_changed),
    )


__all__ = ["OperatorContractAssessment", "assess_discrete_torsion"]
