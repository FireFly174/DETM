"""Epoch/consensus builders for fabric runtime composition."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detm.runtime.fabric import (
    FabricEpochCoordinator,
    FileEpochWatermarkCoordinator,
    InMemoryEpochWatermarkCoordinator,
    ReplicatedFileEpochWatermarkCoordinator,
    TransportEpochConsensusCoordinator,
)


def build_epoch_runtime(
    *,
    rec: Any,
    artifact_store: Any,
    transport: Any,
) -> tuple[FabricEpochCoordinator, TransportEpochConsensusCoordinator | None]:
    epoch_coordinator: FabricEpochCoordinator
    if list(rec.epoch_replica_state_paths or []):
        epoch_coordinator = ReplicatedFileEpochWatermarkCoordinator(
            state_paths=list(rec.epoch_replica_state_paths or []),
            read_quorum=rec.epoch_replica_read_quorum,
            write_quorum=rec.epoch_replica_write_quorum,
            lock_timeout_ms=int(rec.epoch_lock_timeout_ms),
            lock_poll_ms=int(rec.epoch_lock_poll_ms),
            lock_stale_ms=None if rec.epoch_lock_stale_ms is None else int(rec.epoch_lock_stale_ms),
        )
    elif rec.epoch_state_path is not None:
        epoch_coordinator = FileEpochWatermarkCoordinator(
            Path(rec.epoch_state_path),
            lock_timeout_ms=int(rec.epoch_lock_timeout_ms),
            lock_poll_ms=int(rec.epoch_lock_poll_ms),
            lock_stale_ms=None if rec.epoch_lock_stale_ms is None else int(rec.epoch_lock_stale_ms),
        )
    elif artifact_store is not None:
        epoch_coordinator = FileEpochWatermarkCoordinator(
            artifact_store.root_dir / "epoch_state.json",
            lock_timeout_ms=int(rec.epoch_lock_timeout_ms),
            lock_poll_ms=int(rec.epoch_lock_poll_ms),
            lock_stale_ms=None if rec.epoch_lock_stale_ms is None else int(rec.epoch_lock_stale_ms),
        )
    else:
        epoch_coordinator = InMemoryEpochWatermarkCoordinator()

    epoch_consensus: TransportEpochConsensusCoordinator | None = None
    use_consensus = bool(rec.epoch_consensus_enabled) or int(rec.epoch_consensus_required_total_accepts) > 1
    if use_consensus:
        epoch_consensus = TransportEpochConsensusCoordinator(
            coordinator_id=f"epoch.{rec.node_id}",
            transport=transport,
            base_coordinator=epoch_coordinator,
            channel=str(rec.epoch_consensus_channel),
            mode_filter=rec.mode_filter,
            required_total_accepts=int(rec.epoch_consensus_required_total_accepts),
            timeout_ms=int(rec.epoch_consensus_timeout_ms),
            max_attempts=int(getattr(rec, "epoch_consensus_max_attempts", 1)),
            reject_on_any_peer_reject=bool(rec.epoch_consensus_reject_on_any_reject),
        )
        epoch_consensus.start()
        epoch_coordinator = epoch_consensus

    return epoch_coordinator, epoch_consensus


__all__ = ["build_epoch_runtime"]
