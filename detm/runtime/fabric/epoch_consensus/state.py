"""Internal state contracts for transport epoch consensus."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

from detm.runtime.fabric import EpochDecision


@dataclass
class PendingProposal:
    proposal_id: str
    commit_ref: str
    tick: int
    epoch: int
    watermark: int
    required_total_accepts: int
    reject_on_any_peer_reject: bool
    accept_voters: Set[str] = field(default_factory=set)
    reject_reasons: Dict[str, str] = field(default_factory=dict)
    voter_outcomes: Dict[str, bool] = field(default_factory=dict)
    decided: EpochDecision | None = None


__all__ = ["PendingProposal"]


