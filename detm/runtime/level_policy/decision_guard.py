"""Guard bounds and clamping for runtime-adaptive policy candidates."""

from __future__ import annotations

from typing import Any, Dict


def runtime_adaptive_guard_bounds(policy: Any) -> Dict[str, tuple[int, int | None]]:
    micro_min = max(1, int(policy.runtime_adaptive_guard_microsteps_min))
    batch_min = max(1, int(policy.runtime_adaptive_guard_batch_size_min))
    commit_min = max(1, int(policy.runtime_adaptive_guard_commit_stride_min))
    micro_max_raw = max(0, int(policy.runtime_adaptive_guard_microsteps_max))
    batch_max_raw = max(0, int(policy.runtime_adaptive_guard_batch_size_max))
    commit_max_raw = max(0, int(policy.runtime_adaptive_guard_commit_stride_max))
    micro_max = None if micro_max_raw <= 0 else max(micro_min, micro_max_raw)
    batch_max = None if batch_max_raw <= 0 else max(batch_min, batch_max_raw)
    commit_max = None if commit_max_raw <= 0 else max(commit_min, commit_max_raw)
    return {
        "microsteps_per_global_tick": (micro_min, micro_max),
        "batch_size": (batch_min, batch_max),
        "commit_stride": (commit_min, commit_max),
    }


def apply_runtime_adaptive_guards(
    policy: Any,
    *,
    microsteps_per_global_tick: int,
    batch_size: int,
    commit_stride: int,
) -> tuple[int, int, int, Dict[str, Any]]:
    requested = {
        "microsteps_per_global_tick": max(1, int(microsteps_per_global_tick)),
        "batch_size": max(1, int(batch_size)),
        "commit_stride": max(1, int(commit_stride)),
    }
    bounds = runtime_adaptive_guard_bounds(policy)
    violations: list[str] = []
    for key, value in requested.items():
        low, high = bounds[str(key)]
        if int(value) < int(low):
            violations.append(f"{key}<min")
        if high is not None and int(value) > int(high):
            violations.append(f"{key}>max")

    reject = bool(policy.runtime_adaptive_guard_reject_unsafe) and len(violations) > 0
    if reject:
        applied = {
            "microsteps_per_global_tick": max(1, int(policy.microsteps_per_global_tick)),
            "batch_size": max(1, int(policy.batch_size)),
            "commit_stride": max(1, int(policy.commit_stride)),
        }
        return (
            int(applied["microsteps_per_global_tick"]),
            int(applied["batch_size"]),
            int(applied["commit_stride"]),
            {
                "enabled": True,
                "rejected": True,
                "violations": list(violations),
                "requested": dict(requested),
                "applied": dict(applied),
                "clamped": {},
            },
        )

    clamped: Dict[str, int] = {}
    applied = dict(requested)
    for key, value in requested.items():
        low, high = bounds[str(key)]
        out = max(int(low), int(value))
        if high is not None:
            out = min(int(high), int(out))
        applied[str(key)] = int(out)
        if int(out) != int(value):
            clamped[str(key)] = int(out)

    return (
        int(applied["microsteps_per_global_tick"]),
        int(applied["batch_size"]),
        int(applied["commit_stride"]),
        {
            "enabled": True,
            "rejected": False,
            "violations": list(violations),
            "requested": dict(requested),
            "applied": dict(applied),
            "clamped": dict(clamped),
        },
    )


__all__ = ["apply_runtime_adaptive_guards", "runtime_adaptive_guard_bounds"]
