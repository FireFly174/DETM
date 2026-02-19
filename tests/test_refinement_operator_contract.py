from __future__ import annotations

from detm.runtime.refinement.pipeline.operator_contract import assess_discrete_torsion


def test_discrete_torsion_contract_bootstrap_without_previous_decision():
    assessment = assess_discrete_torsion(
        previous_decision=None,
        active_level="L0",
        pattern_mode="minimal",
        operator_source="search",
        operator_hits_before=0,
        overflow_count_before=3,
        overflow_count_after=1,
        entropy_delta=0.05,
        energy_l2_delta=0.10,
    )
    assert assessment.torsion_flag is False
    assert assessment.compatible is True
    assert assessment.commutator_proxy == 0.0


def test_discrete_torsion_contract_flags_same_scope_large_shift():
    previous = {
        "level": "L0",
        "mode": "minimal",
        "hits_after": 4,
        "overflow_count_before": 12,
        "overflow_count_after": 3,
        "entropy_delta": -0.02,
        "energy_l2_delta": 0.06,
    }
    assessment = assess_discrete_torsion(
        previous_decision=previous,
        active_level="L0",
        pattern_mode="minimal",
        operator_source="search",
        operator_hits_before=0,
        overflow_count_before=7,
        overflow_count_after=6,
        entropy_delta=0.80,
        energy_l2_delta=1.20,
        torsion_threshold=1.0,
    )
    assert assessment.scope_changed is False
    assert assessment.torsion_flag is True
    assert assessment.compatible is False
    assert assessment.torsion_score >= assessment.torsion_threshold


def test_discrete_torsion_contract_does_not_flag_cross_scope_shift():
    previous = {
        "level": "L0",
        "mode": "minimal",
        "hits_after": 3,
        "overflow_count_before": 8,
        "overflow_count_after": 3,
        "entropy_delta": -0.01,
        "energy_l2_delta": 0.03,
    }
    assessment = assess_discrete_torsion(
        previous_decision=previous,
        active_level="L1",
        pattern_mode="cpu_full",
        operator_source="search",
        operator_hits_before=0,
        overflow_count_before=8,
        overflow_count_after=3,
        entropy_delta=0.9,
        energy_l2_delta=1.1,
        torsion_threshold=0.5,
    )
    assert assessment.scope_changed is True
    assert assessment.torsion_flag is False
