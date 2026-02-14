"""Delivery retry/timeout tracking for commit envelope acknowledged delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from detm.runtime.fabric import InMemoryDeliveryReceiptCoordinator
from detm.runtime.fabric.delivery_tracking.contracts import RepublishFn
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric.delivery_tracking.flow import (
    clear as _clear_flow,
    load_state as _load_state_flow,
    mark_publish_attempt as _mark_publish_attempt_flow,
    persist_state as _persist_state_flow,
    register_delivery as _register_delivery_flow,
    snapshot as _snapshot_flow,
    state_file as _state_file_flow,
    tick as _tick_flow,
)

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (retry/timeout state-machine extracted as dedicated coordinator)
# - OOP_TECH_DEBT: distributed durable coordinator and replicated commit-delivery state


@dataclass
class DeliveryTrackingCoordinator:
    """Tracks pending commit deliveries and drives retry/timeout transitions."""

    receipt_coordinator: InMemoryDeliveryReceiptCoordinator
    required_receipts: int = 0
    retry_interval_ms: int = 100
    max_attempts: int = 3
    timeout_ms: int = 500
    tracking_enabled: bool = False
    pending: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    accepted_count: int = 0
    rejected_count: int = 0
    retries_total: int = 0
    state_path: str | None = None

    def __post_init__(self) -> None:
        self._load_state()

    def enabled(self) -> bool:
        return bool(self.tracking_enabled)

    def register_delivery(self, envelope: FabricEnvelope, *, now_ms: int | None = None) -> str | None:
        return _register_delivery_flow(self, envelope, now_ms=now_ms)

    def mark_publish_attempt(self, delivery_id: str, *, now_ms: int | None = None) -> None:
        _mark_publish_attempt_flow(self, delivery_id, now_ms=now_ms)

    def on_delivery_ack_envelope(self, envelope: FabricEnvelope) -> None:
        self.receipt_coordinator.on_delivery_ack_envelope(envelope)
        self._persist_state()

    def tick(self, republish: RepublishFn, *, now_ms: int | None = None) -> None:
        _tick_flow(self, republish, now_ms=now_ms)

    def snapshot(self) -> Dict[str, object]:
        return _snapshot_flow(self)

    def clear(self) -> None:
        _clear_flow(self)

    def _state_file(self):
        return _state_file_flow(self)

    def _persist_state(self) -> None:
        _persist_state_flow(self)

    def _load_state(self) -> None:
        _load_state_flow(self)


__all__ = ["DeliveryTrackingCoordinator", "RepublishFn"]



