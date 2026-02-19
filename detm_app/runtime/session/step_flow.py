"""Step-flow helpers for DetmSession."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from detm.runtime import api
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import PolicyDecision


def override_only_influence(base: DETMInfluence | None) -> DETMInfluence | None:
    if base is None or not base.dynamics_overrides:
        return None
    return DETMInfluence(
        symbol_id=str(base.symbol_id or "scheduled_overrides"),
        amplitude=0.0,
        dynamics_overrides={str(k): float(v) for k, v in dict(base.dynamics_overrides).items()},
    )


def merge_observables(chunks: list[api.Observables]) -> api.Observables:
    if not chunks:
        raise ValueError("chunks must not be empty")
    if len(chunks) == 1:
        return chunks[0]

    last = chunks[-1]
    events = [event for obs in chunks for event in list(obs.events)]
    merged_cost: dict[str, float] = {}
    for obs in chunks:
        for key, value in dict(obs.cost).items():
            merged_cost[str(key)] = float(merged_cost.get(str(key), 0.0) + float(value))

    return api.Observables(
        signature=last.signature,
        field_summaries=last.field_summaries,
        events=events,
        cost=merged_cost,
        quality=dict(last.quality),
    )


def ticks_to_next_stride_boundary(*, step_count: int, stride: int) -> int:
    safe_stride = max(1, int(stride))
    offset = int(step_count) % safe_stride
    if offset == 0:
        return safe_stride
    return safe_stride - offset


def run_step(
    session: Any,
    *,
    influence: DETMInfluence | None,
    n_ticks: int,
    rng: np.random.Generator | None = None,
) -> api.Observables:
    step_start = int(session.state.step_count)
    level_policy = session.config.level_policy
    runtime_window_active = bool(
        level_policy.runtime_adaptive_enabled()
        and int(step_start) < int(session._runtime_adaptive_until_step)
    )
    runtime_profile = str(session._runtime_adaptive_profile if runtime_window_active else "manual")
    policy_decision: PolicyDecision = session.config.level_policy.decide(
        step_count=int(session.state.step_count),
        requested_n_ticks=int(n_ticks),
    )
    runtime_adaptive_decision = session._runtime_adaptive_decision_for_window(
        step_start=step_start,
        requested_n_ticks=int(n_ticks),
    )
    if runtime_adaptive_decision is not None:
        policy_decision = runtime_adaptive_decision
    policy_decision = replace(
        policy_decision,
        runtime_adaptive_window_active=bool(runtime_window_active),
        runtime_adaptive_profile=str(runtime_profile),
    )
    adaptive_profile = session._adaptive_profile_for_window(step_start=step_start)
    if adaptive_profile is not None:
        policy_decision = replace(policy_decision, observability_profile=adaptive_profile)
    effective_n_ticks = int(policy_decision.effective_n_ticks)
    batch_size = max(1, int(policy_decision.batch_size))
    commit_stride = max(1, int(policy_decision.commit_stride))
    base_observability_profile = level_policy.observability_profile
    total_commit_boundaries_crossed = (
        (int(step_start) + int(effective_n_ticks)) // commit_stride
    ) - (int(step_start) // commit_stride)

    def policy_with_runtime_telemetry(
        *,
        base_decision: PolicyDecision,
        observables: api.Observables,
    ) -> PolicyDecision:
        signal_hits = level_policy.runtime_adaptive_signal_hits(
            list(observables.events),
            quality=dict(observables.quality),
            cost=dict(observables.cost),
        )
        signal_triggered = level_policy.runtime_adaptive_signal_triggered(
            list(observables.events),
            quality=dict(observables.quality),
            cost=dict(observables.cost),
            signal_hits=signal_hits,
        )
        sampled_hits, sampled, aggregate = session._runtime_adaptive_telemetry_snapshot(
            tick=int(session.state.step_count),
            signal_triggered=bool(signal_triggered),
            signal_hits=signal_hits,
            profile=str(runtime_profile),
            window_active=bool(runtime_window_active),
        )
        guard_meta = dict(base_decision.runtime_adaptive_guard)
        anti_snapshot = session._runtime_anti_goodhart_snapshot()
        if len(dict(anti_snapshot)) > 0:
            guard_meta["anti_goodhart"] = dict(anti_snapshot)
        return replace(
            base_decision,
            runtime_adaptive_window_active=bool(runtime_window_active),
            runtime_adaptive_profile=str(runtime_profile),
            runtime_adaptive_signal_triggered=bool(signal_triggered),
            runtime_adaptive_signal_hits={str(k): bool(v) for k, v in dict(sampled_hits).items()},
            runtime_adaptive_signal_hits_sampled=bool(sampled),
            runtime_adaptive_aggregate=dict(aggregate),
            runtime_adaptive_guard=dict(guard_meta),
        )

    def publish_step_event(
        *,
        publish_influence: DETMInfluence | None,
        publish_n_ticks: int,
        publish_observables: api.Observables,
        publish_policy_decision: PolicyDecision,
    ) -> None:
        blob_cache: dict[str, bytes] = {}

        def get_state_blob() -> bytes:
            if "blob" not in blob_cache:
                blob_cache["blob"] = api.serialize(session.state)
            return blob_cache["blob"]

        session.bus.publish(
            "step",
            config=session.config,
            seed=int(session.seed),
            state=session.state,
            influence=publish_influence,
            n_ticks=int(publish_n_ticks),
            requested_n_ticks=int(n_ticks),
            step_requested_n_ticks=int(n_ticks),
            step_effective_n_ticks=int(effective_n_ticks),
            observables=publish_observables,
            level_policy=session.config.level_policy,
            policy_decision=publish_policy_decision,
            get_state_blob=get_state_blob,
        )

    chunked_observables: list[api.Observables] = []
    if effective_n_ticks <= 0:
        # Preserve historical semantics: n_ticks=0 can still apply influence.
        session.state, obs = api.step(session.state, influence, effective_n_ticks, rng)
        adaptive_triggered = base_observability_profile.adaptive_signal_triggered(list(obs.events))
        if adaptive_triggered:
            adaptive_override = base_observability_profile.adaptive_profile()
            policy_decision = replace(policy_decision, observability_profile=adaptive_override)
            hold = max(0, int(base_observability_profile.adaptive_hold_ticks))
            session._adaptive_until_step = max(session._adaptive_until_step, int(session.state.step_count) + hold)
        session._update_runtime_adaptive_window_from_events(
            events=list(obs.events),
            quality=dict(obs.quality),
            cost=dict(obs.cost),
            step_after=int(session.state.step_count),
        )
        publish_step_event(
            publish_influence=influence,
            publish_n_ticks=effective_n_ticks,
            publish_observables=obs,
            publish_policy_decision=policy_with_runtime_telemetry(
                base_decision=policy_decision,
                observables=obs,
            ),
        )
        return obs

    if int(total_commit_boundaries_crossed) <= 1:
        remaining = int(effective_n_ticks)
        first_chunk = True
        while remaining > 0:
            chunk_n_ticks = min(batch_size, remaining)
            chunk_influence = influence if first_chunk else override_only_influence(influence)
            session.state, chunk_obs = api.step(session.state, chunk_influence, chunk_n_ticks, rng)
            chunked_observables.append(chunk_obs)
            remaining -= chunk_n_ticks
            first_chunk = False
        obs = merge_observables(chunked_observables)
        adaptive_triggered = base_observability_profile.adaptive_signal_triggered(list(obs.events))
        if adaptive_triggered:
            adaptive_override = base_observability_profile.adaptive_profile()
            policy_decision = replace(policy_decision, observability_profile=adaptive_override)
            hold = max(0, int(base_observability_profile.adaptive_hold_ticks))
            session._adaptive_until_step = max(session._adaptive_until_step, int(session.state.step_count) + hold)
        session._update_runtime_adaptive_window_from_events(
            events=list(obs.events),
            quality=dict(obs.quality),
            cost=dict(obs.cost),
            step_after=int(session.state.step_count),
        )
        publish_step_event(
            publish_influence=influence,
            publish_n_ticks=effective_n_ticks,
            publish_observables=obs,
            publish_policy_decision=policy_with_runtime_telemetry(
                base_decision=policy_decision,
                observables=obs,
            ),
        )
        return obs

    remaining = int(effective_n_ticks)
    first_chunk = True
    adaptive_profile_active = policy_decision.observability_profile
    adaptive_triggered_any = False
    while remaining > 0:
        step_before = int(session.state.step_count)
        boundary_ticks = ticks_to_next_stride_boundary(step_count=step_before, stride=commit_stride)
        chunk_n_ticks = min(batch_size, remaining, boundary_ticks)
        chunk_influence = influence if first_chunk else override_only_influence(influence)
        session.state, chunk_obs = api.step(session.state, chunk_influence, chunk_n_ticks, rng)
        chunked_observables.append(chunk_obs)

        if base_observability_profile.adaptive_signal_triggered(list(chunk_obs.events)):
            adaptive_profile_active = base_observability_profile.adaptive_profile()
            adaptive_triggered_any = True
        step_after = int(session.state.step_count)
        chunk_commit_boundary = chunk_n_ticks > 0 and ((step_before // commit_stride) != (step_after // commit_stride))
        chunk_policy_decision = replace(
            policy_decision,
            effective_n_ticks=int(chunk_n_ticks),
            commit_boundary_crossed=bool(chunk_commit_boundary),
            observability_profile=adaptive_profile_active,
        )
        session._update_runtime_adaptive_window_from_events(
            events=list(chunk_obs.events),
            quality=dict(chunk_obs.quality),
            cost=dict(chunk_obs.cost),
            step_after=int(step_after),
        )
        publish_step_event(
            publish_influence=chunk_influence,
            publish_n_ticks=chunk_n_ticks,
            publish_observables=chunk_obs,
            publish_policy_decision=policy_with_runtime_telemetry(
                base_decision=chunk_policy_decision,
                observables=chunk_obs,
            ),
        )

        remaining -= chunk_n_ticks
        first_chunk = False

    if adaptive_triggered_any:
        hold = max(0, int(base_observability_profile.adaptive_hold_ticks))
        session._adaptive_until_step = max(session._adaptive_until_step, int(session.state.step_count) + hold)
    obs = merge_observables(chunked_observables)
    return obs


__all__ = ["merge_observables", "override_only_influence", "run_step", "ticks_to_next_stride_boundary"]
