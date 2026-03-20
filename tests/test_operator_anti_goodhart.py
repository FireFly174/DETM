from __future__ import annotations

from detm_app.runtime.subscribers.watch.portability import (
    AntiGoodhartThresholds,
    evaluate_anti_goodhart,
)
from detm_app.runtime.session.adaptive import (
    advance_exploration_horizon,
    derive_exploration_horizon_break_reason,
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


def test_derive_exploration_horizon_break_reason_prefers_manual_stop_then_goodhart_then_boundary():
    assert (
        derive_exploration_horizon_break_reason(
            anti_snapshot={"goodhart_flag": True},
            panel={"acceptance": {"passed": False}},
            decisions=[{"contract": {"torsion_flag": True}}],
            manual_stop=True,
        )
        == "manual_stop"
    )
    assert (
        derive_exploration_horizon_break_reason(
            anti_snapshot={"goodhart_flag": True},
            panel={"acceptance": {"passed": False}},
            decisions=[{"contract": {"torsion_flag": True}}],
            manual_stop=False,
        )
        == "goodhart_flag"
    )
    assert (
        derive_exploration_horizon_break_reason(
            anti_snapshot={"goodhart_flag": False},
            panel={"acceptance": {"passed": False}},
            decisions=[{"contract": {"torsion_flag": True}}],
            manual_stop=False,
        )
        == "boundary_stress"
    )
    assert (
        derive_exploration_horizon_break_reason(
            anti_snapshot={"goodhart_flag": False},
            panel={"acceptance": {"passed": False}},
            decisions=[],
            manual_stop=False,
        )
        == "readout_degraded"
    )


def test_derive_exploration_horizon_break_reason_ignores_cold_start_acceptance_failure():
    assert (
        derive_exploration_horizon_break_reason(
            anti_snapshot={"goodhart_flag": False, "applicability": "cold_start"},
            panel={"acceptance": {"passed": False, "failed_signals": ["operator_reuse"]}},
            decisions=[{"contract": {"torsion_flag": False}}],
            manual_stop=False,
        )
        == ""
    )


def test_advance_exploration_horizon_tracks_break_and_recovery_ticks():
    runtime = {}

    first = advance_exploration_horizon(runtime=runtime, tick=1, break_reason="")
    assert int(first.get("exploration_horizon_ticks", 0)) == 1
    assert int(first.get("horizon_start_tick", 0)) == 1
    assert str(first.get("horizon_break_reason", "")) == ""
    assert int(first.get("horizon_recovery_cost_ticks", 0)) == 0

    broken = advance_exploration_horizon(runtime=runtime, tick=3, break_reason="goodhart_flag")
    assert int(broken.get("exploration_horizon_ticks", 0)) == 3
    assert int(broken.get("horizon_start_tick", 0)) == 1
    assert str(broken.get("horizon_break_reason", "")) == "goodhart_flag"
    assert int(broken.get("horizon_recovery_cost_ticks", 0)) == 0

    recovered = advance_exploration_horizon(runtime=runtime, tick=5, break_reason="")
    assert int(recovered.get("exploration_horizon_ticks", 0)) == 1
    assert int(recovered.get("horizon_start_tick", 0)) == 5
    assert str(recovered.get("horizon_break_reason", "")) == ""
    assert int(recovered.get("horizon_recovery_cost_ticks", 0)) == 2


def test_advance_exploration_horizon_does_not_start_without_eligible_decisions():
    runtime = {}

    idle = advance_exploration_horizon(runtime=runtime, tick=4, break_reason="", can_start=False)
    assert int(idle.get("exploration_horizon_ticks", 0)) == 0
    assert int(idle.get("horizon_start_tick", 0)) == 0
    assert str(idle.get("horizon_break_reason", "")) == ""
    assert int(idle.get("horizon_recovery_cost_ticks", 0)) == 0

    broken = advance_exploration_horizon(
        runtime=runtime,
        tick=5,
        break_reason="readout_degraded",
        can_start=False,
    )
    assert int(broken.get("exploration_horizon_ticks", 0)) == 0
    assert int(broken.get("horizon_start_tick", 0)) == 0
    assert str(broken.get("horizon_break_reason", "")) == "readout_degraded"
    assert int(broken.get("horizon_recovery_cost_ticks", 0)) == 0
