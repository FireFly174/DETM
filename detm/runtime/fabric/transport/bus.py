"""In-memory fabric transport implementation."""

from __future__ import annotations

from collections import defaultdict

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric.transport.contracts import FabricHandler
from detm.runtime.fabric.transport.idempotency import EnvelopeIdempotencyCache


class InMemoryFabricBus:
    """Topic-based in-process transport for tests and local runtimes."""

    def __init__(
        self,
        *,
        dedup_ingress_enabled: bool = False,
        dedup_ttl_ms: int = 30_000,
        dedup_max_entries: int = 10_000,
    ) -> None:
        self._channel_handlers: dict[tuple[str, str | None], list[FabricHandler]] = defaultdict(list)
        self._dedup = EnvelopeIdempotencyCache(
            enabled=bool(dedup_ingress_enabled),
            ttl_ms=int(dedup_ttl_ms),
            max_entries=int(dedup_max_entries),
        )

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
        if not self._dedup.allow(envelope):
            return 0
        delivered = 0
        delivered += self._dispatch((envelope.channel, None), envelope)
        delivered += self._dispatch((envelope.channel, envelope.mode), envelope)
        delivered += self._dispatch(("*", None), envelope)
        delivered += self._dispatch(("*", envelope.mode), envelope)
        return delivered

    def snapshot(self) -> dict[str, object]:
        return {
            "enabled": True,
            "kind": "memory",
            "subscription_count": int(sum(len(v) for v in self._channel_handlers.values())),
            "dedup": self._dedup.snapshot(),
        }

    def _dispatch(self, key: tuple[str, str | None], envelope: FabricEnvelope) -> int:
        handlers = self._channel_handlers.get(key, [])
        for handler in list(handlers):
            handler(envelope)
        return len(handlers)

    def close(self) -> None:
        self._channel_handlers.clear()


__all__ = ["InMemoryFabricBus"]



