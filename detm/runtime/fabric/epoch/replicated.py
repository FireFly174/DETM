"""Replicated file-backed epoch/watermark coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric.epoch.contracts import EpochDecision
from detm.runtime.fabric.epoch.file import FileEpochWatermarkCoordinator
from detm.runtime.fabric.epoch.operations import commit_epoch, commit_watermark


@dataclass
class ReplicatedFileEpochWatermarkCoordinator:
    """Replicated file-backed coordinator with read/write quorums."""

    state_paths: Sequence[Path | str]
    read_quorum: int | None = None
    write_quorum: int | None = None
    lock_timeout_ms: int = 5000
    lock_poll_ms: int = 10
    lock_stale_ms: int | None = 30000
    enforce_monotonic_tick: bool = True
    enforce_monotonic_epoch: bool = True
    enforce_monotonic_watermark: bool = True
    enforce_watermark_le_epoch: bool = True
    _coordinators: List[FileEpochWatermarkCoordinator] = field(default_factory=list)

    def __post_init__(self) -> None:
        normalized_paths: List[Path] = []
        seen: set[str] = set()
        for raw in list(self.state_paths or []):
            path = Path(raw)
            key = str(path.resolve()) if path.is_absolute() else str(path)
            if key in seen:
                continue
            seen.add(key)
            normalized_paths.append(path)
        if not normalized_paths:
            raise ValueError("state_paths must contain at least one path")

        self._coordinators = [
            FileEpochWatermarkCoordinator(
                state_path=path,
                lock_timeout_ms=int(self.lock_timeout_ms),
                lock_poll_ms=int(self.lock_poll_ms),
                lock_stale_ms=None if self.lock_stale_ms is None else int(self.lock_stale_ms),
                enforce_monotonic_tick=bool(self.enforce_monotonic_tick),
                enforce_monotonic_epoch=bool(self.enforce_monotonic_epoch),
                enforce_monotonic_watermark=bool(self.enforce_monotonic_watermark),
                enforce_watermark_le_epoch=bool(self.enforce_watermark_le_epoch),
            )
            for path in normalized_paths
        ]
        replica_count = len(self._coordinators)
        default_quorum = (replica_count // 2) + 1
        if self.read_quorum is None:
            self.read_quorum = default_quorum
        if self.write_quorum is None:
            self.write_quorum = default_quorum
        self.read_quorum = min(replica_count, max(1, int(self.read_quorum)))
        self.write_quorum = min(replica_count, max(1, int(self.write_quorum)))

    def evaluate_commit(self, packet: CommitPacket) -> EpochDecision:
        accepted = 0
        rejected_reasons: List[str] = []
        for coordinator in self._coordinators:
            decision = coordinator.evaluate_commit(packet)
            if bool(decision.accepted):
                accepted += 1
            else:
                rejected_reasons.append(str(decision.reason))
        if accepted >= int(self.write_quorum):
            return EpochDecision(
                accepted=True,
                reason=None,
                epoch=int(commit_epoch(packet)),
                watermark=int(commit_watermark(packet)),
                tick=int(packet.tick_ref.tick),
            )
        reasons = ", ".join(r for r in rejected_reasons if r) if rejected_reasons else "unknown"
        return EpochDecision(
            accepted=False,
            reason=(
                f"write quorum not reached: accepted={accepted}, required={int(self.write_quorum)}; "
                f"reasons={reasons}"
            ),
            epoch=int(commit_epoch(packet)),
            watermark=int(commit_watermark(packet)),
            tick=int(packet.tick_ref.tick),
        )

    def snapshot(self) -> Dict[str, Any]:
        snapshots: List[Dict[str, Any]] = []
        errors: List[str] = []
        for idx, coordinator in enumerate(self._coordinators):
            try:
                snap = coordinator.snapshot()
                snapshots.append(dict(snap))
            except Exception as exc:
                errors.append(f"replica[{idx}] snapshot error: {exc}")

        reachable = len(snapshots)
        replica_count = len(self._coordinators)
        replication_meta = {
            "mode": "replicated",
            "replica_count": replica_count,
            "reachable": reachable,
            "read_quorum": int(self.read_quorum or 0),
            "write_quorum": int(self.write_quorum or 0),
            "state_paths": [str(c.state_path) for c in self._coordinators],
            "errors": errors,
        }
        if reachable < int(self.read_quorum or 1):
            return {
                "node_count": 0,
                "global": {"epoch": None, "watermark": None},
                "nodes": {},
                "replication": replication_meta,
                "error": f"read quorum not reached: reachable={reachable}, required={int(self.read_quorum or 1)}",
            }

        merged_nodes = _merge_replica_nodes(snapshots)
        epochs = [int(row["epoch"]) for row in merged_nodes.values()] if merged_nodes else []
        watermarks = [int(row["watermark"]) for row in merged_nodes.values()] if merged_nodes else []
        return {
            "node_count": len(merged_nodes),
            "global": {
                "epoch": (max(epochs) if epochs else None),
                "watermark": (min(watermarks) if watermarks else None),
            },
            "nodes": merged_nodes,
            "replication": replication_meta,
        }


def _merge_replica_nodes(snapshots: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    merged: Dict[str, Dict[str, int]] = {}
    for snap in snapshots:
        raw_nodes = snap.get("nodes")
        if not isinstance(raw_nodes, dict):
            continue
        for node_id, row in raw_nodes.items():
            if not isinstance(row, dict):
                continue
            normalized = {
                "tick": int(row.get("tick", 0)),
                "epoch": int(row.get("epoch", 0)),
                "watermark": int(row.get("watermark", 0)),
            }
            existing = merged.get(str(node_id))
            if existing is None:
                merged[str(node_id)] = normalized
                continue
            if int(normalized["tick"]) > int(existing["tick"]):
                merged[str(node_id)] = normalized
            elif int(normalized["tick"]) == int(existing["tick"]):
                if int(normalized["epoch"]) > int(existing["epoch"]):
                    merged[str(node_id)] = normalized
                elif int(normalized["epoch"]) == int(existing["epoch"]):
                    merged[str(node_id)]["watermark"] = max(
                        int(existing["watermark"]), int(normalized["watermark"])
                    )
    return {k: merged[k] for k in sorted(merged.keys())}


__all__ = ["ReplicatedFileEpochWatermarkCoordinator"]

