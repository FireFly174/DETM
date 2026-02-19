from __future__ import annotations

from detm_app.runtime.subscribers.watch.portability import (
    AntiGoodhartThresholds,
    evaluate_anti_goodhart,
)


def test_evaluate_anti_goodhart_triggers_when_target_rises_and_two_signals_degrade():
    thresholds = AntiGoodhartThresholds(
        target_signal="operator_reuse",
        min_target_delta=0.0,
        min_degraded_signals=2,
        degradation_epsilon=0.0,
    )
    previous = {
        "operator_reuse": 0.40,
        "hold_rate": 0.95,
        "transferability": 0.50,
        "torsion_health": 0.90,
    }
    current = {
        "operator_reuse": 0.55,
        "hold_rate": 0.91,
        "transferability": 0.42,
        "torsion_health": 0.89,
    }
    out = evaluate_anti_goodhart(panel=current, previous_panel=previous, thresholds=thresholds)
    assert bool(out.get("goodhart_flag")) is True
    assert int(out.get("degraded_signal_count", 0)) >= 2
    reaction = dict(out.get("policy_reaction", {}))
    assert bool(reaction.get("apply")) is True
    assert "downweight_target_signal" in list(reaction.get("actions", []))


def test_evaluate_anti_goodhart_does_not_trigger_with_single_degraded_signal():
    thresholds = AntiGoodhartThresholds(min_degraded_signals=2)
    previous = {
        "operator_reuse": 0.40,
        "hold_rate": 0.95,
        "transferability": 0.50,
        "torsion_health": 0.90,
    }
    current = {
        "operator_reuse": 0.55,
        "hold_rate": 0.95,
        "transferability": 0.48,
        "torsion_health": 0.90,
    }
    out = evaluate_anti_goodhart(panel=current, previous_panel=previous, thresholds=thresholds)
    assert bool(out.get("goodhart_flag")) is False
    assert int(out.get("degraded_signal_count", 0)) == 1


def test_evaluate_anti_goodhart_cold_start_is_not_flagged():
    thresholds = AntiGoodhartThresholds()
    current = {
        "operator_reuse": 0.55,
        "hold_rate": 0.95,
        "transferability": 0.48,
        "torsion_health": 0.90,
    }
    out = evaluate_anti_goodhart(panel=current, previous_panel=None, thresholds=thresholds)
    assert bool(out.get("goodhart_flag")) is False
    assert str(out.get("applicability", "")) == "cold_start"
