"""Lifecycle bundle for fabric handshake runtime components."""

from __future__ import annotations

from dataclasses import dataclass

from detm.runtime.fabric import FabricAckIngressService
from detm.runtime.fabric import FabricCommitDeliveryService
from detm.runtime.fabric import TransportEpochConsensusCoordinator
from detm.runtime.fabric import FabricHandshakeService
from detm.runtime.fabric import FabricTransportAdapter

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (runtime lifecycle wiring extracted from subscriber orchestration)
# - OOP_TECH_DEBT: distributed runtime lifecycle coordinator with health checks and failover


@dataclass
class FabricHandshakeRuntimeBundle:
    """Owns start/stop lifecycle order for handshake runtime services."""

    service: FabricHandshakeService | None = None
    ack_runtime: FabricAckIngressService | None = None
    delivery_runtime: FabricCommitDeliveryService | None = None
    transport: FabricTransportAdapter | None = None
    epoch_consensus: TransportEpochConsensusCoordinator | None = None

    def start(self) -> None:
        if self.service is not None:
            self.service.start()
        if self.ack_runtime is not None:
            self.ack_runtime.start()
        if self.delivery_runtime is not None:
            self.delivery_runtime.start()

    def stop(self) -> None:
        if self.service is not None:
            self.service.stop()
        if self.ack_runtime is not None:
            self.ack_runtime.stop()
        if self.delivery_runtime is not None:
            self.delivery_runtime.stop()
        if self.transport is not None:
            self.transport.close()
        if self.epoch_consensus is not None:
            self.epoch_consensus.stop()

    def ack_subscriptions(self) -> list[tuple[str, str | None]]:
        if self.ack_runtime is None:
            return []
        return self.ack_runtime.subscriptions

    def delivery_ack_subscriptions(self) -> list[tuple[str, str | None]]:
        if self.delivery_runtime is None:
            return []
        return self.delivery_runtime.subscriptions


__all__ = ["FabricHandshakeRuntimeBundle"]


