"""Epoch/watermark coordination for fabric commit boundaries."""

from __future__ import annotations

import contextlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Protocol, Sequence

from detm.runtime.commit_packet import CommitPacket

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (epoch coordinator abstraction exists)
# - OOP_TECH_DEBT: distributed replicated coordinator + membership-aware quorum clock


@dataclass(frozen=True)
class EpochDecision:
    """Coordinator decision for a commit boundary."""

    accepted: bool
    reason: str | None
    epoch: int
    watermark: int
    tick: int


class FabricEpochCoordinator(Protocol):
    """Abstract epoch/watermark coordination contract."""

    def evaluate_commit(self, packet: CommitPacket) -> EpochDecision:
        ...

    def snapshot(self) -> Dict[str, Any]:
        ...


def commit_epoch(packet: CommitPacket) -> int:
    summary = dict(packet.summary or {})
    raw = summary.get("epoch", packet.tick_ref.tick)
    return max(0, int(raw))


def commit_watermark(packet: CommitPacket) -> int:
    summary = dict(packet.summary or {})
    raw = summary.get("watermark", packet.tick_ref.tick)
    return max(0, int(raw))


@dataclass
class InMemoryEpochWatermarkCoordinator:
    """In-memory monotonic epoch/watermark coordinator (MVP)."""

    enforce_monotonic_tick: bool = True
    enforce_monotonic_epoch: bool = True
    enforce_monotonic_watermark: bool = True
    enforce_watermark_le_epoch: bool = True
    _node_state: Dict[str, Dict[str, int]] = field(default_factory=dict)
    _global_epoch: int | None = None
    _global_watermark: int | None = None

    def evaluate_commit(self, packet: CommitPacket) -> EpochDecision:
        node_id = str(packet.node_id)
        tick = int(packet.tick_ref.tick)
        epoch = int(commit_epoch(packet))
        watermark = int(commit_watermark(packet))
        if self.enforce_watermark_le_epoch and watermark > epoch:
            return EpochDecision(
                accepted=False,
                reason=f"watermark {watermark} cannot exceed epoch {epoch}",
                epoch=epoch,
                watermark=watermark,
                tick=tick,
            )

        prev = self._node_state.get(node_id)
        if prev is not None:
            prev_tick = int(prev.get("tick", -1))
            prev_epoch = int(prev.get("epoch", -1))
            prev_watermark = int(prev.get("watermark", -1))
            if self.enforce_monotonic_tick and tick <= prev_tick:
                return EpochDecision(
                    accepted=False,
                    reason=f"tick regression for {node_id}: prev={prev_tick}, got={tick}",
                    epoch=epoch,
                    watermark=watermark,
                    tick=tick,
                )
            if self.enforce_monotonic_epoch and epoch < prev_epoch:
                return EpochDecision(
                    accepted=False,
                    reason=f"epoch regression for {node_id}: prev={prev_epoch}, got={epoch}",
                    epoch=epoch,
                    watermark=watermark,
                    tick=tick,
                )
            if self.enforce_monotonic_watermark and watermark < prev_watermark:
                return EpochDecision(
                    accepted=False,
                    reason=f"watermark regression for {node_id}: prev={prev_watermark}, got={watermark}",
                    epoch=epoch,
                    watermark=watermark,
                    tick=tick,
                )

        self._node_state[node_id] = {"tick": tick, "epoch": epoch, "watermark": watermark}
        self._recompute_global_state()
        return EpochDecision(accepted=True, reason=None, epoch=epoch, watermark=watermark, tick=tick)

    def _recompute_global_state(self) -> None:
        if not self._node_state:
            self._global_epoch = None
            self._global_watermark = None
            return
        epochs = [int(row["epoch"]) for row in self._node_state.values()]
        watermarks = [int(row["watermark"]) for row in self._node_state.values()]
        self._global_epoch = max(epochs) if epochs else None
        self._global_watermark = min(watermarks) if watermarks else None

    def snapshot(self) -> Dict[str, Any]:
        nodes = {
            str(node_id): {
                "tick": int(row.get("tick", 0)),
                "epoch": int(row.get("epoch", 0)),
                "watermark": int(row.get("watermark", 0)),
            }
            for node_id, row in sorted(self._node_state.items())
        }
        return {
            "node_count": len(nodes),
            "global": {"epoch": self._global_epoch, "watermark": self._global_watermark},
            "nodes": nodes,
        }

    def load_snapshot(self, payload: Dict[str, Any]) -> None:
        raw_nodes = payload.get("nodes")
        nodes: Dict[str, Dict[str, int]] = {}
        if isinstance(raw_nodes, dict):
            for node_id, row in raw_nodes.items():
                if not isinstance(row, dict):
                    continue
                nodes[str(node_id)] = {
                    "tick": int(row.get("tick", 0)),
                    "epoch": int(row.get("epoch", 0)),
                    "watermark": int(row.get("watermark", 0)),
                }
        self._node_state = nodes
        self._recompute_global_state()


@dataclass
class FileEpochWatermarkCoordinator:
    """File-backed epoch/watermark coordinator for shared-node MVP."""

    state_path: Path
    lock_path: Path | None = None
    lock_timeout_ms: int = 5000
    lock_poll_ms: int = 10
    lock_stale_ms: int | None = 30000
    enforce_monotonic_tick: bool = True
    enforce_monotonic_epoch: bool = True
    enforce_monotonic_watermark: bool = True
    enforce_watermark_le_epoch: bool = True
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def __post_init__(self) -> None:
        self.state_path = Path(self.state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path is None:
            self.lock_path = self.state_path.with_suffix(f"{self.state_path.suffix}.lock")
        else:
            self.lock_path = Path(self.lock_path)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_timeout_ms = max(1, int(self.lock_timeout_ms))
        self.lock_poll_ms = max(1, int(self.lock_poll_ms))
        if self.lock_stale_ms is not None:
            self.lock_stale_ms = max(1, int(self.lock_stale_ms))

    def evaluate_commit(self, packet: CommitPacket) -> EpochDecision:
        with self._lock:
            try:
                with self._file_lock():
                    coordinator = self._load_coordinator()
                    decision = coordinator.evaluate_commit(packet)
                    if bool(decision.accepted):
                        self._store_snapshot(coordinator.snapshot())
                    return decision
            except TimeoutError as exc:
                tick = int(packet.tick_ref.tick)
                epoch = int(commit_epoch(packet))
                watermark = int(commit_watermark(packet))
                return EpochDecision(
                    accepted=False,
                    reason=f"epoch coordinator lock timeout: {exc}",
                    epoch=epoch,
                    watermark=watermark,
                    tick=tick,
                )

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            with self._file_lock():
                coordinator = self._load_coordinator()
                payload = coordinator.snapshot()
                payload["state_path"] = str(self.state_path)
                payload["lock"] = {
                    "lock_path": str(self.lock_path),
                    "timeout_ms": int(self.lock_timeout_ms),
                    "poll_ms": int(self.lock_poll_ms),
                    "stale_ms": None if self.lock_stale_ms is None else int(self.lock_stale_ms),
                }
                return payload

    def _load_coordinator(self) -> InMemoryEpochWatermarkCoordinator:
        coordinator = InMemoryEpochWatermarkCoordinator(
            enforce_monotonic_tick=bool(self.enforce_monotonic_tick),
            enforce_monotonic_epoch=bool(self.enforce_monotonic_epoch),
            enforce_monotonic_watermark=bool(self.enforce_monotonic_watermark),
            enforce_watermark_le_epoch=bool(self.enforce_watermark_le_epoch),
        )
        if not self.state_path.exists():
            return coordinator
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return coordinator
        if isinstance(payload, dict):
            coordinator.load_snapshot(payload)
        return coordinator

    def _store_snapshot(self, payload: Dict[str, Any]) -> None:
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self.state_path)

    @contextlib.contextmanager
    def _file_lock(self) -> Iterator[None]:
        assert self.lock_path is not None
        start = time.monotonic()
        fh: int | None = None
        while fh is None:
            try:
                fh = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                meta = json.dumps({"pid": os.getpid(), "acquired_at_ms": int(time.time() * 1000)})
                os.write(fh, meta.encode("utf-8"))
                break
            except FileExistsError:
                if self._clear_stale_lock_if_needed():
                    continue
                elapsed_ms = (time.monotonic() - start) * 1000.0
                if elapsed_ms >= float(self.lock_timeout_ms):
                    raise TimeoutError(f"lock_path={self.lock_path}")
                time.sleep(float(self.lock_poll_ms) / 1000.0)
        try:
            yield
        finally:
            if fh is not None:
                try:
                    os.close(fh)
                except OSError:
                    pass
            with contextlib.suppress(OSError):
                if self.lock_path.exists():
                    self.lock_path.unlink()

    def _clear_stale_lock_if_needed(self) -> bool:
        if self.lock_stale_ms is None:
            return False
        assert self.lock_path is not None
        try:
            stat = self.lock_path.stat()
        except FileNotFoundError:
            return True
        age_ms = int((time.time() - float(stat.st_mtime)) * 1000.0)
        if age_ms < int(self.lock_stale_ms):
            return False
        with contextlib.suppress(OSError):
            self.lock_path.unlink()
        return not self.lock_path.exists()


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


__all__ = [
    "EpochDecision",
    "FabricEpochCoordinator",
    "FileEpochWatermarkCoordinator",
    "InMemoryEpochWatermarkCoordinator",
    "ReplicatedFileEpochWatermarkCoordinator",
    "commit_epoch",
    "commit_watermark",
]
