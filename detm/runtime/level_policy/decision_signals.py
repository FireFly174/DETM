"""Signal predicates for runtime-adaptive level policy."""

from __future__ import annotations

from typing import Any, Dict, Tuple


def runtime_adaptive_enabled(policy: Any) -> bool:
    has_signal_criteria = bool(
        len(tuple(policy.runtime_adaptive_signal_event_types)) > 0
        or float(policy.runtime_adaptive_quality_oscillation_threshold) > 0.0
        or float(policy.runtime_adaptive_quality_jitter_threshold) > 0.0
        or float(policy.runtime_adaptive_cost_cpu_time_ms_threshold) > 0.0
    )
    has_profile_deltas = bool(
        bool(policy.runtime_adaptive_auto_profile)
        and (
            int(policy.runtime_adaptive_stability_microsteps_delta) != 0
            or int(policy.runtime_adaptive_stability_batch_size_delta) != 0
            or int(policy.runtime_adaptive_stability_commit_stride_delta) != 0
            or int(policy.runtime_adaptive_throughput_microsteps_delta) != 0
            or int(policy.runtime_adaptive_throughput_batch_size_delta) != 0
            or int(policy.runtime_adaptive_throughput_commit_stride_delta) != 0
        )
    )
    has_delta_overrides = bool(
        bool(policy.runtime_adaptive_use_deltas)
        and (
            int(policy.runtime_adaptive_microsteps_delta) != 0
            or int(policy.runtime_adaptive_batch_size_delta) != 0
            or int(policy.runtime_adaptive_commit_stride_delta) != 0
        )
    )
    has_absolute_overrides = bool(
        int(policy.runtime_adaptive_microsteps_per_global_tick) > 0
        or int(policy.runtime_adaptive_batch_size) > 0
        or int(policy.runtime_adaptive_commit_stride) > 0
    )
    return bool(has_signal_criteria and (has_profile_deltas or has_delta_overrides or has_absolute_overrides))


def allows_runtime_adaptive_signal(policy: Any, event_type: str) -> bool:
    if "*" in tuple(policy.runtime_adaptive_signal_event_types):
        return True
    return str(event_type) in set(policy.runtime_adaptive_signal_event_types)


def runtime_adaptive_signal_hits(
    policy: Any,
    events: Tuple[Dict[str, Any], ...] | list[Dict[str, Any]],
    *,
    quality: Dict[str, Any] | None = None,
    cost: Dict[str, Any] | None = None,
) -> Dict[str, bool]:
    quality = dict(quality or {})
    cost = dict(cost or {})
    event_types = [str(dict(event).get("type", "")) for event in list(events)]

    event_hit = False
    if len(tuple(policy.runtime_adaptive_signal_event_types)) > 0:
        event_hit = any(allows_runtime_adaptive_signal(policy, event_type) for event_type in event_types)
    oscillation_hit = False
    if float(policy.runtime_adaptive_quality_oscillation_threshold) > 0.0:
        oscillation = float(quality.get("oscillation_score", 0.0) or 0.0)
        oscillation_hit = bool(oscillation >= float(policy.runtime_adaptive_quality_oscillation_threshold))
    jitter_hit = False
    if float(policy.runtime_adaptive_quality_jitter_threshold) > 0.0:
        jitter = float(quality.get("jitter_signature", 0.0) or 0.0)
        jitter_hit = bool(jitter >= float(policy.runtime_adaptive_quality_jitter_threshold))
    cpu_time_hit = False
    if float(policy.runtime_adaptive_cost_cpu_time_ms_threshold) > 0.0:
        cpu_time_ms = float(cost.get("cpu_time_ms", 0.0) or 0.0)
        cpu_time_hit = bool(cpu_time_ms >= float(policy.runtime_adaptive_cost_cpu_time_ms_threshold))

    return {
        "event": bool(event_hit),
        "quality_oscillation": bool(oscillation_hit),
        "quality_jitter": bool(jitter_hit),
        "quality": bool(oscillation_hit or jitter_hit),
        "cost_cpu_time": bool(cpu_time_hit),
    }


def runtime_adaptive_signal_triggered(
    policy: Any,
    events: Tuple[Dict[str, Any], ...] | list[Dict[str, Any]],
    *,
    quality: Dict[str, Any] | None = None,
    cost: Dict[str, Any] | None = None,
    signal_hits: Dict[str, bool] | None = None,
) -> bool:
    if not runtime_adaptive_enabled(policy):
        return False
    hits = dict(signal_hits or {})
    if len(hits) == 0:
        hits = runtime_adaptive_signal_hits(policy, events, quality=quality, cost=cost)

    configured_hits = []
    if len(tuple(policy.runtime_adaptive_signal_event_types)) > 0:
        configured_hits.append(bool(hits.get("event", False)))
    if float(policy.runtime_adaptive_quality_oscillation_threshold) > 0.0:
        configured_hits.append(bool(hits.get("quality_oscillation", False)))
    if float(policy.runtime_adaptive_quality_jitter_threshold) > 0.0:
        configured_hits.append(bool(hits.get("quality_jitter", False)))
    if float(policy.runtime_adaptive_cost_cpu_time_ms_threshold) > 0.0:
        configured_hits.append(bool(hits.get("cost_cpu_time", False)))

    if len(configured_hits) == 0:
        return False
    min_signals = max(1, int(policy.runtime_adaptive_min_signals))
    return int(sum(1 for hit in configured_hits if bool(hit))) >= min_signals


def runtime_adaptive_profile_for_signal_hits(policy: Any, signal_hits: Dict[str, bool] | None = None) -> str:
    if not bool(policy.runtime_adaptive_auto_profile):
        return "manual"
    hits = dict(signal_hits or {})
    if bool(hits.get("cost_cpu_time", False)):
        return "throughput"
    if bool(hits.get("event", False)) or bool(hits.get("quality", False)):
        return "stability"
    return "manual"


__all__ = [
    "allows_runtime_adaptive_signal",
    "runtime_adaptive_enabled",
    "runtime_adaptive_profile_for_signal_hits",
    "runtime_adaptive_signal_hits",
    "runtime_adaptive_signal_triggered",
]
