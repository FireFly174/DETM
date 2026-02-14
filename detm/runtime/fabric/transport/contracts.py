"""Transport contracts and shared constants for fabric routing."""

from __future__ import annotations

from typing import Callable, Protocol

from detm.runtime.fabric import FabricEnvelope

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


__all__ = ["BACKPRESSURE_POLICIES", "FabricHandler", "FabricTransportAdapter"]


