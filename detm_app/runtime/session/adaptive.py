"""Adaptive/runtime-adaptive policy helpers for DetmSession."""

from __future__ import annotations

from collections import deque
from typing import Any

from detm.runtime.level_policy import ObservabilityProfile, PolicyDecision

from detm_app.runtime.anti_goodhart import AntiGoodhartThresholds, evaluate_anti_goodhart


def _normalize_runtime_profile(profile: str) -> str:
    value = str(profile).strip().lower()
    if value in {"stability", "throughput", "manual"}:
        return value
    return "stability"


def _ensure_anti_goodhart_runtime(session: Any) -> dict[str, object]:
    state = getattr(session, "_anti_goodhart_runtime", None)
    if isinstance(state, dict):
        return state
    state = {
        "total_decisions": 0,
        "compatible_decisions": 0,
        "reuse_decisions": 0,
        "transferable_reuse_decisions": 0,
        "torsion_flag_decisions": 0,
        "operator_scopes": {},
        "last_panel": None,
        "last_snapshot": {},
    }
    session._anti_goodhart_runtime = state
    return state


def _operator_decisions_from_events(events: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for event in list(events):
        if str(dict(event).get("type", "")) != "refinement":
            continue
        operator = dict(dict(event).get("operator", {}))
        if len(operator) == 0:
            continue
        out.append(operator)
    return out


def _anti_goodhart_panel_from_decisions(session: Any, decisions: list[dict[str, object]]) -> dict[str, object]:
    state = _ensure_anti_goodhart_runtime(session)
    operator_scopes = state.get("operator_scopes")
    if not isinstance(operator_scopes, dict):
        operator_scopes = {}
        state["operator_scopes"] = operator_scopes

    for decision in decisions:
        state["total_decisions"] = int(state.get("total_decisions", 0)) + 1
        contract = dict(decision.get("contract", {}))
        if bool(contract.get("compatible", False)):
            state["compatible_decisions"] = int(state.get("compatible_decisions", 0)) + 1
        if bool(contract.get("torsion_flag", False)):
            state["torsion_flag_decisions"] = int(state.get("torsion_flag_decisions", 0)) + 1

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
            state["reuse_decisions"] = int(state.get("reuse_decisions", 0)) + 1
            if len(known_scopes) > 0 and scope_tuple not in known_scopes:
                state["transferable_reuse_decisions"] = int(
                    state.get("transferable_reuse_decisions", 0)
                ) + 1
        known_scopes.add(scope_tuple)
        operator_scopes[operator_id] = known_scopes

    total = max(0, int(state.get("total_decisions", 0)))
    reuse = max(0, int(state.get("reuse_decisions", 0)))
    torsion_flags = max(0, int(state.get("torsion_flag_decisions", 0)))
    return {
        "hold_rate": (
            float(int(state.get("compatible_decisions", 0))) / float(total)
            if total > 0
            else 0.0
        ),
        "operator_reuse": (float(reuse) / float(total)) if total > 0 else 0.0,
        "transferability": (
            float(int(state.get("transferable_reuse_decisions", 0))) / float(reuse)
            if reuse > 0
            else 0.0
        ),
        "torsion_flag_rate": (float(torsion_flags) / float(total)) if total > 0 else 0.0,
        "torsion_health": (1.0 - (float(torsion_flags) / float(total))) if total > 0 else 1.0,
        "counts": {
            "total_decisions": int(total),
            "compatible_decisions": int(state.get("compatible_decisions", 0)),
            "reuse_decisions": int(reuse),
            "transferable_reuse_decisions": int(state.get("transferable_reuse_decisions", 0)),
            "torsion_flag_decisions": int(torsion_flags),
        },
    }


def runtime_anti_goodhart_snapshot(session: Any) -> dict[str, object]:
    state = _ensure_anti_goodhart_runtime(session)
    snapshot = state.get("last_snapshot", {})
    return dict(snapshot) if isinstance(snapshot, dict) else {}


def reset_runtime_adaptive_state(session: Any) -> None:
    session._adaptive_until_step = 0
    session._runtime_adaptive_until_step = 0
    session._runtime_adaptive_cooldown_until_step = 0
    session._runtime_adaptive_profile = "manual"
    session._runtime_adaptive_telemetry_recent = deque()
    session._anti_goodhart_runtime = {
        "total_decisions": 0,
        "compatible_decisions": 0,
        "reuse_decisions": 0,
        "transferable_reuse_decisions": 0,
        "torsion_flag_decisions": 0,
        "operator_scopes": {},
        "last_panel": None,
        "last_snapshot": {},
    }


def adaptive_profile_for_window(
    session: Any,
    *,
    step_start: int,
) -> ObservabilityProfile | None:
    base = session.config.level_policy.observability_profile
    if not base.adaptive_enabled():
        return None
    if int(step_start) < int(session._adaptive_until_step):
        return base.adaptive_profile()
    return None


def runtime_adaptive_decision_for_window(
    session: Any,
    *,
    step_start: int,
    requested_n_ticks: int,
) -> PolicyDecision | None:
    level_policy = session.config.level_policy
    if not level_policy.runtime_adaptive_enabled():
        return None
    if int(step_start) < int(session._runtime_adaptive_until_step):
        return level_policy.decide_runtime_adaptive(
            step_count=int(step_start),
            requested_n_ticks=int(requested_n_ticks),
            profile=str(session._runtime_adaptive_profile or "manual"),
        )
    return None


def runtime_adaptive_telemetry_snapshot(
    session: Any,
    *,
    tick: int,
    signal_triggered: bool,
    signal_hits: dict[str, bool],
    profile: str,
    window_active: bool,
) -> tuple[dict[str, bool], bool, dict[str, object]]:
    level_policy = session.config.level_policy
    sample_stride = max(1, int(level_policy.runtime_adaptive_telemetry_sample_stride))
    agg_window = max(1, int(level_policy.runtime_adaptive_telemetry_aggregation_window))
    include_hits = bool(signal_triggered or (int(tick) % sample_stride == 0))

    if session._runtime_adaptive_telemetry_recent is None:
        session._runtime_adaptive_telemetry_recent = deque()
    rec = {
        "tick": int(tick),
        "profile": str(profile),
        "window_active": bool(window_active),
        "signal_triggered": bool(signal_triggered),
        "signal_hits": {str(k): bool(v) for k, v in dict(signal_hits).items()},
    }
    session._runtime_adaptive_telemetry_recent.append(rec)
    while len(session._runtime_adaptive_telemetry_recent) > agg_window:
        session._runtime_adaptive_telemetry_recent.popleft()

    profile_counts: dict[str, int] = {}
    signal_hit_counts: dict[str, int] = {}
    triggered_count = 0
    window_active_count = 0
    for item in list(session._runtime_adaptive_telemetry_recent):
        if bool(item.get("signal_triggered", False)):
            triggered_count += 1
        if bool(item.get("window_active", False)):
            window_active_count += 1
        profile_name = str(item.get("profile", "manual"))
        profile_counts[profile_name] = int(profile_counts.get(profile_name, 0) + 1)
        for key, value in dict(item.get("signal_hits", {})).items():
            if bool(value):
                signal_hit_counts[str(key)] = int(signal_hit_counts.get(str(key), 0) + 1)

    aggregate = {
        "window_size": int(len(session._runtime_adaptive_telemetry_recent)),
        "triggered_count": int(triggered_count),
        "window_active_count": int(window_active_count),
        "profile_counts": {str(k): int(v) for k, v in profile_counts.items()},
        "signal_hit_counts": {str(k): int(v) for k, v in signal_hit_counts.items()},
    }
    sampled_hits = {str(k): bool(v) for k, v in dict(signal_hits).items()} if include_hits else {}
    return sampled_hits, bool(include_hits), aggregate


def update_runtime_adaptive_window_from_events(
    session: Any,
    *,
    events: list[dict[str, object]],
    quality: dict[str, float],
    cost: dict[str, float],
    step_after: int,
) -> None:
    level_policy = session.config.level_policy
    anti_runtime = _ensure_anti_goodhart_runtime(session)
    decisions = _operator_decisions_from_events(events)
    anti_snapshot: dict[str, object] = {}
    if len(decisions) > 0:
        panel = _anti_goodhart_panel_from_decisions(session, decisions)
        previous_panel = anti_runtime.get("last_panel")
        previous = dict(previous_panel) if isinstance(previous_panel, dict) else None
        thresholds = AntiGoodhartThresholds(
            target_signal=str(level_policy.anti_goodhart_target_signal or "operator_reuse"),
            min_target_delta=float(max(0.0, level_policy.anti_goodhart_min_target_delta)),
            min_degraded_signals=int(max(1, level_policy.anti_goodhart_min_degraded_signals)),
            degradation_epsilon=float(max(0.0, level_policy.anti_goodhart_degradation_epsilon)),
        )
        preferred_profile = _normalize_runtime_profile(str(level_policy.anti_goodhart_prefer_runtime_profile))
        if bool(level_policy.anti_goodhart_enabled):
            anti_snapshot = evaluate_anti_goodhart(
                panel=panel,
                previous_panel=previous,
                thresholds=thresholds,
            )
        else:
            anti_snapshot = {
                "goodhart_flag": False,
                "target_signal": str(thresholds.target_signal),
                "target_delta": 0.0,
                "degraded_signals": [],
                "degraded_signal_count": 0,
                "thresholds": thresholds.to_dict(),
                "rule": "goodhart_flag=(d_target>min_target_delta) and (degraded_signals>=min_degraded_signals)",
                "policy_reaction": {"apply": False, "actions": []},
                "applicability": "disabled",
            }

        reaction_enabled = bool(level_policy.anti_goodhart_policy_reaction_enabled)
        reaction_apply = bool(anti_snapshot.get("goodhart_flag", False)) and reaction_enabled
        if reaction_apply:
            if preferred_profile == "throughput":
                profile_action = "prefer_throughput_runtime_profile"
            elif preferred_profile == "manual":
                profile_action = "prefer_manual_runtime_profile"
            else:
                profile_action = "prefer_stability_runtime_profile"
            anti_snapshot["policy_reaction"] = {
                "apply": True,
                "actions": [
                    "downweight_target_signal",
                    "enable_extended_outerfields_audit",
                    profile_action,
                ],
            }
        else:
            anti_snapshot["policy_reaction"] = {"apply": False, "actions": []}
        anti_snapshot["policy_reaction_enabled"] = bool(reaction_enabled)
        anti_snapshot["preferred_runtime_profile"] = str(preferred_profile)
        anti_snapshot["runtime_profile_applied"] = False
        anti_runtime["last_panel"] = dict(panel)

    if int(step_after) > int(session._runtime_adaptive_cooldown_until_step):
        signal_hits = level_policy.runtime_adaptive_signal_hits(events, quality=quality, cost=cost)
        if level_policy.runtime_adaptive_signal_triggered(
            events,
            quality=quality,
            cost=cost,
            signal_hits=signal_hits,
        ):
            session._runtime_adaptive_profile = level_policy.runtime_adaptive_profile_for_signal_hits(signal_hits)
            hold = max(0, int(level_policy.runtime_adaptive_hold_ticks))
            session._runtime_adaptive_until_step = max(
                int(session._runtime_adaptive_until_step),
                int(step_after) + hold,
            )
            cooldown = max(0, int(level_policy.runtime_adaptive_cooldown_ticks))
            session._runtime_adaptive_cooldown_until_step = max(
                int(session._runtime_adaptive_cooldown_until_step),
                int(step_after) + cooldown,
            )

    if bool(dict(anti_snapshot.get("policy_reaction", {})).get("apply", False)):
        if bool(level_policy.runtime_adaptive_enabled()):
            preferred_profile = _normalize_runtime_profile(
                str(anti_snapshot.get("preferred_runtime_profile", "stability"))
            )
            session._runtime_adaptive_profile = preferred_profile
            reaction_hold = max(1, int(level_policy.runtime_adaptive_hold_ticks))
            session._runtime_adaptive_until_step = max(
                int(session._runtime_adaptive_until_step),
                int(step_after) + reaction_hold,
            )
            anti_snapshot["runtime_profile_applied"] = True
        else:
            anti_snapshot["runtime_profile_applied"] = False

    anti_runtime["last_snapshot"] = dict(anti_snapshot)


__all__ = [
    "adaptive_profile_for_window",
    "reset_runtime_adaptive_state",
    "runtime_anti_goodhart_snapshot",
    "runtime_adaptive_decision_for_window",
    "runtime_adaptive_telemetry_snapshot",
    "update_runtime_adaptive_window_from_events",
]
