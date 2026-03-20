"""Learning/readout helpers for UI runtime runners."""

from __future__ import annotations

from collections import deque
from typing import Any

from detm.runtime import api
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.signature import projection_metadata_any
from detm.runtime.state import DETMState
from detm_app.runtime.subscribers.watch.flow import filter_events, operator_decision_rows, runtime_watchpoints
from detm_app.runtime.subscribers.watch.portability import PortabilityThresholds, evaluate_portability_acceptance


def _normalize_field_stats(raw: dict[str, Any]) -> dict[str, float]:
    minimum = float(raw.get("minimum", 0.0))
    maximum = float(raw.get("maximum", 0.0))
    variance = float(raw.get("variance", 0.0))
    return {
        "minimum": float(minimum),
        "maximum": float(maximum),
        "mean": float(raw.get("mean", 0.0)),
        "variance": float(variance),
        "std": float(max(0.0, variance) ** 0.5),
        "range": float(maximum - minimum),
    }


def init_learning_runtime(*, window_steps: int = 64) -> dict[str, Any]:
    return {
        "window_steps": max(1, int(window_steps)),
        "recent": deque(),
        "operator_scopes": {},
        "total_decisions": 0,
        "compatible_decisions": 0,
        "reuse_decisions": 0,
        "transferable_reuse_decisions": 0,
        "torsion_flag_decisions": 0,
        "last_snapshot": {},
    }


def reset_learning_runtime(runtime: dict[str, Any], *, window_steps: int | None = None) -> None:
    window = int(runtime.get("window_steps", 64))
    if window_steps is not None:
        window = max(1, int(window_steps))
    fresh = init_learning_runtime(window_steps=window)
    runtime.clear()
    runtime.update(fresh)


def configure_learning_runtime(runtime: dict[str, Any], *, window_steps: int) -> None:
    desired = max(1, int(window_steps))
    current = max(1, int(runtime.get("window_steps", desired)))
    if desired == current:
        return
    runtime["window_steps"] = desired
    recent = runtime.get("recent")
    rows = list(recent) if isinstance(recent, deque) else []
    runtime["recent"] = deque(rows[-desired:], maxlen=desired)


def _policy_decision_for_step(
    *,
    state: DETMState,
    n_ticks: int,
    requested_n_ticks: int,
    level_policy: LevelPolicy | None,
    policy_decision: PolicyDecision | None,
) -> PolicyDecision:
    if policy_decision is not None:
        return policy_decision
    active = level_policy if level_policy is not None else LevelPolicy()
    return active.decide(
        step_count=max(0, int(state.step_count) - int(n_ticks)),
        requested_n_ticks=int(requested_n_ticks or n_ticks),
    )


def _update_panel_counters(
    *,
    runtime: dict[str, Any],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    operator_scopes = runtime.get("operator_scopes")
    if not isinstance(operator_scopes, dict):
        operator_scopes = {}
        runtime["operator_scopes"] = operator_scopes

    for decision in list(decisions):
        runtime["total_decisions"] = int(runtime.get("total_decisions", 0)) + 1

        contract = dict(decision.get("contract", {}))
        if bool(contract.get("compatible", False)):
            runtime["compatible_decisions"] = int(runtime.get("compatible_decisions", 0)) + 1
        if bool(contract.get("torsion_flag", False)):
            runtime["torsion_flag_decisions"] = int(runtime.get("torsion_flag_decisions", 0)) + 1

        source = str(decision.get("source", "")).strip().lower()
        operator_id = str(decision.get("id", ""))
        scope = dict(decision.get("scope", {}))
        scope_tuple = (
            str(scope.get("level", "")),
            str(scope.get("mode", "")),
        )
        known_scopes = operator_scopes.get(operator_id, set())
        if not isinstance(known_scopes, set):
            known_scopes = set()
        if source == "reuse":
            runtime["reuse_decisions"] = int(runtime.get("reuse_decisions", 0)) + 1
            if len(known_scopes) > 0 and scope_tuple not in known_scopes:
                runtime["transferable_reuse_decisions"] = int(runtime.get("transferable_reuse_decisions", 0)) + 1
        known_scopes.add(scope_tuple)
        operator_scopes[operator_id] = known_scopes

    total = max(0, int(runtime.get("total_decisions", 0)))
    reuse = max(0, int(runtime.get("reuse_decisions", 0)))
    torsion_flags = max(0, int(runtime.get("torsion_flag_decisions", 0)))
    panel = {
        "hold_rate": (float(int(runtime.get("compatible_decisions", 0))) / float(total)) if total > 0 else 0.0,
        "operator_reuse": (float(reuse) / float(total)) if total > 0 else 0.0,
        "transferability": (
            float(int(runtime.get("transferable_reuse_decisions", 0))) / float(reuse) if reuse > 0 else 0.0
        ),
        "torsion_flag_rate": (float(torsion_flags) / float(total)) if total > 0 else 0.0,
        "torsion_health": (1.0 - (float(torsion_flags) / float(total))) if total > 0 else 1.0,
        "counts": {
            "total_decisions": int(total),
            "compatible_decisions": int(runtime.get("compatible_decisions", 0)),
            "reuse_decisions": int(reuse),
            "transferable_reuse_decisions": int(runtime.get("transferable_reuse_decisions", 0)),
            "torsion_flag_decisions": int(torsion_flags),
        },
    }
    thresholds = PortabilityThresholds()
    panel["thresholds"] = thresholds.to_dict()
    panel["acceptance"] = evaluate_portability_acceptance(panel=panel, thresholds=thresholds)
    return panel


def _window_summary(runtime: dict[str, Any]) -> dict[str, Any]:
    recent = runtime.get("recent")
    rows = list(recent) if isinstance(recent, deque) else []
    steps = max(0, int(len(rows)))
    events = int(sum(int(row.get("event_count", 0)) for row in rows))
    refinements = int(sum(int(row.get("refinement_count", 0)) for row in rows))
    decisions = int(sum(int(row.get("decision_count", 0)) for row in rows))
    reuse = int(sum(int(row.get("reuse_count", 0)) for row in rows))
    runtime_active = int(sum(int(bool(row.get("runtime_active", False))) for row in rows))
    anti_goodhart_true = int(sum(int(bool(row.get("anti_goodhart_flag", False))) for row in rows))
    return {
        "steps": int(steps),
        "event_count": int(events),
        "refinement_count": int(refinements),
        "decision_count": int(decisions),
        "reuse_rate": (float(reuse) / float(decisions)) if decisions > 0 else 0.0,
        "runtime_active_ratio": (float(runtime_active) / float(steps)) if steps > 0 else 0.0,
        "anti_goodhart_ratio": (float(anti_goodhart_true) / float(steps)) if steps > 0 else 0.0,
    }


def _projection_summary_text(raw: dict[str, Any]) -> str:
    payload = dict(raw or {})
    source_shape = list(payload.get("source_shape", []))
    projected_shape = list(payload.get("projected_shape", []))
    if len(source_shape) <= 0 or len(projected_shape) <= 0:
        return ""
    source = "x".join(str(int(dim)) for dim in source_shape)
    projected = "x".join(str(int(dim)) for dim in projected_shape)
    if source == projected:
        return ""
    return f"{source}->{projected}"


def update_learning_snapshot(
    runtime: dict[str, Any],
    *,
    state: DETMState,
    n_ticks: int,
    requested_n_ticks: int,
    observables: api.Observables,
    level_policy: LevelPolicy | None,
    policy_decision: PolicyDecision | None,
) -> dict[str, Any]:
    decision = _policy_decision_for_step(
        state=state,
        n_ticks=int(n_ticks),
        requested_n_ticks=int(requested_n_ticks),
        level_policy=level_policy,
        policy_decision=policy_decision,
    )
    events = filter_events(observables=observables, policy_decision=decision)
    watchpoints = runtime_watchpoints(
        events=events,
        policy_decision=decision,
        observables=observables,
        include_telemetry=True,
    )
    decisions = operator_decision_rows(events=events)
    panel = _update_panel_counters(runtime=runtime, decisions=decisions)
    projection = projection_metadata_any(state.field_state.energy)
    signature_summary = {
        str(key): float(value)
        for key, value in dict(getattr(observables.signature, "summary", {})).items()
        if isinstance(value, (int, float))
    }
    field_summaries = {
        "energy": _normalize_field_stats(dict(getattr(observables.field_summaries, "energy", {}))),
        "entropy": _normalize_field_stats(dict(getattr(observables.field_summaries, "entropy", {}))),
        "internal_time": _normalize_field_stats(dict(getattr(observables.field_summaries, "internal_time", {}))),
    }
    influence_events = [dict(event) for event in events if str(event.get("type", "")) == "influence"]
    last_influence = influence_events[-1] if len(influence_events) > 0 else {}

    window_steps = max(1, int(runtime.get("window_steps", 64)))
    recent = runtime.get("recent")
    if not isinstance(recent, deque):
        recent = deque()
    recent.append(
        {
            "event_count": int(len(events)),
            "refinement_count": int(sum(1 for event in events if str(event.get("type", "")) == "refinement")),
            "decision_count": int(len(decisions)),
            "reuse_count": int(sum(1 for row in decisions if str(row.get("source", "")) == "reuse")),
            "runtime_active": bool(watchpoints.get("runtime_adaptive_window_active", False)),
            "anti_goodhart_flag": bool(watchpoints.get("anti_goodhart_flag", False)),
        }
    )
    while len(recent) > window_steps:
        recent.popleft()
    recent = deque(list(recent), maxlen=window_steps)
    runtime["recent"] = recent

    snapshot = {
        "tick": int(state.step_count),
        "event_count": int(len(events)),
        "event_types": [str(event.get("type", "")) for event in events],
        "projection": projection,
        "watchpoints": watchpoints,
        "signature_summary": signature_summary,
        "field_summaries": field_summaries,
        "influence": {
            "count": int(len(influence_events)),
            "last_amplitude": float(last_influence.get("amplitude", 0.0)),
            "last_affected_fraction": float(last_influence.get("affected_fraction", 0.0)),
        },
        "portability_panel": panel,
        "window": _window_summary(runtime),
    }
    runtime["last_snapshot"] = dict(snapshot)
    return snapshot


def learning_status_compact(
    snapshot: dict[str, Any] | None,
    *,
    enabled: bool = True,
    max_len: int = 160,
) -> str:
    if not enabled:
        return "learn=off"
    payload = dict(snapshot or {})
    if len(payload) == 0:
        return "learn=na"
    panel = dict(payload.get("portability_panel", {}))
    counts = dict(panel.get("counts", {}))
    watchpoints = dict(payload.get("watchpoints", {}))
    total = int(counts.get("total_decisions", 0))
    operator_reuse = float(panel.get("operator_reuse", 0.0))
    transferability = float(panel.get("transferability", 0.0))
    hold_rate = float(panel.get("hold_rate", 0.0))
    runtime_profile = str(watchpoints.get("runtime_adaptive_profile", "manual"))
    runtime_active = bool(watchpoints.get("runtime_adaptive_window_active", False))
    anti_goodhart = bool(watchpoints.get("anti_goodhart_flag", False))
    projection_text = _projection_summary_text(dict(payload.get("projection", {})))
    out = (
        f"learn tick={int(payload.get('tick', 0))}"
        f" dec={total}"
        f" reuse={operator_reuse:.2f}"
        f" xfer={transferability:.2f}"
        f" hold={hold_rate:.2f}"
        f" rt={runtime_profile}{'*' if runtime_active else ''}"
        f" ag={1 if anti_goodhart else 0}"
    )
    if projection_text:
        out += f" proj={projection_text}"
    limit = max(32, int(max_len))
    if len(out) > limit:
        return out[: limit - 1] + "…"
    return out


def learning_status_multiline(
    snapshot: dict[str, Any] | None,
    *,
    enabled: bool = True,
) -> str:
    if not enabled:
        return "Learning view is disabled."
    payload = dict(snapshot or {})
    if len(payload) == 0:
        return "Learning snapshot is not available yet. Make one or more steps."

    panel = dict(payload.get("portability_panel", {}))
    counts = dict(panel.get("counts", {}))
    acceptance = dict(panel.get("acceptance", {}))
    watchpoints = dict(payload.get("watchpoints", {}))
    window = dict(payload.get("window", {}))
    anti = dict(watchpoints.get("anti_goodhart", {}))
    projection = dict(payload.get("projection", {}))
    lines = [
        f"Tick: {int(payload.get('tick', 0))}",
        f"Events: {int(payload.get('event_count', 0))}  types={list(payload.get('event_types', []))}",
    ]
    if len(projection) > 0:
        lines.extend(
            [
                "Projection:",
                "  source_shape="
                + str(list(projection.get("source_shape", [])))
                + " -> projected_shape="
                + str(list(projection.get("projected_shape", []))),
                "  reduction="
                + str(projection.get("reduction", ""))
                + " collapsed_axes="
                + str(list(projection.get("collapsed_axes", [])))
                + " planes="
                + str(int(projection.get("collapsed_plane_count", 0))),
            ]
        )
    lines.extend(
        [
            "Portability panel:",
            f"  hold_rate={float(panel.get('hold_rate', 0.0)):.4f}",
            f"  operator_reuse={float(panel.get('operator_reuse', 0.0)):.4f}",
            f"  transferability={float(panel.get('transferability', 0.0)):.4f}",
            f"  torsion_health={float(panel.get('torsion_health', 1.0)):.4f}",
            f"  acceptance.passed={bool(acceptance.get('passed', False))} failed={list(acceptance.get('failed_signals', []))}",
            "Counts:",
            f"  total={int(counts.get('total_decisions', 0))} reuse={int(counts.get('reuse_decisions', 0))} transferable_reuse={int(counts.get('transferable_reuse_decisions', 0))}",
            f"  compatible={int(counts.get('compatible_decisions', 0))} torsion_flag={int(counts.get('torsion_flag_decisions', 0))}",
            "Runtime adaptive / anti-goodhart:",
            f"  runtime_profile={str(watchpoints.get('runtime_adaptive_profile', 'manual'))} window_active={bool(watchpoints.get('runtime_adaptive_window_active', False))}",
            f"  signal_triggered={bool(watchpoints.get('runtime_adaptive_signal_triggered', False))} anti_goodhart_flag={bool(watchpoints.get('anti_goodhart_flag', False))}",
            f"  anti_goodhart.applicability={str(anti.get('applicability', 'n/a'))} degraded_count={int(anti.get('degraded_signal_count', 0))}",
            f"  anti_goodhart.reaction_applied={bool(watchpoints.get('anti_goodhart_policy_reaction_applied', False))} runtime_profile_applied={bool(watchpoints.get('anti_goodhart_runtime_profile_applied', False))}",
            "Exploration horizon:",
            f"  ticks={int(watchpoints.get('exploration_horizon_ticks', 0))} start_tick={int(watchpoints.get('horizon_start_tick', 0))}",
            f"  break_reason={str(watchpoints.get('horizon_break_reason', ''))} recovery_cost_ticks={int(watchpoints.get('horizon_recovery_cost_ticks', 0))}",
            "Window:",
            f"  steps={int(window.get('steps', 0))} events={int(window.get('event_count', 0))} refinements={int(window.get('refinement_count', 0))}",
            f"  decisions={int(window.get('decision_count', 0))} reuse_rate={float(window.get('reuse_rate', 0.0)):.4f}",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "configure_learning_runtime",
    "init_learning_runtime",
    "learning_status_compact",
    "learning_status_multiline",
    "reset_learning_runtime",
    "update_learning_snapshot",
]
