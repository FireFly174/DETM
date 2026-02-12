"""Transport-based pre-consensus coordinator for epoch/watermark decisions."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Set

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_epoch import EpochDecision, FabricEpochCoordinator
from detm.runtime.fabric_transport import FabricTransportAdapter

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (pre-consensus coordinator abstraction exists)
# - OOP_TECH_DEBT: Byzantine-safe consensus + replicated log


@dataclass
class _PendingProposal:
    proposal_id: str
    commit_ref: str
    tick: int
    epoch: int
    watermark: int
    required_total_accepts: int
    reject_on_any_peer_reject: bool
    accept_voters: Set[str] = field(default_factory=set)
    reject_reasons: Dict[str, str] = field(default_factory=dict)
    decided: EpochDecision | None = None


@dataclass
class TransportEpochConsensusCoordinator:
    """Collects epoch votes over transport and enforces quorum before accept."""

    coordinator_id: str
    transport: FabricTransportAdapter
    base_coordinator: FabricEpochCoordinator
    channel: str = "fabric.epoch"
    mode_filter: str | None = "realtime"
    required_total_accepts: int = 1
    timeout_ms: int = 200
    reject_on_any_peer_reject: bool = False
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _condition: threading.Condition = field(init=False)
    _pending: Dict[str, _PendingProposal] = field(default_factory=dict)
    _seq: int = 0
    _started: bool = False
    _stats: Dict[str, int] = field(default_factory=lambda: {"accepted": 0, "rejected": 0, "timeouts": 0})

    def __post_init__(self) -> None:
        self._condition = threading.Condition(self._lock)
        self.required_total_accepts = max(1, int(self.required_total_accepts))
        self.timeout_ms = max(1, int(self.timeout_ms))

    def start(self) -> None:
        if self._started:
            return
        self.transport.subscribe(self.channel, self._on_epoch_envelope, mode=self.mode_filter)
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self.transport.unsubscribe(self.channel, self._on_epoch_envelope, mode=self.mode_filter)
        self._started = False

    def evaluate_commit(self, packet: CommitPacket) -> EpochDecision:
        if not self._started:
            self.start()

        local = self.base_coordinator.evaluate_commit(packet)
        if not bool(local.accepted):
            with self._lock:
                self._stats["rejected"] = int(self._stats.get("rejected", 0)) + 1
            return local
        if int(self.required_total_accepts) <= 1:
            with self._lock:
                self._stats["accepted"] = int(self._stats.get("accepted", 0)) + 1
            return local

        with self._condition:
            self._seq += 1
            proposal_id = f"{self.coordinator_id}:{int(packet.tick_ref.tick)}:{self._seq}"
            pending = _PendingProposal(
                proposal_id=proposal_id,
                commit_ref=str(packet.commit_id),
                tick=int(packet.tick_ref.tick),
                epoch=int(local.epoch),
                watermark=int(local.watermark),
                required_total_accepts=int(self.required_total_accepts),
                reject_on_any_peer_reject=bool(self.reject_on_any_peer_reject),
                accept_voters={str(self.coordinator_id)},
            )
            self._pending[proposal_id] = pending

        proposal_env = FabricEnvelope(
            message_type="epoch_proposal",
            channel=str(self.channel),
            mode=str(packet.mode),
            sender=str(self.coordinator_id),
            recipient=None,
            payload_ref=f"artifact://epoch/proposal/{proposal_id}",
            payload_inline={
                "proposal_id": proposal_id,
                "commit_ref": str(packet.commit_id),
                "packet": packet.to_dict(),
            },
            trace_ref=str(packet.trace_ref),
            commit_ref=str(packet.commit_id),
        )
        self.transport.publish(proposal_env)

        deadline = time.monotonic() + (float(self.timeout_ms) / 1000.0)
        with self._condition:
            while True:
                current = self._pending.get(proposal_id)
                if current is None:
                    break
                if current.decided is not None:
                    decision = current.decided
                    self._pending.pop(proposal_id, None)
                    self._stats["accepted" if bool(decision.accepted) else "rejected"] = (
                        int(self._stats.get("accepted" if bool(decision.accepted) else "rejected", 0)) + 1
                    )
                    return decision
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(timeout=remaining)

            current = self._pending.pop(proposal_id, None)
            if current is None:
                self._stats["rejected"] = int(self._stats.get("rejected", 0)) + 1
                return EpochDecision(
                    accepted=False,
                    reason="consensus pending state lost",
                    epoch=int(local.epoch),
                    watermark=int(local.watermark),
                    tick=int(local.tick),
                )
            self._stats["rejected"] = int(self._stats.get("rejected", 0)) + 1
            self._stats["timeouts"] = int(self._stats.get("timeouts", 0)) + 1
            return EpochDecision(
                accepted=False,
                reason=(
                    f"epoch consensus timeout: accepts={len(current.accept_voters)}, "
                    f"required={int(current.required_total_accepts)}, rejects={len(current.reject_reasons)}"
                ),
                epoch=int(current.epoch),
                watermark=int(current.watermark),
                tick=int(current.tick),
            )

    def _on_epoch_envelope(self, envelope: FabricEnvelope) -> None:
        if envelope.message_type == "epoch_proposal":
            self._on_proposal(envelope)
            return
        if envelope.message_type == "epoch_vote":
            self._on_vote(envelope)

    def _on_proposal(self, envelope: FabricEnvelope) -> None:
        if str(envelope.sender) == str(self.coordinator_id):
            return
        payload = envelope.payload_inline
        if not isinstance(payload, dict):
            return
        proposal_id = str(payload.get("proposal_id", "")).strip()
        packet_raw = payload.get("packet")
        if not proposal_id or not isinstance(packet_raw, dict):
            return
        try:
            packet = CommitPacket.from_dict(packet_raw)
        except Exception:
            return
        decision = self.base_coordinator.evaluate_commit(packet)
        vote_env = FabricEnvelope(
            message_type="epoch_vote",
            channel=str(self.channel),
            mode=str(envelope.mode),
            sender=str(self.coordinator_id),
            recipient=str(envelope.sender),
            payload_ref=f"artifact://epoch/vote/{proposal_id}/{self.coordinator_id}",
            payload_inline={
                "proposal_id": proposal_id,
                "voter_id": str(self.coordinator_id),
                "accepted": bool(decision.accepted),
                "reason": None if decision.reason is None else str(decision.reason),
                "epoch": int(decision.epoch),
                "watermark": int(decision.watermark),
                "tick": int(decision.tick),
                "commit_ref": str(packet.commit_id),
            },
            trace_ref=str(packet.trace_ref),
            commit_ref=str(packet.commit_id),
        )
        self.transport.publish(vote_env)

    def _on_vote(self, envelope: FabricEnvelope) -> None:
        payload = envelope.payload_inline
        if not isinstance(payload, dict):
            return
        proposal_id = str(payload.get("proposal_id", "")).strip()
        voter_id = str(payload.get("voter_id", envelope.sender)).strip()
        if not proposal_id or not voter_id:
            return
        accepted = bool(payload.get("accepted", False))
        reason = None if payload.get("reason") is None else str(payload.get("reason"))

        with self._condition:
            pending = self._pending.get(proposal_id)
            if pending is None:
                return
            if accepted:
                pending.accept_voters.add(voter_id)
            else:
                pending.reject_reasons[voter_id] = str(reason or "rejected")

            if pending.reject_on_any_peer_reject and pending.reject_reasons:
                details = ", ".join(
                    f"{key}:{value}" for key, value in sorted(pending.reject_reasons.items())
                )
                pending.decided = EpochDecision(
                    accepted=False,
                    reason=f"peer rejected epoch proposal: {details}",
                    epoch=int(pending.epoch),
                    watermark=int(pending.watermark),
                    tick=int(pending.tick),
                )
            elif len(pending.accept_voters) >= int(pending.required_total_accepts):
                pending.decided = EpochDecision(
                    accepted=True,
                    reason=None,
                    epoch=int(pending.epoch),
                    watermark=int(pending.watermark),
                    tick=int(pending.tick),
                )

            self._condition.notify_all()

    def snapshot(self) -> Dict[str, Any]:
        base = self.base_coordinator.snapshot()
        with self._lock:
            return {
                "base": base,
                "consensus": {
                    "mode": "transport_pre_consensus",
                    "coordinator_id": str(self.coordinator_id),
                    "channel": str(self.channel),
                    "required_total_accepts": int(self.required_total_accepts),
                    "timeout_ms": int(self.timeout_ms),
                    "reject_on_any_peer_reject": bool(self.reject_on_any_peer_reject),
                    "pending_count": len(self._pending),
                    "stats": dict(self._stats),
                },
            }


__all__ = ["TransportEpochConsensusCoordinator"]
