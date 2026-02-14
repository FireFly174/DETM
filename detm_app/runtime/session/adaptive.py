"""Adaptive/runtime-adaptive policy helpers for DetmSession."""

from __future__ import annotations

from collections import deque
from typing import Any

from detm.runtime.level_policy import ObservabilityProfile, PolicyDecision


def reset_runtime_adaptive_state(session: Any) -> None:
    session._adaptive_until_step = 0
    session._runtime_adaptive_until_step = 0
    session._runtime_adaptive_cooldown_until_step = 0
    session._runtime_adaptive_profile = "manual"
    session._runtime_adaptive_telemetry_recent = deque()


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
    if int(step_after) <= int(session._runtime_adaptive_cooldown_until_step):
        return
    signal_hits = level_policy.runtime_adaptive_signal_hits(events, quality=quality, cost=cost)
    if not level_policy.runtime_adaptive_signal_triggered(
        events,
        quality=quality,
        cost=cost,
        signal_hits=signal_hits,
    ):
        return
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


__all__ = [
    "adaptive_profile_for_window",
    "reset_runtime_adaptive_state",
    "runtime_adaptive_decision_for_window",
    "runtime_adaptive_telemetry_snapshot",
    "update_runtime_adaptive_window_from_events",
]
