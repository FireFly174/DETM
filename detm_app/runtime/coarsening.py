"""Coarsening / invariant tick streams.

This module provides a *frequency-based* "invariant tick" mechanism that is not
hardcoded to discrete levels (L1/L2/...). Instead, each stream is defined by a
dt ratio relative to the L0 tick (the `DetmSession` step_count).

Example streams:
- dt = 1/10   -> "L1" style update cadence (0.1 per L0 tick)
- dt = 4/25   -> 0.16 per L0 tick

Streams update incrementally on every L0 step (no signature accumulation in the
coarsener). The coarsener emits an `invariant_tick` event on every session step
and includes:
- the current stream time coordinate (as a rational number)
- the integer `invariant_index` and `phase_num` (position within the unit interval)
- a `boundary_crossed` flag when the integer index changes during this step

Persistence / JSON logging is intentionally implemented in separate subscribers.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Iterable, List

from detm_app.runtime.bus import EventBus


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
    l0_tick: int
    dt_num: int
    dt_den: int
    time_num: int
    invariant_index: int
    phase_num: int
    boundary_crossed: bool


class InvariantStream:
    """Pure timekeeper for one invariant stream (no accumulation)."""

    def __init__(self, spec: InvariantStreamSpec) -> None:
        fr = spec.fraction()
        if fr <= 0:
            raise ValueError("Invariant stream dt must be positive")

        self.stream_id = str(spec.stream_id)
        self.dt_num = int(fr.numerator)
        self.dt_den = int(fr.denominator)

    def compute_tick(self, *, l0_tick: int, delta_l0_ticks: int) -> InvariantTick:
        l0_tick = int(l0_tick)
        delta_l0_ticks = max(0, int(delta_l0_ticks))
        start_tick = l0_tick - delta_l0_ticks
        if start_tick < 0:
            start_tick = 0

        time_num_end = l0_tick * self.dt_num
        time_num_start = start_tick * self.dt_num
        idx_end, phase_end = divmod(time_num_end, self.dt_den)
        idx_start, _phase_start = divmod(time_num_start, self.dt_den)
        boundary_crossed = bool(idx_end != idx_start)

        return InvariantTick(
            stream_id=self.stream_id,
            l0_tick=l0_tick,
            dt_num=self.dt_num,
            dt_den=self.dt_den,
            time_num=int(time_num_end),
            invariant_index=int(idx_end),
            phase_num=int(phase_end),
            boundary_crossed=boundary_crossed,
        )


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
        return None

    def on_step(self, *, state, observables, n_ticks: int = 1, get_state_blob: Any | None = None, **_payload: Any) -> None:
        l0_tick = int(state.step_count)
        delta_l0_ticks = max(0, int(n_ticks))
        for stream in self._streams:
            inv = stream.compute_tick(l0_tick=l0_tick, delta_l0_ticks=delta_l0_ticks)
            # Pass through `state/observables/get_state_blob` so listeners that only
            # subscribe to `invariant_tick` can still access the latest L0 snapshot.
            self.bus.publish(
                "invariant_tick",
                stream_id=inv.stream_id,
                l0_tick=inv.l0_tick,
                dt_num=inv.dt_num,
                dt_den=inv.dt_den,
                time_num=inv.time_num,
                invariant_index=inv.invariant_index,
                phase_num=inv.phase_num,
                boundary_crossed=inv.boundary_crossed,
                state=state,
                observables=observables,
                get_state_blob=get_state_blob,
                delta_l0_ticks=delta_l0_ticks,
            )


def parse_invariant_streams(spec: str | Iterable[str]) -> List[InvariantStreamSpec]:
    """Parse stream specs from CLI/UI.

    Accepted formats:
    - "id=1/10"
    - "id=0.1"
    - "id:1/10"
    - "id:0.1"
    - multiple: "a=1/10,b=4/25"
    - list input: ["a=1/10", "b=4/25"]
    """

    if isinstance(spec, str):
        chunks = [c.strip() for c in spec.split(",") if c.strip()]
    else:
        chunks = [str(c).strip() for c in spec if str(c).strip()]

    out: List[InvariantStreamSpec] = []
    for chunk in chunks:
        if "=" in chunk:
            sid, dt = chunk.split("=", 1)
        elif ":" in chunk:
            sid, dt = chunk.split(":", 1)
        else:
            # If only dt is provided, generate a stable id.
            sid = f"inv_{len(out)}"
            dt = chunk
        sid = sid.strip()
        dt = dt.strip()
        if not sid:
            sid = f"inv_{len(out)}"
        if not dt:
            raise ValueError(f"Invalid invariant stream spec (missing dt): {chunk}")
        out.append(InvariantStreamSpec(stream_id=sid, dt=dt))
    return out

__all__ = ["InvariantCoarsener", "InvariantStreamSpec", "parse_invariant_streams"]
