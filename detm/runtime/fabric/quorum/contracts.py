"""Quorum contracts and shared aliases."""

from __future__ import annotations

from typing import Protocol, Sequence, Callable

from detm.runtime.fabric import ProofAck, TrustAck

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (quorum policy abstraction exists)
# - OOP_TECH_DEBT: distributed persistent coordinator and cross-node consensus strategy


class QuorumPolicy(Protocol):
    """Abstract policy deciding commit status from proof/trust acknowledgements."""

    def evaluate(
        self,
        proof_acks: Sequence[ProofAck],
        trust_acks: Sequence[TrustAck],
    ) -> tuple[str, str | None]:
        ...


AckResolver = Callable[[str], ProofAck | TrustAck | None]


__all__ = ["AckResolver", "QuorumPolicy"]


