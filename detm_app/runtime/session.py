"""Session wrapper around the public runtime API."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Optional

import numpy as np

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import ObservabilityProfile, PolicyDecision
from detm.runtime.state import DETMState

from detm_app.runtime.bus import EventBus


def _override_only_influence(base: DETMInfluence | None) -> DETMInfluence | None:
    if base is None or not base.dynamics_overrides:
        return None
    return DETMInfluence(
        symbol_id=str(base.symbol_id or "scheduled_overrides"),
        amplitude=0.0,
        dynamics_overrides={str(k): float(v) for k, v in dict(base.dynamics_overrides).items()},
    )


def _merge_observables(chunks: list[api.Observables]) -> api.Observables:
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


def _ticks_to_next_stride_boundary(*, step_count: int, stride: int) -> int:
    safe_stride = max(1, int(stride))
    offset = int(step_count) % safe_stride
    if offset == 0:
        return safe_stride
    return safe_stride - offset


@dataclass
class DetmSession:
    """A single DETM episode/session.

    This object owns the current `DETMState` and provides `reset/step/digest`
    while emitting events to an attached EventBus.
    """

    config: DETMConfig
    seed: int
    bus: EventBus
    state: DETMState
    _adaptive_until_step: int = 0
    _runtime_adaptive_until_step: int = 0
    _runtime_adaptive_cooldown_until_step: int = 0
    _runtime_adaptive_profile: str = "manual"
    _runtime_adaptive_telemetry_recent: deque[dict[str, object]] = None  # type: ignore[assignment]

    @classmethod
    def create(cls, config: DETMConfig, seed: int, *, bus: Optional[EventBus] = None) -> "DetmSession":
        bus = bus or EventBus()
        state = api.reset(config, seed)
        blob_cache: dict[str, bytes] = {}

        def get_state_blob() -> bytes:
            if "blob" not in blob_cache:
                blob_cache["blob"] = api.serialize(state)
            return blob_cache["blob"]

        bus.publish("reset", config=config, seed=int(seed), state=state, get_state_blob=get_state_blob)
        return cls(
            config=config,
            seed=int(seed),
            bus=bus,
            state=state,
            _runtime_adaptive_telemetry_recent=deque(),
        )

    def reset(self, *, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.seed = int(seed)
        self.state = api.reset(self.config, self.seed)
        self._adaptive_until_step = 0
        self._runtime_adaptive_until_step = 0
        self._runtime_adaptive_cooldown_until_step = 0
        self._runtime_adaptive_profile = "manual"
        self._runtime_adaptive_telemetry_recent = deque()
        blob_cache: dict[str, bytes] = {}

        def get_state_blob() -> bytes:
            if "blob" not in blob_cache:
                blob_cache["blob"] = api.serialize(self.state)
            return blob_cache["blob"]

        self.bus.publish("reset", config=self.config, seed=int(self.seed), state=self.state, get_state_blob=get_state_blob)

    def step(
        self,
        influence: DETMInfluence | None,
        n_ticks: int,
        rng: np.random.Generator | None = None,
    ) -> api.Observables:
        step_start = int(self.state.step_count)
        level_policy = self.config.level_policy
        runtime_window_active = bool(
            level_policy.runtime_adaptive_enabled()
            and int(step_start) < int(self._runtime_adaptive_until_step)
        )
        runtime_profile = str(self._runtime_adaptive_profile if runtime_window_active else "manual")
        policy_decision: PolicyDecision = self.config.level_policy.decide(
            step_count=int(self.state.step_count),
            requested_n_ticks=int(n_ticks),
        )
        runtime_adaptive_decision = self._runtime_adaptive_decision_for_window(
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
        adaptive_profile = self._adaptive_profile_for_window(step_start=step_start)
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
            sampled_hits, sampled, aggregate = self._runtime_adaptive_telemetry_snapshot(
                tick=int(self.state.step_count),
                signal_triggered=bool(signal_triggered),
                signal_hits=signal_hits,
                profile=str(runtime_profile),
                window_active=bool(runtime_window_active),
            )
            return replace(
                base_decision,
                runtime_adaptive_window_active=bool(runtime_window_active),
                runtime_adaptive_profile=str(runtime_profile),
                runtime_adaptive_signal_triggered=bool(signal_triggered),
                runtime_adaptive_signal_hits={str(k): bool(v) for k, v in dict(sampled_hits).items()},
                runtime_adaptive_signal_hits_sampled=bool(sampled),
                runtime_adaptive_aggregate=dict(aggregate),
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
                    blob_cache["blob"] = api.serialize(self.state)
                return blob_cache["blob"]

            self.bus.publish(
                "step",
                config=self.config,
                seed=int(self.seed),
                state=self.state,
                influence=publish_influence,
                n_ticks=int(publish_n_ticks),
                requested_n_ticks=int(n_ticks),
                step_requested_n_ticks=int(n_ticks),
                step_effective_n_ticks=int(effective_n_ticks),
                observables=publish_observables,
                level_policy=self.config.level_policy,
                policy_decision=publish_policy_decision,
                get_state_blob=get_state_blob,
            )

        chunked_observables: list[api.Observables] = []
        if effective_n_ticks <= 0:
            # Preserve historical semantics: n_ticks=0 can still apply influence.
            self.state, obs = api.step(self.state, influence, effective_n_ticks, rng)
            adaptive_triggered = base_observability_profile.adaptive_signal_triggered(list(obs.events))
            if adaptive_triggered:
                adaptive_override = base_observability_profile.adaptive_profile()
                policy_decision = replace(policy_decision, observability_profile=adaptive_override)
                hold = max(0, int(base_observability_profile.adaptive_hold_ticks))
                self._adaptive_until_step = max(self._adaptive_until_step, int(self.state.step_count) + hold)
            publish_step_event(
                publish_influence=influence,
                publish_n_ticks=effective_n_ticks,
                publish_observables=obs,
                publish_policy_decision=policy_with_runtime_telemetry(
                    base_decision=policy_decision,
                    observables=obs,
                ),
            )
            self._update_runtime_adaptive_window_from_events(
                events=list(obs.events),
                quality=dict(obs.quality),
                cost=dict(obs.cost),
                step_after=int(self.state.step_count),
            )
            return obs

        if int(total_commit_boundaries_crossed) <= 1:
            remaining = int(effective_n_ticks)
            first_chunk = True
            while remaining > 0:
                chunk_n_ticks = min(batch_size, remaining)
                chunk_influence = influence if first_chunk else _override_only_influence(influence)
                self.state, chunk_obs = api.step(self.state, chunk_influence, chunk_n_ticks, rng)
                chunked_observables.append(chunk_obs)
                remaining -= chunk_n_ticks
                first_chunk = False
            obs = _merge_observables(chunked_observables)
            adaptive_triggered = base_observability_profile.adaptive_signal_triggered(list(obs.events))
            if adaptive_triggered:
                adaptive_override = base_observability_profile.adaptive_profile()
                policy_decision = replace(policy_decision, observability_profile=adaptive_override)
                hold = max(0, int(base_observability_profile.adaptive_hold_ticks))
                self._adaptive_until_step = max(self._adaptive_until_step, int(self.state.step_count) + hold)
            publish_step_event(
                publish_influence=influence,
                publish_n_ticks=effective_n_ticks,
                publish_observables=obs,
                publish_policy_decision=policy_with_runtime_telemetry(
                    base_decision=policy_decision,
                    observables=obs,
                ),
            )
            self._update_runtime_adaptive_window_from_events(
                events=list(obs.events),
                quality=dict(obs.quality),
                cost=dict(obs.cost),
                step_after=int(self.state.step_count),
            )
            return obs

        remaining = int(effective_n_ticks)
        first_chunk = True
        adaptive_profile_active = policy_decision.observability_profile
        adaptive_triggered_any = False
        while remaining > 0:
            step_before = int(self.state.step_count)
            boundary_ticks = _ticks_to_next_stride_boundary(step_count=step_before, stride=commit_stride)
            chunk_n_ticks = min(batch_size, remaining, boundary_ticks)
            chunk_influence = influence if first_chunk else _override_only_influence(influence)
            self.state, chunk_obs = api.step(self.state, chunk_influence, chunk_n_ticks, rng)
            chunked_observables.append(chunk_obs)

            if base_observability_profile.adaptive_signal_triggered(list(chunk_obs.events)):
                adaptive_profile_active = base_observability_profile.adaptive_profile()
                adaptive_triggered_any = True
            step_after = int(self.state.step_count)
            chunk_commit_boundary = chunk_n_ticks > 0 and ((step_before // commit_stride) != (step_after // commit_stride))
            chunk_policy_decision = replace(
                policy_decision,
                effective_n_ticks=int(chunk_n_ticks),
                commit_boundary_crossed=bool(chunk_commit_boundary),
                observability_profile=adaptive_profile_active,
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
            self._adaptive_until_step = max(self._adaptive_until_step, int(self.state.step_count) + hold)
        obs = _merge_observables(chunked_observables)
        self._update_runtime_adaptive_window_from_events(
            events=list(obs.events),
            quality=dict(obs.quality),
            cost=dict(obs.cost),
            step_after=int(self.state.step_count),
        )
        return obs

    def _adaptive_profile_for_window(self, *, step_start: int) -> ObservabilityProfile | None:
        base = self.config.level_policy.observability_profile
        if not base.adaptive_enabled():
            return None
        if int(step_start) < int(self._adaptive_until_step):
            return base.adaptive_profile()
        return None

    def _runtime_adaptive_decision_for_window(
        self,
        *,
        step_start: int,
        requested_n_ticks: int,
    ) -> PolicyDecision | None:
        level_policy = self.config.level_policy
        if not level_policy.runtime_adaptive_enabled():
            return None
        if int(step_start) < int(self._runtime_adaptive_until_step):
            return level_policy.decide_runtime_adaptive(
                step_count=int(step_start),
                requested_n_ticks=int(requested_n_ticks),
                profile=str(self._runtime_adaptive_profile or "manual"),
            )
        return None

    def _runtime_adaptive_telemetry_snapshot(
        self,
        *,
        tick: int,
        signal_triggered: bool,
        signal_hits: dict[str, bool],
        profile: str,
        window_active: bool,
    ) -> tuple[dict[str, bool], bool, dict[str, object]]:
        level_policy = self.config.level_policy
        sample_stride = max(1, int(level_policy.runtime_adaptive_telemetry_sample_stride))
        agg_window = max(1, int(level_policy.runtime_adaptive_telemetry_aggregation_window))
        include_hits = bool(signal_triggered or (int(tick) % sample_stride == 0))

        if self._runtime_adaptive_telemetry_recent is None:
            self._runtime_adaptive_telemetry_recent = deque()
        rec = {
            "tick": int(tick),
            "profile": str(profile),
            "window_active": bool(window_active),
            "signal_triggered": bool(signal_triggered),
            "signal_hits": {str(k): bool(v) for k, v in dict(signal_hits).items()},
        }
        self._runtime_adaptive_telemetry_recent.append(rec)
        while len(self._runtime_adaptive_telemetry_recent) > agg_window:
            self._runtime_adaptive_telemetry_recent.popleft()

        profile_counts: dict[str, int] = {}
        signal_hit_counts: dict[str, int] = {}
        triggered_count = 0
        window_active_count = 0
        for item in list(self._runtime_adaptive_telemetry_recent):
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
            "window_size": int(len(self._runtime_adaptive_telemetry_recent)),
            "triggered_count": int(triggered_count),
            "window_active_count": int(window_active_count),
            "profile_counts": {str(k): int(v) for k, v in profile_counts.items()},
            "signal_hit_counts": {str(k): int(v) for k, v in signal_hit_counts.items()},
        }
        sampled_hits = {str(k): bool(v) for k, v in dict(signal_hits).items()} if include_hits else {}
        return sampled_hits, bool(include_hits), aggregate

    def _update_runtime_adaptive_window_from_events(
        self,
        *,
        events: list[dict[str, object]],
        quality: dict[str, float],
        cost: dict[str, float],
        step_after: int,
    ) -> None:
        level_policy = self.config.level_policy
        if int(step_after) <= int(self._runtime_adaptive_cooldown_until_step):
            return
        signal_hits = level_policy.runtime_adaptive_signal_hits(events, quality=quality, cost=cost)
        if not level_policy.runtime_adaptive_signal_triggered(
            events,
            quality=quality,
            cost=cost,
            signal_hits=signal_hits,
        ):
            return
        self._runtime_adaptive_profile = level_policy.runtime_adaptive_profile_for_signal_hits(signal_hits)
        hold = max(0, int(level_policy.runtime_adaptive_hold_ticks))
        self._runtime_adaptive_until_step = max(
            int(self._runtime_adaptive_until_step),
            int(step_after) + hold,
        )
        cooldown = max(0, int(level_policy.runtime_adaptive_cooldown_ticks))
        self._runtime_adaptive_cooldown_until_step = max(
            int(self._runtime_adaptive_cooldown_until_step),
            int(step_after) + cooldown,
        )

    def digest(self) -> api.DETMSignature:
        sig = api.digest(self.state)
        blob_cache: dict[str, bytes] = {}

        def get_state_blob() -> bytes:
            if "blob" not in blob_cache:
                blob_cache["blob"] = api.serialize(self.state)
            return blob_cache["blob"]

        self.bus.publish(
            "digest",
            config=self.config,
            seed=int(self.seed),
            state=self.state,
            signature=sig,
            get_state_blob=get_state_blob,
        )
        return sig

    def close(self) -> None:
        blob_cache: dict[str, bytes] = {}

        def get_state_blob() -> bytes:
            if "blob" not in blob_cache:
                blob_cache["blob"] = api.serialize(self.state)
            return blob_cache["blob"]

        self.bus.publish("close", config=self.config, seed=int(self.seed), state=self.state, get_state_blob=get_state_blob)

__all__ = ["DetmSession"]
