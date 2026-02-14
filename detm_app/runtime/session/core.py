"""Session wrapper around the public runtime API."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional

import numpy as np

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import ObservabilityProfile, PolicyDecision
from detm.runtime.state import DETMState

from detm_app.runtime.bus import EventBus
from detm_app.runtime.session.adaptive import (
    adaptive_profile_for_window as _adaptive_profile_for_window_flow,
    reset_runtime_adaptive_state as _reset_runtime_adaptive_state_flow,
    runtime_adaptive_decision_for_window as _runtime_adaptive_decision_for_window_flow,
    runtime_adaptive_telemetry_snapshot as _runtime_adaptive_telemetry_snapshot_flow,
    update_runtime_adaptive_window_from_events as _update_runtime_adaptive_window_from_events_flow,
)
from detm_app.runtime.session.step_flow import run_step as _run_step_flow


@dataclass
class DetmSession:
    """A single DETM episode/session."""

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
        _reset_runtime_adaptive_state_flow(self)
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
        return _run_step_flow(self, influence=influence, n_ticks=int(n_ticks), rng=rng)

    def _adaptive_profile_for_window(self, *, step_start: int) -> ObservabilityProfile | None:
        return _adaptive_profile_for_window_flow(self, step_start=step_start)

    def _runtime_adaptive_decision_for_window(
        self,
        *,
        step_start: int,
        requested_n_ticks: int,
    ) -> PolicyDecision | None:
        return _runtime_adaptive_decision_for_window_flow(
            self,
            step_start=step_start,
            requested_n_ticks=requested_n_ticks,
        )

    def _runtime_adaptive_telemetry_snapshot(
        self,
        *,
        tick: int,
        signal_triggered: bool,
        signal_hits: dict[str, bool],
        profile: str,
        window_active: bool,
    ) -> tuple[dict[str, bool], bool, dict[str, object]]:
        return _runtime_adaptive_telemetry_snapshot_flow(
            self,
            tick=tick,
            signal_triggered=signal_triggered,
            signal_hits=signal_hits,
            profile=profile,
            window_active=window_active,
        )

    def _update_runtime_adaptive_window_from_events(
        self,
        *,
        events: list[dict[str, object]],
        quality: dict[str, float],
        cost: dict[str, float],
        step_after: int,
    ) -> None:
        _update_runtime_adaptive_window_from_events_flow(
            self,
            events=events,
            quality=quality,
            cost=cost,
            step_after=step_after,
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
