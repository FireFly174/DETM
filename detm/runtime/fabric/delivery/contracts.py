"""Delivery outbox contracts and policy constants."""

from __future__ import annotations

from typing import Callable, Protocol

from detm.runtime.fabric import FabricEnvelope

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 1 (durable queue abstraction exists, no distributed replication yet)
# - OOP_TECH_DEBT: replicated outbox, transactional fs writes, and transport-level exactly-once semantics

PublishFunc = Callable[[FabricEnvelope], int]
OUTBOX_DROP_POLICIES = {"oldest", "newest", "audit_first"}


class FabricEnvelopeOutbox(Protocol):
    """Persistent envelope outbox abstraction for retry/flush workflows."""

    def enqueue(self, envelope: FabricEnvelope, *, error: str | None = None) -> None:
        ...

    def flush(self, publish: PublishFunc, *, max_items: int | None = None) -> dict[str, int]:
        ...

    def snapshot(self) -> dict[str, object]:
        ...


__all__ = ["FabricEnvelopeOutbox", "OUTBOX_DROP_POLICIES", "PublishFunc"]


