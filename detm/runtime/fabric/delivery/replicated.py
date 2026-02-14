"""Replicated file-backed outbox queue with read/write quorum."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric.delivery.contracts import PublishFunc
from detm.runtime.fabric.delivery.outbox import JsonlFabricEnvelopeOutbox


@dataclass
class ReplicatedJsonlFabricEnvelopeOutbox:
    """Replicate outbox state across multiple files with quorum-based access."""

    paths: Sequence[Path | str]
    read_quorum: int | None = None
    write_quorum: int | None = None
    max_entries: int | None = None
    drop_policy: str | None = None
    drop_oldest: bool = True
    _replicas: List[Tuple[Path, JsonlFabricEnvelopeOutbox]] = field(default_factory=list)

    def __post_init__(self) -> None:
        normalized_paths: List[Path] = []
        seen: set[str] = set()
        for raw in list(self.paths or []):
            path = Path(raw)
            key = str(path.resolve()) if path.is_absolute() else str(path)
            if key in seen:
                continue
            seen.add(key)
            normalized_paths.append(path)
        if not normalized_paths:
            raise ValueError("paths must contain at least one replica path")

        self._replicas = [
            (
                path,
                JsonlFabricEnvelopeOutbox(
                    path=path,
                    max_entries=self.max_entries,
                    drop_policy=self.drop_policy,
                    drop_oldest=bool(self.drop_oldest),
                ),
            )
            for path in normalized_paths
        ]

        replica_count = len(self._replicas)
        default_quorum = (replica_count // 2) + 1
        rq = default_quorum if self.read_quorum is None else int(self.read_quorum)
        wq = default_quorum if self.write_quorum is None else int(self.write_quorum)
        self.read_quorum = min(replica_count, max(1, rq))
        self.write_quorum = min(replica_count, max(1, wq))

    def enqueue(self, envelope: FabricEnvelope, *, error: str | None = None) -> None:
        ok = 0
        last_error: Exception | None = None
        for _path, replica in list(self._replicas):
            try:
                replica.enqueue(envelope, error=error)
                ok += 1
            except Exception as exc:  # pragma: no cover - filesystem failure branch
                last_error = exc
        if ok < int(self.write_quorum or 1):
            if last_error is None:
                raise RuntimeError(
                    f"outbox write quorum not reached: ok={ok}, required={int(self.write_quorum or 1)}"
                )
            raise RuntimeError(
                f"outbox write quorum not reached: ok={ok}, required={int(self.write_quorum or 1)}; last_error={last_error}"
            ) from last_error

    def flush(self, publish: PublishFunc, *, max_items: int | None = None) -> Dict[str, int]:
        source = self._select_read_replica()
        if source is None:
            return {
                "sent": 0,
                "failed": 1,
                "remaining": 0,
                "dropped": 0,
                "read_quorum_reached": 0,
                "write_quorum_reached": 0,
                "replica_write_ok": 0,
            }

        src_path, src_replica = source
        report = src_replica.flush(publish, max_items=max_items)
        write_ok = self._replicate_state_from_source(src_path)
        out = {str(k): int(v) for k, v in dict(report).items()}
        out["read_quorum_reached"] = 1
        out["replica_write_ok"] = int(write_ok)
        out["write_quorum_reached"] = 1 if write_ok >= int(self.write_quorum or 1) else 0
        if out["write_quorum_reached"] == 0:
            out["failed"] = int(out.get("failed", 0)) + 1
        return out

    def snapshot(self) -> Dict[str, object]:
        rows: List[Dict[str, object]] = []
        reachable = 0
        for path, replica in list(self._replicas):
            try:
                snap = replica.snapshot()
                reachable += 1
                rows.append(
                    {
                        "path": str(path),
                        "reachable": True,
                        "pending_count": int(snap.get("pending_count", 0)),
                    }
                )
            except Exception as exc:  # pragma: no cover - filesystem failure branch
                rows.append(
                    {
                        "path": str(path),
                        "reachable": False,
                        "error": str(exc),
                        "pending_count": 0,
                    }
                )

        source = self._select_read_replica()
        source_snapshot: Dict[str, object] = {}
        if source is not None:
            _, replica = source
            try:
                source_snapshot = replica.snapshot()
            except Exception:
                source_snapshot = {}
        return {
            "mode": "replicated",
            "replica_count": len(self._replicas),
            "reachable": int(reachable),
            "read_quorum": int(self.read_quorum or 0),
            "write_quorum": int(self.write_quorum or 0),
            "read_quorum_reached": bool(reachable >= int(self.read_quorum or 1)),
            "pending_count": int(source_snapshot.get("pending_count", 0)),
            "max_entries": source_snapshot.get("max_entries", self.max_entries),
            "drop_policy": source_snapshot.get("drop_policy", self.drop_policy),
            "enqueue_total": int(source_snapshot.get("enqueue_total", 0)),
            "flushed_total": int(source_snapshot.get("flushed_total", 0)),
            "dropped_total": int(source_snapshot.get("dropped_total", 0)),
            "dropped_by_mode": dict(source_snapshot.get("dropped_by_mode", {}))
            if isinstance(source_snapshot.get("dropped_by_mode"), dict)
            else {"realtime": 0, "audit": 0, "unknown": 0},
            "replicas": rows,
        }

    def _select_read_replica(self) -> Tuple[Path, JsonlFabricEnvelopeOutbox] | None:
        reachable: List[Tuple[Path, JsonlFabricEnvelopeOutbox]] = []
        for path, replica in list(self._replicas):
            try:
                replica.snapshot()
                reachable.append((path, replica))
            except Exception:  # pragma: no cover - filesystem failure branch
                continue
        if len(reachable) < int(self.read_quorum or 1):
            return None
        return reachable[0]

    def _replicate_state_from_source(self, src_path: Path) -> int:
        try:
            body = src_path.read_text(encoding="utf-8")
        except Exception:  # pragma: no cover - filesystem failure branch
            body = ""
        write_ok = 0
        for path, _replica in list(self._replicas):
            try:
                if path == src_path:
                    write_ok += 1
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
                write_ok += 1
            except Exception:  # pragma: no cover - filesystem failure branch
                continue
        return int(write_ok)


__all__ = ["ReplicatedJsonlFabricEnvelopeOutbox"]
