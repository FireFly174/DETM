"""Local validator contracts and default implementation for fabric handshakes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, Tuple

from detm.runtime.commit_chain import CommitChainManager
from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric_ack import ProofAck, TrustAck

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


@dataclass(frozen=True)
class ReplaySamplePolicy:
    """Sampling policy for optional replay checks in validator flow."""

    enabled: bool = False
    sample_stride: int = 1
    sample_offset: int = 0

    def should_check(self, packet: CommitPacket) -> bool:
        if not bool(self.enabled):
            return False
        stride = max(1, int(self.sample_stride))
        tick = int(packet.tick_ref.tick)
        offset = int(self.sample_offset)
        return ((tick - offset) % stride) == 0


@dataclass
class LocalFabricValidator:
    """Single-node validator that checks local chain consistency and emits acks."""

    validator_id: str = "validator.local"
    chain_manager: CommitChainManager = field(default_factory=CommitChainManager)
    replay_policy: ReplaySamplePolicy = field(default_factory=ReplaySamplePolicy)
    replay_checker: ReplayChecker | None = None

    def validate_commit(
        self,
        packet: CommitPacket,
        *,
        epoch: int | None = None,
        watermark: int | None = None,
        created_at_ms: int = 0,
    ) -> Tuple[ProofAck, TrustAck]:
        reason: str | None = None
        try:
            self.chain_manager.accept(packet)
        except Exception as exc:
            reason = str(exc)
        if reason is None and self.replay_policy.should_check(packet):
            if self.replay_checker is None:
                reason = "replay check required by sampling policy, but replay_checker is not configured"
            else:
                try:
                    ok, replay_reason = self.replay_checker(packet)
                except Exception as exc:
                    ok, replay_reason = False, f"replay checker error: {exc}"
                if not bool(ok):
                    reason = str(replay_reason or "replay check failed")

        status = "accepted" if reason is None else "rejected"
        commit_ref = str(packet.commit_id)
        node_id = str(packet.node_id)

        proof = ProofAck(
            validator_id=str(self.validator_id),
            node_id=node_id,
            commit_ref=commit_ref,
            status=status,
            reason=reason,
            proof_ref=None if status == "rejected" else f"proof://{node_id}/{commit_ref}",
            epoch=epoch,
            watermark=watermark,
            signature=f"sig://{self.validator_id}/proof/{commit_ref}",
            created_at_ms=int(created_at_ms),
        )
        trust = TrustAck(
            validator_id=str(self.validator_id),
            node_id=node_id,
            commit_ref=commit_ref,
            status=status,
            reason=reason,
            trust_ref=None if status == "rejected" else f"trust://{self.validator_id}/{node_id}/{commit_ref}",
            signature=f"sig://{self.validator_id}/trust/{commit_ref}",
            created_at_ms=int(created_at_ms),
        )
        return proof, trust


__all__ = ["FabricValidator", "LocalFabricValidator", "ReplayChecker", "ReplaySamplePolicy"]
