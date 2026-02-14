"""Validator contracts and shared aliases."""

from __future__ import annotations

from typing import Callable, Protocol, Tuple

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck

# ARCH-MARKERS:
# - LAYER_BAND: L4-L5
# - ABSTRACT_DISTANCE: 0 (FabricValidator protocol exists)
# - OOP_TECH_DEBT: distributed quorum validator and replay sampling strategy


class FabricValidator(Protocol):
    """Abstract validator role for commit -> ack conversion."""

    def validate_commit(
        self,
        packet: CommitPacket,
        *,
        epoch: int | None = None,
        watermark: int | None = None,
        created_at_ms: int = 0,
    ) -> Tuple[ProofAck, TrustAck]:
        ...


ReplayChecker = Callable[[CommitPacket], tuple[bool, str | None]]


__all__ = ["FabricValidator", "ReplayChecker"]


