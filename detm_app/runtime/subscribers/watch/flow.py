"""Data-shaping helpers for watch trace/contract subscribers."""

from __future__ import annotations

from typing import Any

from detm.runtime import api
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.watch_contract import OuterFieldsRef, WatchContractPacket

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


def runtime_watchpoints(
    *,
    events: list[dict[str, Any]],
    policy_decision: PolicyDecision,
    observables: api.Observables,
    include_telemetry: bool,
) -> dict[str, Any]:
    out = {
        "refinement_count": int(sum(1 for event in events if str(event.get("type", "")) == "refinement")),
        "influence_count": int(sum(1 for event in events if str(event.get("type", "")) == "influence")),
        "attractor_count": int(sum(1 for event in events if str(event.get("type", "")) == "attractor")),
        "runtime_adaptive_window_active": bool(policy_decision.runtime_adaptive_window_active),
        "runtime_adaptive_signal_triggered": bool(policy_decision.runtime_adaptive_signal_triggered),
        "runtime_adaptive_profile": str(policy_decision.runtime_adaptive_profile),
        "runtime_adaptive_signal_hits": {
            str(k): bool(v) for k, v in dict(policy_decision.runtime_adaptive_signal_hits).items()
        },
    }
    if bool(include_telemetry):
        out["cpu_time_ms"] = float(observables.cost.get("cpu_time_ms", 0.0))
        out["step_ops_estimate"] = float(observables.cost.get("step_ops_estimate", 0.0))
        out["oscillation_score"] = float(observables.quality.get("oscillation_score", 0.0))
    return out


def runtime_policy_projection(policy_decision: PolicyDecision) -> dict[str, Any]:
    return {
        "active_level": str(policy_decision.active_level),
        "detail_mode": policy_decision.observability_profile.normalized_detail_mode(),
        "commit_stride": int(policy_decision.commit_stride),
        "runtime_adaptive_window_active": bool(policy_decision.runtime_adaptive_window_active),
        "runtime_adaptive_profile": str(policy_decision.runtime_adaptive_profile),
        "runtime_adaptive_signal_triggered": bool(policy_decision.runtime_adaptive_signal_triggered),
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
    return {
        "type": "watch_step",
        "tick": tick,
        "trace_ref": _trace_ref_for_tick(tick),
        "event_types": kinds,
        "event_count": int(len(kinds)),
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
    )


__all__ = [
    "build_watch_contract_packet",
    "build_watch_trace_entry",
    "filter_events",
    "resolve_policy_decision",
    "runtime_policy_projection",
    "runtime_watchpoints",
]
