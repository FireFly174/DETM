"""Data-shaping and plugin execution helpers for system trace subscriber."""

from __future__ import annotations

from typing import Any, Dict, Sequence

from detm.runtime import api
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import PolicyDecision
from detm.runtime.state import DETMState
from detm.metrics.base import MetricContext, MetricPlugin

from detm_app.runtime.subscribers.common import _trace_ref_for_tick
from detm_app.runtime.subscribers.watch.flow import resolve_policy_decision


def filter_events(*, observables: api.Observables, policy_decision: PolicyDecision) -> list[dict[str, Any]]:
    return [
        event
        for event in list(observables.events)
        if policy_decision.observability_profile.allows_event_type(str(event.get("type", "")))
    ]


def compute_plugin_metrics(
    *,
    metric_plugins: Sequence[MetricPlugin],
    state: DETMState,
    observables: api.Observables,
    filtered_events: list[dict[str, Any]],
    influence: DETMInfluence | None,
    n_ticks: int,
    get_state_blob: Any | None,
    detail_mode: str,
) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    if str(detail_mode) == "minimal":
        return metrics
    filtered_observables = api.Observables(
        signature=observables.signature,
        field_summaries=observables.field_summaries,
        events=filtered_events,
        cost=observables.cost,
        quality=observables.quality,
    )
    ctx = MetricContext(
        state=state,
        observables=filtered_observables,
        influence=influence,
        n_ticks=int(n_ticks),
        get_state_blob=get_state_blob,
    )
    for plugin in metric_plugins:
        key = str(getattr(plugin, "name", plugin.__class__.__name__))
        try:
            metrics[key] = plugin.compute(ctx)
        except Exception as exc:
            metrics[key] = {"error": str(exc)}
    return metrics


def build_trace_entry(
    *,
    state: DETMState,
    influence: DETMInfluence | None,
    n_ticks: int,
    requested_n_ticks: int,
    step_requested_n_ticks: int,
    step_effective_n_ticks: int,
    observables: api.Observables,
    filtered_events: list[dict[str, Any]],
    metrics: Dict[str, Any],
    detail_mode: str,
    policy_decision: PolicyDecision,
) -> dict[str, Any]:
    tick = int(state.step_count)
    return {
        "type": "step",
        "tick": tick,
        "trace_ref": _trace_ref_for_tick(tick),
        # Backward-compatible alias: historically n_ticks is publish chunk size.
        "n_ticks": int(n_ticks),
        "chunk_n_ticks": int(n_ticks),
        "requested_n_ticks": int(requested_n_ticks or n_ticks),
        "step_requested_n_ticks": int(step_requested_n_ticks or requested_n_ticks or n_ticks),
        "step_effective_n_ticks": int(step_effective_n_ticks or n_ticks),
        "influence": influence.__dict__ if (influence is not None and detail_mode == "debug") else None,
        "signature": observables.signature.as_dict(),
        "field_summaries": None
        if detail_mode == "minimal"
        else {
            "energy": observables.field_summaries.energy,
            "entropy": observables.field_summaries.entropy,
            "internal_time": observables.field_summaries.internal_time,
        },
        "cost": dict(observables.cost),
        "quality": dict(observables.quality),
        "events": filtered_events if detail_mode != "minimal" else [],
        "event_types": [str(event.get("type", "")) for event in filtered_events],
        "event_count": len(filtered_events),
        "metrics": metrics,
        "detail_mode": detail_mode,
        "policy": policy_decision.to_dict(),
    }


__all__ = [
    "build_trace_entry",
    "compute_plugin_metrics",
    "filter_events",
    "resolve_policy_decision",
]
