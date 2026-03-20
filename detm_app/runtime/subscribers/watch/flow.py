"""Data-shaping helpers for watch trace/contract subscribers."""

from __future__ import annotations

from typing import Any

from detm.runtime import api
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.signature import projection_metadata_any
from detm.runtime.watch_contract import (
    AntiGoodhartSnapshot,
    ExplorationHorizonSnapshot,
    OuterFieldsRef,
    WatchContractPacket,
)

from detm_app.runtime.subscribers.common import _trace_ref_for_tick


def resolve_policy_decision(
    *,
    state: Any,
    n_ticks: int,
    requested_n_ticks: int,
    level_policy: LevelPolicy | None,
    policy_decision: PolicyDecision | None,
) -> PolicyDecision:
    if policy_decision is not None:
        return policy_decision
    inferred_policy = level_policy if level_policy is not None else LevelPolicy()
    return inferred_policy.decide(
        step_count=max(0, int(state.step_count) - int(n_ticks)),
        requested_n_ticks=int(requested_n_ticks or n_ticks),
    )


def filter_events(
    *,
    observables: api.Observables,
    policy_decision: PolicyDecision,
) -> list[dict[str, Any]]:
    return [
        event
        for event in list(observables.events)
        if policy_decision.observability_profile.allows_event_type(str(event.get("type", "")))
    ]


def event_types(events: list[dict[str, Any]]) -> list[str]:
    return [str(event.get("type", "")) for event in events]


def anti_goodhart_projection(policy_decision: PolicyDecision) -> dict[str, Any]:
    guard = dict(policy_decision.runtime_adaptive_guard)
    raw = guard.get("anti_goodhart", {})
    payload = dict(raw) if isinstance(raw, dict) else {}
    return AntiGoodhartSnapshot.from_dict(payload).to_dict()


def exploration_horizon_projection(policy_decision: PolicyDecision) -> dict[str, Any]:
    guard = dict(policy_decision.runtime_adaptive_guard)
    raw = guard.get("exploration_horizon", {})
    payload = dict(raw) if isinstance(raw, dict) else {}
    return ExplorationHorizonSnapshot.from_dict(payload).to_dict()


def operator_decision_rows(*, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        if str(event.get("type", "")) != "refinement":
            continue
        operator = event.get("operator")
        if not isinstance(operator, dict):
            continue
        row = dict(operator)
        row["id"] = str(row.get("id", ""))
        row["source"] = str(row.get("source", ""))
        row["accepted"] = bool(row.get("accepted", False))
        selection = row.get("selection", {})
        row["selection"] = dict(selection) if isinstance(selection, dict) else {}
        scope = row.get("scope", {})
        row["scope"] = dict(scope) if isinstance(scope, dict) else {}
        contract = row.get("contract", {})
        row["contract"] = dict(contract) if isinstance(contract, dict) else {}
        rows.append(row)
    return rows


def runtime_watchpoints(
    *,
    events: list[dict[str, Any]],
    policy_decision: PolicyDecision,
    observables: api.Observables,
    include_telemetry: bool,
) -> dict[str, Any]:
    operator_events = [
        dict(event.get("operator", {}))
        for event in events
        if str(event.get("type", "")) == "refinement" and isinstance(event.get("operator", None), dict)
    ]
    operator_decision_count = int(len(operator_events))
    operator_reuse_count = int(sum(1 for op in operator_events if str(op.get("source", "")) == "reuse"))
    operator_search_count = int(sum(1 for op in operator_events if str(op.get("source", "")) == "search"))
    operator_torsion_guard_block_count = int(
        sum(
            1
            for op in operator_events
            if str(dict(op.get("selection", {})).get("reason", "")) == "torsion_guard_blocked"
        )
    )
    torsion_flags = [
        bool(dict(op.get("contract", {})).get("torsion_flag"))
        for op in operator_events
        if isinstance(op.get("contract", None), dict)
    ]
    torsion_scores = [
        float(dict(op.get("contract", {})).get("torsion_score", 0.0))
        for op in operator_events
        if isinstance(op.get("contract", None), dict)
    ]
    operator_torsion_flag_count = int(sum(1 for flag in torsion_flags if bool(flag)))
    operator_reuse_rate = (
        float(operator_reuse_count) / float(operator_decision_count)
        if operator_decision_count > 0
        else 0.0
    )
    operator_torsion_mean = (
        float(sum(torsion_scores) / len(torsion_scores))
        if len(torsion_scores) > 0
        else 0.0
    )
    anti_goodhart = anti_goodhart_projection(policy_decision)
    exploration_horizon = exploration_horizon_projection(policy_decision)
    out = {
        "refinement_count": int(sum(1 for event in events if str(event.get("type", "")) == "refinement")),
        "influence_count": int(sum(1 for event in events if str(event.get("type", "")) == "influence")),
        "attractor_count": int(sum(1 for event in events if str(event.get("type", "")) == "attractor")),
        "operator_decision_count": int(operator_decision_count),
        "operator_reuse_count": int(operator_reuse_count),
        "operator_search_count": int(operator_search_count),
        "operator_reuse_rate": float(operator_reuse_rate),
        "operator_torsion_guard_block_count": int(operator_torsion_guard_block_count),
        "operator_torsion_flag_count": int(operator_torsion_flag_count),
        "operator_torsion_score_mean": float(operator_torsion_mean),
        "runtime_adaptive_window_active": bool(policy_decision.runtime_adaptive_window_active),
        "runtime_adaptive_signal_triggered": bool(policy_decision.runtime_adaptive_signal_triggered),
        "runtime_adaptive_profile": str(policy_decision.runtime_adaptive_profile),
        "runtime_adaptive_signal_hits": {
            str(k): bool(v) for k, v in dict(policy_decision.runtime_adaptive_signal_hits).items()
        },
        "anti_goodhart_flag": bool(anti_goodhart.get("goodhart_flag", False)),
        "anti_goodhart_degraded_signal_count": int(anti_goodhart.get("degraded_signal_count", 0)),
        "anti_goodhart_policy_reaction_applied": bool(
            dict(anti_goodhart.get("policy_reaction", {})).get("apply", False)
        ),
        "anti_goodhart_runtime_profile_applied": bool(
            anti_goodhart.get("runtime_profile_applied", False)
        ),
        "anti_goodhart": anti_goodhart,
        "exploration_horizon_ticks": int(exploration_horizon.get("exploration_horizon_ticks", 0)),
        "horizon_start_tick": int(exploration_horizon.get("horizon_start_tick", 0)),
        "horizon_break_reason": str(exploration_horizon.get("horizon_break_reason", "")),
        "horizon_recovery_cost_ticks": int(exploration_horizon.get("horizon_recovery_cost_ticks", 0)),
        "exploration_horizon": exploration_horizon,
    }
    if bool(include_telemetry):
        out["cpu_time_ms"] = float(observables.cost.get("cpu_time_ms", 0.0))
        out["step_ops_estimate"] = float(observables.cost.get("step_ops_estimate", 0.0))
        out["oscillation_score"] = float(observables.quality.get("oscillation_score", 0.0))
    return out


def runtime_policy_projection(policy_decision: PolicyDecision) -> dict[str, Any]:
    anti_goodhart = anti_goodhart_projection(policy_decision)
    exploration_horizon = exploration_horizon_projection(policy_decision)
    return {
        "active_level": str(policy_decision.active_level),
        "detail_mode": policy_decision.observability_profile.normalized_detail_mode(),
        "commit_stride": int(policy_decision.commit_stride),
        "runtime_adaptive_window_active": bool(policy_decision.runtime_adaptive_window_active),
        "runtime_adaptive_profile": str(policy_decision.runtime_adaptive_profile),
        "runtime_adaptive_signal_triggered": bool(policy_decision.runtime_adaptive_signal_triggered),
        "anti_goodhart": anti_goodhart,
        "exploration_horizon": exploration_horizon,
    }


def build_watch_trace_entry(
    *,
    state: Any,
    observables: api.Observables,
    policy_decision: PolicyDecision,
) -> dict[str, Any]:
    tick = int(state.step_count)
    events = filter_events(observables=observables, policy_decision=policy_decision)
    kinds = event_types(events)
    projection = projection_metadata_any(state.field_state.energy)
    return {
        "type": "watch_step",
        "tick": tick,
        "trace_ref": _trace_ref_for_tick(tick),
        "event_types": kinds,
        "event_count": int(len(kinds)),
        "projection": projection,
        "watchpoints": runtime_watchpoints(
            events=events,
            policy_decision=policy_decision,
            observables=observables,
            include_telemetry=True,
        ),
        "policy": runtime_policy_projection(policy_decision),
    }


def build_watch_contract_packet(
    *,
    state: Any,
    observables: api.Observables,
    policy_decision: PolicyDecision,
    n_ticks: int,
    level_src: str,
    base_level: str,
    uri: str,
    schema: str,
) -> WatchContractPacket:
    tick = int(state.step_count)
    events = filter_events(observables=observables, policy_decision=policy_decision)
    kinds = event_types(events)
    watchpoints = runtime_watchpoints(
        events=events,
        policy_decision=policy_decision,
        observables=observables,
        include_telemetry=False,
    )
    projection = projection_metadata_any(state.field_state.energy)
    outerfields_ref = OuterFieldsRef(
        kind="outerfields",
        level_src=str(level_src),
        base_level=str(base_level),
        tick=tick,
        window_ticks=max(1, int(n_ticks)),
        stride_ticks=max(1, int(policy_decision.commit_stride)),
        uri=str(uri),
        schema=str(schema),
    )
    return WatchContractPacket(
        tick=tick,
        trace_ref=str(_trace_ref_for_tick(tick)),
        outerfields_ref=outerfields_ref,
        signature=observables.signature.as_dict(),
        metrics={
            "cost": dict(observables.cost),
            "quality": dict(observables.quality),
            "watchpoints": watchpoints,
        },
        events=[dict(event) for event in events],
        event_types=kinds,
        event_count=int(len(kinds)),
        policy=runtime_policy_projection(policy_decision),
        projection=projection,
    )


def build_operator_decisions_entry(
    *,
    state: Any,
    observables: api.Observables,
    policy_decision: PolicyDecision,
) -> dict[str, Any]:
    tick = int(state.step_count)
    events = filter_events(observables=observables, policy_decision=policy_decision)
    decisions = operator_decision_rows(events=events)
    decision_count = int(len(decisions))
    reuse_count = int(sum(1 for row in decisions if str(row.get("source", "")) == "reuse"))
    search_count = int(sum(1 for row in decisions if str(row.get("source", "")) == "search"))
    guard_block_count = int(
        sum(
            1
            for row in decisions
            if str(dict(row.get("selection", {})).get("reason", "")) == "torsion_guard_blocked"
        )
    )
    torsion_flag_count = int(
        sum(1 for row in decisions if bool(dict(row.get("contract", {})).get("torsion_flag", False)))
    )
    return {
        "type": "operator_decisions_step",
        "tick": tick,
        "trace_ref": _trace_ref_for_tick(tick),
        "decision_count": decision_count,
        "decisions": decisions,
        "summary": {
            "reuse_count": reuse_count,
            "search_count": search_count,
            "torsion_guard_block_count": guard_block_count,
            "torsion_flag_count": torsion_flag_count,
            "reuse_rate": (float(reuse_count) / float(decision_count)) if decision_count > 0 else 0.0,
        },
        "policy": runtime_policy_projection(policy_decision),
    }


__all__ = [
    "build_operator_decisions_entry",
    "build_watch_contract_packet",
    "build_watch_trace_entry",
    "anti_goodhart_projection",
    "exploration_horizon_projection",
    "filter_events",
    "operator_decision_rows",
    "resolve_policy_decision",
    "runtime_policy_projection",
    "runtime_watchpoints",
]
