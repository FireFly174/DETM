"""Default local validator implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from detm.runtime.commit_chain import CommitChainManager
from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric.validator.contracts import ReplayChecker
from detm.runtime.fabric.validator.policies import ReplaySamplePolicy


@dataclass
class LocalFabricValidator:
    """Single-node validator that checks local chain consistency and emits acks."""

    validator_id: str = "validator.local"
    chain_manager: CommitChainManager = field(default_factory=CommitChainManager)
    replay_policy: ReplaySamplePolicy = field(default_factory=ReplaySamplePolicy)
    replay_checker: ReplayChecker | None = None
    _max_seen_tick: int | None = field(default=None, init=False, repr=False)

    def validate_commit(
        self,
        packet: CommitPacket,
        *,
        epoch: int | None = None,
        watermark: int | None = None,
        created_at_ms: int = 0,
    ) -> Tuple[ProofAck, TrustAck]:
        reason: str | None = None
        tick = int(packet.tick_ref.tick)
        strict_window_reason = self.replay_policy.strict_window_violation_reason(
            packet,
            max_seen_tick=self._max_seen_tick,
        )
        if strict_window_reason is not None:
            reason = strict_window_reason
        if reason is None:
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
        if self._max_seen_tick is None or int(tick) > int(self._max_seen_tick):
            self._max_seen_tick = int(tick)

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


__all__ = ["LocalFabricValidator"]



