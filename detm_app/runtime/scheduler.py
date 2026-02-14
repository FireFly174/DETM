"""Tick-driven scheduler built on top of the EventBus.

Design goals:
- Deterministic: scheduling and dispatch order are stable.
- Composable: the scheduler is *not* part of core L0 dynamics.
- Tick-driven: everything is expressed in integer ticks to match the external
  orchestrator (ACGS) model.

The scheduler publishes:
- `tick` events (every global tick)
- `signal` events when scheduled influences fire

It can be used standalone (to only dispatch events) or paired with DetmSession
via `TickRunner` which advances the simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from detm.runtime.influence import DETMInfluence, InfluenceApplication, apply_influence

from detm_app.runtime.bus import EventBus
from detm_app.runtime.session import DetmSession


@dataclass(frozen=True, order=True)
class ScheduledItem:
    tick: int
    order: int
    kind: str = field(compare=False)
    payload: Dict[str, Any] = field(compare=False)


class TickScheduler:
    """Deterministic scheduler that dispatches scheduled items on ticks."""

    def __init__(self, *, bus: Optional[EventBus] = None, tick0: int = 0) -> None:
        self.bus = bus or EventBus()
        self.tick = int(tick0)
        self._counter = 0
        self._queue: List[ScheduledItem] = []

    def schedule_influence(self, tick: int, influence: DETMInfluence) -> None:
        self._push(int(tick), "influence", {"influence": influence})

    def schedule_callback(self, tick: int, fn: Callable[[], None], *, name: str = "callback") -> None:
        self._push(int(tick), "callback", {"fn": fn, "name": str(name)})

    def _push(self, tick: int, kind: str, payload: Dict[str, Any]) -> None:
        item = ScheduledItem(tick=tick, order=self._counter, kind=str(kind), payload=dict(payload))
        self._counter += 1
        self._queue.append(item)
        self._queue.sort()  # small N; deterministic

    def peek_next_tick(self) -> Optional[int]:
        if not self._queue:
            return None
        return int(self._queue[0].tick)

    def pop_due(self, tick: int) -> List[ScheduledItem]:
        tick = int(tick)
        due: List[ScheduledItem] = []
        rest: List[ScheduledItem] = []
        for item in self._queue:
            if item.tick == tick:
                due.append(item)
            else:
                rest.append(item)
        self._queue = rest
        return due

    def step_tick(self) -> List[ScheduledItem]:
        """Advance the scheduler by one tick and dispatch scheduled items."""

        current = int(self.tick)
        self.bus.publish("tick", tick=current)
        due = self.pop_due(current)

        for item in due:
            if item.kind == "influence":
                self.bus.publish("signal", tick=current, influence=item.payload["influence"])
            elif item.kind == "callback":
                fn = item.payload.get("fn")
                if callable(fn):
                    fn()
                self.bus.publish("signal", tick=current, name=item.payload.get("name", "callback"))
            else:
                self.bus.publish("signal", tick=current, kind=item.kind, payload=item.payload)

        self.tick = current + 1
        return due


class TickRunner:
    """Convenience: couple a DetmSession to a TickScheduler.

    Semantics:
    - For each global tick, apply all due influences without advancing time
      (n_ticks=0), then advance the simulation by 1 tick.
    - Uses the session RNG for deterministic influence noise.
    """

    def __init__(self, session: DetmSession, scheduler: TickScheduler) -> None:
        self.session = session
        # Unify the clock and event stream: Scheduler is the "time spine" for the same bus.
        scheduler.bus = session.bus
        self.scheduler = scheduler
        self._clock_initialized = False

    @property
    def bus(self) -> EventBus:
        return self.scheduler.bus

    def tick_once(self) -> None:
        if not self._clock_initialized:
            self.scheduler.tick = int(self.session.state.step_count)
            self._clock_initialized = True
        tick = int(self.scheduler.tick)

        rng = self.session.state.restore_rng()
        due = self.scheduler.pop_due(tick)
        self.bus.publish("tick", tick=tick)

        merged_overrides: Dict[str, float] = {}
        for item in due:
            if item.kind != "influence":
                continue
            influence: DETMInfluence = item.payload["influence"]
            application: InfluenceApplication = apply_influence(self.session.state.field_state, influence, rng)
            if influence.dynamics_overrides:
                merged_overrides.update({k: float(v) for k, v in influence.dynamics_overrides.items()})
            self.bus.publish(
                "signal",
                tick=tick,
                influence=influence,
                application=application,
                state=self.session.state,
            )

        # Advance L0 by one global tick after all signals are applied.
        override_influence = None
        if merged_overrides:
            override_influence = DETMInfluence(
                symbol_id="scheduled_overrides",
                amplitude=0.0,
                dynamics_overrides=merged_overrides,
            )
        self.session.step(override_influence, 1, rng=rng)
        self.scheduler.tick = tick + 1

    def run(self, n_ticks: int) -> None:
        for _ in range(max(0, int(n_ticks))):
            self.tick_once()

__all__ = ["ScheduledItem", "TickRunner", "TickScheduler"]
