"""Minimal in-memory transport adapter for fabric envelopes."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Protocol

from detm.runtime.fabric_envelope import FabricEnvelope

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (adapter protocol exists)
# - OOP_TECH_DEBT: network adapter with delivery guarantees and backpressure controls


FabricHandler = Callable[[FabricEnvelope], None]
BACKPRESSURE_POLICIES = {"block", "drop_oldest", "drop_newest", "fail"}


class FabricTransportAdapter(Protocol):
    """Transport adapter abstraction for channel-based fabric routing."""

    def subscribe(self, channel: str, handler: FabricHandler, *, mode: str | None = None) -> None:
        ...

    def unsubscribe(self, channel: str, handler: FabricHandler, *, mode: str | None = None) -> bool:
        ...

    def publish(self, envelope: FabricEnvelope) -> int:
        ...

    def close(self) -> None:
        ...


class InMemoryFabricBus:
    """Topic-based in-process transport for tests and local runtimes."""

    def __init__(self) -> None:
        self._channel_handlers: Dict[tuple[str, str | None], List[FabricHandler]] = defaultdict(list)

    def subscribe(self, channel: str, handler: FabricHandler, *, mode: str | None = None) -> None:
        key = (str(channel), None if mode is None else str(mode).strip().lower())
        self._channel_handlers[key].append(handler)

    def unsubscribe(self, channel: str, handler: FabricHandler, *, mode: str | None = None) -> bool:
        key = (str(channel), None if mode is None else str(mode).strip().lower())
        handlers = self._channel_handlers.get(key)
        if not handlers:
            return False
        for idx, existing in enumerate(list(handlers)):
            if existing is handler:
                del handlers[idx]
                if not handlers:
                    self._channel_handlers.pop(key, None)
                return True
        return False

    def publish(self, envelope: FabricEnvelope) -> int:
        envelope.validate()
        delivered = 0
        delivered += self._dispatch((envelope.channel, None), envelope)
        delivered += self._dispatch((envelope.channel, envelope.mode), envelope)
        delivered += self._dispatch(("*", None), envelope)
        delivered += self._dispatch(("*", envelope.mode), envelope)
        return delivered

    def _dispatch(self, key: tuple[str, str | None], envelope: FabricEnvelope) -> int:
        handlers = self._channel_handlers.get(key, [])
        for handler in list(handlers):
            handler(envelope)
        return len(handlers)

    def close(self) -> None:
        self._channel_handlers.clear()


@dataclass
class BufferedFabricTransport:
    """Backpressure-aware publish buffer wrapper over a base transport adapter."""

    base: FabricTransportAdapter
    max_pending: int = 1024
    policy: str = "block"  # block | drop_oldest | drop_newest | fail
    block_timeout_ms: int = 200
    close_base_on_close: bool = True
    auto_start: bool = True
    _queue: list[FabricEnvelope] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _cond: threading.Condition = field(init=False)
    _worker: threading.Thread | None = None
    _running: bool = False
    _enqueued_total: int = 0
    _sent_total: int = 0
    _failed_total: int = 0
    _dropped_oldest_total: int = 0
    _dropped_newest_total: int = 0
    _rejected_total: int = 0
    _last_error: str | None = None

    def __post_init__(self) -> None:
        self.policy = str(self.policy).strip().lower()
        if self.policy not in BACKPRESSURE_POLICIES:
            raise ValueError(f"policy must be one of {sorted(BACKPRESSURE_POLICIES)}")
        self.max_pending = max(1, int(self.max_pending))
        self.block_timeout_ms = max(0, int(self.block_timeout_ms))
        self._cond = threading.Condition(self._lock)
        if bool(self.auto_start):
            self.start()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._worker = threading.Thread(target=self._drain_loop, name="fabric-transport-buffer", daemon=True)
            self._worker.start()

    def subscribe(self, channel: str, handler: FabricHandler, *, mode: str | None = None) -> None:
        self.base.subscribe(channel, handler, mode=mode)

    def unsubscribe(self, channel: str, handler: FabricHandler, *, mode: str | None = None) -> bool:
        return bool(self.base.unsubscribe(channel, handler, mode=mode))

    def publish(self, envelope: FabricEnvelope) -> int:
        envelope.validate()
        if bool(self.auto_start):
            self.start()
        with self._cond:
            while len(self._queue) >= int(self.max_pending):
                if self.policy == "drop_oldest":
                    if self._queue:
                        self._queue.pop(0)
                        self._dropped_oldest_total += 1
                    break
                if self.policy == "drop_newest":
                    self._dropped_newest_total += 1
                    return 0
                if self.policy == "fail":
                    self._rejected_total += 1
                    raise RuntimeError("transport backpressure: pending queue is full")
                timeout_s = float(self.block_timeout_ms) / 1000.0
                if timeout_s <= 0.0:
                    self._rejected_total += 1
                    raise RuntimeError("transport backpressure: block timeout exceeded (0ms)")
                started = time.perf_counter()
                self._cond.wait(timeout=timeout_s)
                waited_ms = (time.perf_counter() - started) * 1000.0
                if waited_ms + 1e-6 >= float(self.block_timeout_ms) and len(self._queue) >= int(self.max_pending):
                    self._rejected_total += 1
                    raise RuntimeError(
                        f"transport backpressure: block timeout exceeded ({int(waited_ms)}ms >= {int(self.block_timeout_ms)}ms)"
                    )
            self._queue.append(envelope)
            self._enqueued_total += 1
            self._cond.notify_all()
        return 1

    def _drain_loop(self) -> None:
        while True:
            envelope: FabricEnvelope | None = None
            with self._cond:
                while self._running and not self._queue:
                    self._cond.wait(timeout=0.2)
                if not self._running and not self._queue:
                    break
                if self._queue:
                    envelope = self._queue.pop(0)
                    self._cond.notify_all()
            if envelope is None:
                continue
            try:
                delivered = int(self.base.publish(envelope))
                if delivered <= 0:
                    raise RuntimeError("base transport dropped envelope")
            except Exception as exc:
                with self._lock:
                    self._failed_total += 1
                    self._last_error = str(exc)
            else:
                with self._lock:
                    self._sent_total += 1

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            return {
                "enabled": True,
                "max_pending": int(self.max_pending),
                "policy": str(self.policy),
                "block_timeout_ms": int(self.block_timeout_ms),
                "pending_count": len(self._queue),
                "enqueued_total": int(self._enqueued_total),
                "sent_total": int(self._sent_total),
                "failed_total": int(self._failed_total),
                "dropped_oldest_total": int(self._dropped_oldest_total),
                "dropped_newest_total": int(self._dropped_newest_total),
                "rejected_total": int(self._rejected_total),
                "last_error": self._last_error,
            }

    def close(self) -> None:
        worker: threading.Thread | None = None
        with self._cond:
            self._running = False
            self._cond.notify_all()
            worker = self._worker
            self._worker = None
        if worker is not None:
            worker.join(timeout=1.0)
        if bool(self.close_base_on_close):
            self.base.close()


__all__ = [
    "BACKPRESSURE_POLICIES",
    "BufferedFabricTransport",
    "FabricHandler",
    "FabricTransportAdapter",
    "InMemoryFabricBus",
]
