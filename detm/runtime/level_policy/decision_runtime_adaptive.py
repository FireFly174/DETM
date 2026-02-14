"""Runtime-adaptive decision composition for level policy."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from detm.runtime.level_policy.decision_guard import apply_runtime_adaptive_guards


def decide_runtime_adaptive_policy(
    policy: Any,
    *,
    step_count: int,
    requested_n_ticks: int,
    profile: str = "manual",
):
    profile_name = str(profile).strip().lower()
    if bool(policy.runtime_adaptive_auto_profile) and profile_name in {"stability", "throughput"}:
        if profile_name == "stability":
            microsteps_delta = int(policy.runtime_adaptive_stability_microsteps_delta)
            batch_delta = int(policy.runtime_adaptive_stability_batch_size_delta)
            commit_stride_delta = int(policy.runtime_adaptive_stability_commit_stride_delta)
        else:
            microsteps_delta = int(policy.runtime_adaptive_throughput_microsteps_delta)
            batch_delta = int(policy.runtime_adaptive_throughput_batch_size_delta)
            commit_stride_delta = int(policy.runtime_adaptive_throughput_commit_stride_delta)
        if microsteps_delta != 0 or batch_delta != 0 or commit_stride_delta != 0:
            microsteps = max(1, int(policy.microsteps_per_global_tick) + microsteps_delta)
            batch_size = max(1, int(policy.batch_size) + batch_delta)
            commit_stride = max(1, int(policy.commit_stride) + commit_stride_delta)
            guarded_microsteps, guarded_batch, guarded_stride, guard_meta = apply_runtime_adaptive_guards(
                policy,
                microsteps_per_global_tick=int(microsteps),
                batch_size=int(batch_size),
                commit_stride=int(commit_stride),
            )
            decision = policy._decide_with_values(
                step_count=step_count,
                requested_n_ticks=requested_n_ticks,
                microsteps_per_global_tick=int(guarded_microsteps),
                batch_size=int(guarded_batch),
                commit_stride=int(guarded_stride),
            )
            return replace(decision, runtime_adaptive_guard=dict(guard_meta))

    use_deltas = bool(policy.runtime_adaptive_use_deltas) and (
        int(policy.runtime_adaptive_microsteps_delta) != 0
        or int(policy.runtime_adaptive_batch_size_delta) != 0
        or int(policy.runtime_adaptive_commit_stride_delta) != 0
    )
    if use_deltas:
        microsteps = max(1, int(policy.microsteps_per_global_tick) + int(policy.runtime_adaptive_microsteps_delta))
        batch_size = max(1, int(policy.batch_size) + int(policy.runtime_adaptive_batch_size_delta))
        commit_stride = max(1, int(policy.commit_stride) + int(policy.runtime_adaptive_commit_stride_delta))
        guarded_microsteps, guarded_batch, guarded_stride, guard_meta = apply_runtime_adaptive_guards(
            policy,
            microsteps_per_global_tick=int(microsteps),
            batch_size=int(batch_size),
            commit_stride=int(commit_stride),
        )
        decision = policy._decide_with_values(
            step_count=step_count,
            requested_n_ticks=requested_n_ticks,
            microsteps_per_global_tick=int(guarded_microsteps),
            batch_size=int(guarded_batch),
            commit_stride=int(guarded_stride),
        )
        return replace(decision, runtime_adaptive_guard=dict(guard_meta))

    guarded_microsteps, guarded_batch, guarded_stride, guard_meta = apply_runtime_adaptive_guards(
        policy,
        microsteps_per_global_tick=(
            int(policy.runtime_adaptive_microsteps_per_global_tick)
            if int(policy.runtime_adaptive_microsteps_per_global_tick) > 0
            else int(policy.microsteps_per_global_tick)
        ),
        batch_size=(
            int(policy.runtime_adaptive_batch_size)
            if int(policy.runtime_adaptive_batch_size) > 0
            else int(policy.batch_size)
        ),
        commit_stride=(
            int(policy.runtime_adaptive_commit_stride)
            if int(policy.runtime_adaptive_commit_stride) > 0
            else int(policy.commit_stride)
        ),
    )
    decision = policy._decide_with_values(
        step_count=step_count,
        requested_n_ticks=requested_n_ticks,
        microsteps_per_global_tick=int(guarded_microsteps),
        batch_size=int(guarded_batch),
        commit_stride=int(guarded_stride),
    )
    return replace(decision, runtime_adaptive_guard=dict(guard_meta))


__all__ = ["decide_runtime_adaptive_policy"]
