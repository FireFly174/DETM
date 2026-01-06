"""Reusable subscribers for the EventBus."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.state import DETMState
from detm.viz.transport import VizTransport


@dataclass
class TraceRecorder:
    """Collects step history and writes `history.jsonl` on close/finish."""

    out_dir: Path
    history: List[Dict[str, Any]]

    @classmethod
    def attach(cls, bus, out_dir: Path) -> "TraceRecorder":
        rec = cls(out_dir=out_dir, history=[])
        bus.add_event_listener("step", rec.on_step)
        bus.add_event_listener("close", rec.on_close)
        return rec

    def on_step(
        self,
        *,
        observables: api.Observables,
        **_rest: Any,
    ) -> None:
        self.history.append(
            {
                "signature": observables.signature.as_dict(),
                "events": list(observables.events),
                "cost": dict(observables.cost),
                "quality": dict(observables.quality),
            }
        )

    def on_close(self, **_rest: Any) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / "history.jsonl"
        path.write_text("\n".join(json.dumps(entry) for entry in self.history), encoding="utf-8")


@dataclass
class ArtifactWriter:
    """Writes `state.msgpack`, `digest.json`, and `config.json` on close."""

    out_dir: Path
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(cls, bus, out_dir: Path) -> "ArtifactWriter":
        writer = cls(out_dir=out_dir)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def on_close(
        self,
        *,
        config: DETMConfig,
        state: DETMState,
        **_rest: Any,
    ) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "config.json").write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
        (self.out_dir / "state.msgpack").write_bytes(api.serialize(state))
        digest = api.digest(state)
        (self.out_dir / "digest.json").write_text(json.dumps(digest.as_dict(), indent=2), encoding="utf-8")
        self.detach()

    def detach(self) -> None:
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


@dataclass
class JsonlTraceWriter:
    """Writes a streaming `trace.jsonl` file from `step` events."""

    path: Path
    _fh: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(cls, bus, path: Path) -> "JsonlTraceWriter":
        writer = cls(path=path)
        writer._unsub_step = bus.add_event_listener_unsub("step", writer.on_step)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def on_step(
        self,
        *,
        state: DETMState,
        influence: DETMInfluence | None,
        n_ticks: int,
        observables: api.Observables,
        **_rest: Any,
    ) -> None:
        self._ensure()
        entry = {
            "tick": int(state.step_count),
            "n_ticks": int(n_ticks),
            "influence": influence.__dict__ if influence is not None else None,
            "signature": observables.signature.as_dict(),
            "field_summaries": {
                "energy": observables.field_summaries.energy,
                "entropy": observables.field_summaries.entropy,
                "internal_time": observables.field_summaries.internal_time,
            },
            "cost": dict(observables.cost),
            "quality": dict(observables.quality),
            "events": list(observables.events),
        }
        assert self._fh is not None
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()

    def on_close(self, **_rest: Any) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        self.detach()

    def detach(self) -> None:
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


@dataclass
class VizStreamer:
    """Streams state updates to a VizTransport.

    For now we stream serialized state blobs; transports can choose how they
    deliver frames (tcp/shared memory/etc.).
    """

    transport: VizTransport
    every_steps: int = 1
    _last_sent_step: int = -1
    _unsub_reset: Callable[[], None] | None = None
    _unsub_step: Callable[[], None] | None = None

    @classmethod
    def attach(cls, bus, transport: VizTransport, *, every_steps: int = 1) -> "VizStreamer":
        inst = cls(transport=transport, every_steps=max(1, int(every_steps)))
        inst._unsub_reset = bus.add_event_listener_unsub("reset", inst.on_reset)
        inst._unsub_step = bus.add_event_listener_unsub("step", inst.on_step)
        return inst

    def _maybe_send(self, state: DETMState, signature: api.DETMSignature) -> None:
        step_count = int(state.step_count)
        if self._last_sent_step >= 0 and (step_count - self._last_sent_step) < self.every_steps:
            return
        self._last_sent_step = step_count
        blob = api.serialize(state)
        self.transport.send_state(state_blob=blob, tick=step_count, signature=signature.vector)

    def on_reset(self, *, state: DETMState, **_rest: Any) -> None:
        self._last_sent_step = -1
        self._maybe_send(state, api.digest(state))

    def on_step(self, *, state: DETMState, observables: api.Observables, **_rest: Any) -> None:
        self._maybe_send(state, observables.signature)

    def detach(self) -> None:
        if self._unsub_reset is not None:
            self._unsub_reset()
            self._unsub_reset = None
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None


__all__ = ["ArtifactWriter", "JsonlTraceWriter", "TraceRecorder", "VizStreamer"]
