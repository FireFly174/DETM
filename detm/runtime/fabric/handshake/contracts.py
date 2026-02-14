"""Type contracts for fabric handshake service."""

from __future__ import annotations

from typing import Callable

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck

CommitResolver = Callable[[str], CommitPacket | None]
AckWriter = Callable[[ProofAck | TrustAck], str]

__all__ = ["AckWriter", "CommitResolver"]


