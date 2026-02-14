"""Minimal in-memory transport adapter for fabric envelopes."""

from detm.runtime.fabric.transport.buffered import BufferedFabricTransport
from detm.runtime.fabric.transport.bus import InMemoryFabricBus
from detm.runtime.fabric.transport.contracts import (
    BACKPRESSURE_POLICIES,
    FabricHandler,
    FabricTransportAdapter,
)

__all__ = [
    "BACKPRESSURE_POLICIES",
    "BufferedFabricTransport",
    "FabricHandler",
    "FabricTransportAdapter",
    "InMemoryFabricBus",
]

