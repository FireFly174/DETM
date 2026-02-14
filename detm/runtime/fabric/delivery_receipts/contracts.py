"""Delivery receipt policy contracts."""

from __future__ import annotations

from typing import Dict, Mapping, Protocol

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (policy + coordinator abstraction exists)
# - OOP_TECH_DEBT: replicated durable coordinator and cross-node consensus integration


class DeliveryReceiptPolicy(Protocol):
    """Policy deciding delivery status from per-sender receipt statuses."""

    def evaluate(self, status_by_sender: Mapping[str, str]) -> tuple[str, str | None, Dict[str, object]]:
        ...


__all__ = ["DeliveryReceiptPolicy"]
