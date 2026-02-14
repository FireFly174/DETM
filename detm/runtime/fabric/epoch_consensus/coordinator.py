"""Transport-based pre-consensus coordinator for epoch/watermark decisions."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import EpochDecision, FabricEpochCoordinator
from detm.runtime.fabric.epoch_consensus.flow import (
    evaluate_commit as evaluate_commit_flow,
    on_epoch_envelope as on_epoch_envelope_flow,
    on_proposal as on_proposal_flow,
    on_vote as on_vote_flow,
    snapshot as snapshot_flow,
)
from detm.runtime.fabric.epoch_consensus.state import PendingProposal
from detm.runtime.fabric import FabricTransportAdapter

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (pre-consensus coordinator abstraction exists)
# - OOP_TECH_DEBT: Byzantine-safe consensus + replicated log


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
    max_attempts: int = 1
    reject_on_any_peer_reject: bool = False
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _condition: threading.Condition = field(init=False)
    _pending: Dict[str, PendingProposal] = field(default_factory=dict)
    _seq: int = 0
    _started: bool = False
    _stats: Dict[str, int] = field(
        default_factory=lambda: {
            "accepted": 0,
            "rejected": 0,
            "timeouts": 0,
            "retries_total": 0,
            "proposals_total": 0,
            "invalid_votes_total": 0,
            "conflicting_votes_total": 0,
        }
    )

    def __post_init__(self) -> None:
        self._condition = threading.Condition(self._lock)
        self.required_total_accepts = max(1, int(self.required_total_accepts))
        self.timeout_ms = max(1, int(self.timeout_ms))
        self.max_attempts = max(1, int(self.max_attempts))

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
        return evaluate_commit_flow(self, packet)

    def _on_epoch_envelope(self, envelope: FabricEnvelope) -> None:
        on_epoch_envelope_flow(self, envelope)

    def _on_proposal(self, envelope: FabricEnvelope) -> None:
        on_proposal_flow(self, envelope)

    def _on_vote(self, envelope: FabricEnvelope) -> None:
        on_vote_flow(self, envelope)

    def snapshot(self) -> Dict[str, Any]:
        return snapshot_flow(self)


__all__ = ["TransportEpochConsensusCoordinator"]



