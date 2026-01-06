"""Session wrapper around the public runtime API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from detm.run.bus import EventBus
from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.state import DETMState


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

    @classmethod
    def create(cls, config: DETMConfig, seed: int, *, bus: Optional[EventBus] = None) -> "DetmSession":
        bus = bus or EventBus()
        state = api.reset(config, seed)
        bus.publish("reset", config=config, seed=int(seed), state=state)
        return cls(config=config, seed=int(seed), bus=bus, state=state)

    def reset(self, *, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.seed = int(seed)
        self.state = api.reset(self.config, self.seed)
        self.bus.publish("reset", config=self.config, seed=int(self.seed), state=self.state)

    def step(
        self,
        influence: DETMInfluence | None,
        n_ticks: int,
        rng: np.random.Generator | None = None,
    ) -> api.Observables:
        self.state, obs = api.step(self.state, influence, int(n_ticks), rng)
        self.bus.publish(
            "step",
            config=self.config,
            seed=int(self.seed),
            state=self.state,
            influence=influence,
            n_ticks=int(n_ticks),
            observables=obs,
        )
        return obs

    def digest(self) -> api.DETMSignature:
        sig = api.digest(self.state)
        self.bus.publish("digest", config=self.config, seed=int(self.seed), state=self.state, signature=sig)
        return sig

    def close(self) -> None:
        self.bus.publish("close", config=self.config, seed=int(self.seed), state=self.state)


__all__ = ["DetmSession"]

