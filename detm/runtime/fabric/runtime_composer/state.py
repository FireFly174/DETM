"""Mutable state containers for fabric runtime composition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricEnvelope, ProofAck, TrustAck


@dataclass
class ComposerMutableState:
    commit_store: dict[str, CommitPacket]
    commit_ref_index: dict[str, str]
    ack_store: dict[str, ProofAck | TrustAck]
    ack_envelopes: list[FabricEnvelope]
    ack_subscriptions: list[tuple[str, str | None]]
    delivery_ack_envelopes: list[FabricEnvelope]
    delivery_ack_subscriptions: list[tuple[str, str | None]]
    delivery_pending: dict[str, dict[str, Any]]
    commit_dead_letters: list[dict[str, str]]
    delivery_tracking_state_path: Path


def init_composer_state(*, rec: Any) -> ComposerMutableState:
    return ComposerMutableState(
        commit_store={},
        commit_ref_index={},
        ack_store={},
        ack_envelopes=[],
        ack_subscriptions=[],
        delivery_ack_envelopes=[],
        delivery_ack_subscriptions=[],
        delivery_pending={},
        commit_dead_letters=[],
        delivery_tracking_state_path=(
            Path(str(rec.delivery_tracking_state_path))
            if getattr(rec, "delivery_tracking_state_path", None) is not None
            else Path(rec.out_dir) / "fabric_delivery_tracking_state.json"
        ),
    )


__all__ = ["ComposerMutableState", "init_composer_state"]
