"""Epoch/watermark coordinator contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from detm.runtime.commit_packet import CommitPacket

# ARCH-MARKERS:
# - LAYER_BAND: L4-L5
# - ABSTRACT_DISTANCE: 0 (FabricEpochCoordinator protocol exists)
# - OOP_TECH_DEBT: distributed replicated coordinator + membership-aware quorum clock


@dataclass(frozen=True)
class EpochDecision:
    """Coordinator decision for a commit boundary."""

    accepted: bool
    reason: str | None
    epoch: int
    watermark: int
    tick: int


class FabricEpochCoordinator(Protocol):
    """Abstract epoch/watermark coordination contract."""

    def evaluate_commit(self, packet: CommitPacket) -> EpochDecision:
        ...

    def snapshot(self) -> Dict[str, Any]:
        ...


__all__ = ["EpochDecision", "FabricEpochCoordinator"]
