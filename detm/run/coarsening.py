"""Coarsening / invariant tick streams.

This module provides a *frequency-based* "invariant tick" mechanism that is not
hardcoded to discrete levels (L1/L2/...). Instead, each stream is defined by a
dt ratio relative to the L0 microtick (the `DetmSession` step_count).

Example streams:
- dt = 1/10   -> "L1" style update cadence (0.1 per L0 tick)
- dt = 4/25   -> 0.16 per L0 tick

Streams update incrementally on every L0 step (no "lump sum" at boundaries).
An `invariant_tick` event is emitted whenever the stream crosses an integer
boundary in its own time coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from detm.run.bus import EventBus


def _as_fraction(value: float | str | Fraction, *, max_denominator: int = 1000) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, str):
        return Fraction(value).limit_denominator(max_denominator)
    return Fraction(value).limit_denominator(max_denominator)


@dataclass(frozen=True)
class InvariantStreamSpec:
    stream_id: str
    dt: float | str | Fraction
    max_denominator: int = 1000

    def fraction(self) -> Fraction:
        return _as_fraction(self.dt, max_denominator=int(self.max_denominator))


@dataclass
class InvariantTick:
    stream_id: str
    invariant_tick: int
    l0_tick: int
    dt_num: int
    dt_den: int
    signature_mean: List[float]
    samples: int


class InvariantStream:
    """Incremental accumulator for one invariant stream."""

    def __init__(self, spec: InvariantStreamSpec) -> None:
        fr = spec.fraction()
        if fr <= 0:
            raise ValueError("Invariant stream dt must be positive")

        self.stream_id = str(spec.stream_id)
        self.dt_num = int(fr.numerator)
        self.dt_den = int(fr.denominator)

        self._phase = 0  # integer in [0..dt_den)
        self._tick = 0

        self._sum: np.ndarray | None = None  # weighted sum
        self._weight = 0  # in dt_den units
        self._samples = 0

    def reset(self) -> None:
        self._phase = 0
        self._tick = 0
        self._sum = None
        self._weight = 0
        self._samples = 0

    def update(self, *, l0_tick: int, signature: Sequence[float]) -> List[InvariantTick]:
        sig = np.asarray(signature, dtype=float)
        if sig.ndim != 1:
            sig = sig.reshape(-1)

        if self._sum is None:
            self._sum = np.zeros_like(sig, dtype=float)

        emitted: List[InvariantTick] = []

        # Split this update into one or more segments if it crosses boundaries.
        remaining = self.dt_num
        while remaining > 0:
            to_boundary = self.dt_den - self._phase
            take = remaining if remaining < to_boundary else to_boundary

            self._sum += sig * float(take)
            self._weight += int(take)
            self._samples += 1
            self._phase += int(take)
            remaining -= int(take)

            if self._phase >= self.dt_den:
                # Emit invariant tick snapshot for the completed unit interval.
                mean = (self._sum / float(max(1, self._weight))).tolist()
                emitted.append(
                    InvariantTick(
                        stream_id=self.stream_id,
                        invariant_tick=int(self._tick),
                        l0_tick=int(l0_tick),
                        dt_num=int(self.dt_num),
                        dt_den=int(self.dt_den),
                        signature_mean=[float(x) for x in mean],
                        samples=int(self._samples),
                    )
                )
                self._tick += 1
                self._phase -= self.dt_den
                # Carry remainder of the last step into the next interval: reset accumulators.
                self._sum = np.zeros_like(sig, dtype=float)
                self._weight = 0
                self._samples = 0

        return emitted


class InvariantCoarsener:
    """EventBus subscriber that emits `invariant_tick` events for configured streams."""

    def __init__(self, bus: EventBus, streams: Iterable[InvariantStreamSpec]) -> None:
        self.bus = bus
        self._streams = [InvariantStream(spec) for spec in streams]
        self._unsub_reset: Callable[[], None] | None = None
        self._unsub_step: Callable[[], None] | None = None

    @classmethod
    def attach(cls, bus: EventBus, streams: Iterable[InvariantStreamSpec]) -> "InvariantCoarsener":
        inst = cls(bus, streams)
        inst._unsub_reset = bus.add_event_listener_unsub("reset", inst.on_reset)
        inst._unsub_step = bus.add_event_listener_unsub("step", inst.on_step)
        return inst

    def detach(self) -> None:
        if self._unsub_reset is not None:
            self._unsub_reset()
            self._unsub_reset = None
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None

    def on_reset(self, **_payload: Any) -> None:
        for stream in self._streams:
            stream.reset()

    def on_step(self, *, state, observables, **_payload: Any) -> None:
        l0_tick = int(state.step_count)
        signature = observables.signature.vector
        for stream in self._streams:
            ticks = stream.update(l0_tick=l0_tick, signature=signature)
            for inv in ticks:
                self.bus.publish(
                    "invariant_tick",
                    stream_id=inv.stream_id,
                    invariant_tick=inv.invariant_tick,
                    l0_tick=inv.l0_tick,
                    dt_num=inv.dt_num,
                    dt_den=inv.dt_den,
                    signature_mean=inv.signature_mean,
                    samples=inv.samples,
                )


__all__ = ["InvariantCoarsener", "InvariantStreamSpec"]

