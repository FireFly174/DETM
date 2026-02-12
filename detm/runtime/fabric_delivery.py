"""Delivery outbox primitives for fabric envelopes."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Protocol

from detm.runtime.fabric_envelope import FabricEnvelope

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 1 (durable queue abstraction exists, no distributed replication yet)
# - OOP_TECH_DEBT: replicated outbox, transactional fs writes, and transport-level exactly-once semantics


PublishFunc = Callable[[FabricEnvelope], int]
OUTBOX_DROP_POLICIES = {"oldest", "newest", "audit_first"}


class FabricEnvelopeOutbox(Protocol):
    """Persistent envelope outbox abstraction for retry/flush workflows."""

    def enqueue(self, envelope: FabricEnvelope, *, error: str | None = None) -> None:
        ...

    def flush(self, publish: PublishFunc, *, max_items: int | None = None) -> Dict[str, int]:
        ...

    def snapshot(self) -> Dict[str, object]:
        ...


def _coerce_non_negative_int(value: object, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return int(default)
    return max(0, parsed)


@dataclass
class JsonlFabricEnvelopeOutbox:
    """Simple file-backed outbox queue for envelope replay."""

    path: Path
    max_entries: int | None = None
    drop_policy: str | None = None
    drop_oldest: bool = True
    _dropped_total: int = 0
    _dropped_realtime: int = 0
    _dropped_audit: int = 0
    _dropped_unknown: int = 0
    _flushed_total: int = 0
    _enqueue_total: int = 0

    def enqueue(self, envelope: FabricEnvelope, *, error: str | None = None) -> None:
        entries = self._load_entries()
        row = {
            "enqueued_at_ms": int(time.time() * 1000),
            "attempts": 0,
            "last_error": None if error is None else str(error),
            "envelope": envelope.to_dict(),
        }
        entries.append(row)
        entries = self._apply_capacity(entries)
        self._save_entries(entries)
        self._enqueue_total += 1

    def flush(self, publish: PublishFunc, *, max_items: int | None = None) -> Dict[str, int]:
        entries = self._load_entries()
        if not entries:
            return {
                "sent": 0,
                "failed": 0,
                "remaining": 0,
                "dropped": int(self._dropped_total),
            }

        if max_items is not None:
            budget = max(0, int(max_items))
        else:
            budget = len(entries)
        if budget == 0:
            return {
                "sent": 0,
                "failed": 0,
                "remaining": len(entries),
                "dropped": int(self._dropped_total),
            }

        sent = 0
        failed = 0
        remaining: List[dict] = []
        consumed = 0
        for row in entries:
            if consumed >= budget:
                remaining.append(row)
                continue
            consumed += 1
            raw_env = row.get("envelope", {})
            try:
                envelope = FabricEnvelope.from_dict(raw_env if isinstance(raw_env, dict) else {})
            except Exception as exc:
                row["attempts"] = _coerce_non_negative_int(row.get("attempts"), default=0) + 1
                row["last_error"] = f"invalid envelope in outbox: {exc}"
                row["last_attempt_ms"] = int(time.time() * 1000)
                remaining.append(row)
                failed += 1
                continue

            try:
                delivered = int(publish(envelope))
                if delivered <= 0:
                    raise RuntimeError("transport publish returned 0 (dropped)")
            except Exception as exc:
                row["attempts"] = _coerce_non_negative_int(row.get("attempts"), default=0) + 1
                row["last_error"] = str(exc)
                row["last_attempt_ms"] = int(time.time() * 1000)
                remaining.append(row)
                failed += 1
            else:
                sent += 1
                self._flushed_total += 1

        remaining = self._apply_capacity(remaining)
        self._save_entries(remaining)
        return {
            "sent": sent,
            "failed": failed,
            "remaining": len(remaining),
            "dropped": int(self._dropped_total),
        }

    def snapshot(self) -> Dict[str, object]:
        entries = self._load_entries()
        return {
            "path": str(self.path),
            "pending_count": len(entries),
            "max_entries": None if self.max_entries is None else int(self.max_entries),
            "drop_policy": self._normalized_drop_policy(),
            "enqueue_total": int(self._enqueue_total),
            "flushed_total": int(self._flushed_total),
            "dropped_total": int(self._dropped_total),
            "dropped_by_mode": {
                "realtime": int(self._dropped_realtime),
                "audit": int(self._dropped_audit),
                "unknown": int(self._dropped_unknown),
            },
        }

    def _apply_capacity(self, entries: List[dict]) -> List[dict]:
        if self.max_entries is None:
            return entries
        cap = max(1, int(self.max_entries))
        if len(entries) <= cap:
            return entries
        overflow = len(entries) - cap
        if overflow <= 0:
            return entries
        policy = self._normalized_drop_policy()
        if policy == "newest":
            dropped = list(entries[cap:])
            kept = list(entries[:cap])
            self._register_drops(dropped)
            return kept
        if policy == "audit_first":
            kept, dropped = self._drop_audit_first(entries, overflow)
            self._register_drops(dropped)
            return kept
        dropped = list(entries[:overflow])
        kept = list(entries[overflow:])
        self._register_drops(dropped)
        return kept

    def _normalized_drop_policy(self) -> str:
        if self.drop_policy is not None:
            policy = str(self.drop_policy).strip().lower()
            if policy in OUTBOX_DROP_POLICIES:
                return policy
        return "oldest" if bool(self.drop_oldest) else "newest"

    def _drop_audit_first(self, entries: List[dict], overflow: int) -> tuple[List[dict], List[dict]]:
        kept = list(entries)
        dropped: List[dict] = []
        remaining = max(0, int(overflow))
        if remaining <= 0:
            return kept, dropped

        idx = 0
        while remaining > 0 and idx < len(kept):
            mode = self._row_mode(kept[idx])
            if mode == "audit":
                dropped.append(kept.pop(idx))
                remaining -= 1
                continue
            idx += 1
        if remaining > 0:
            dropped.extend(kept[:remaining])
            kept = kept[remaining:]
        return kept, dropped

    def _row_mode(self, row: dict) -> str:
        envelope = row.get("envelope")
        if not isinstance(envelope, dict):
            return "unknown"
        mode = str(envelope.get("mode", "")).strip().lower()
        if mode == "realtime":
            return "realtime"
        if mode == "audit":
            return "audit"
        return "unknown"

    def _register_drops(self, rows: List[dict]) -> None:
        self._dropped_total += len(rows)
        for row in list(rows):
            mode = self._row_mode(row)
            if mode == "realtime":
                self._dropped_realtime += 1
            elif mode == "audit":
                self._dropped_audit += 1
            else:
                self._dropped_unknown += 1

    def _load_entries(self) -> List[dict]:
        if not self.path.exists():
            return []
        rows: List[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(dict(row))
        return rows

    def _save_entries(self, entries: List[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = "\n".join(json.dumps(row, ensure_ascii=False) for row in list(entries))
        self.path.write_text(body, encoding="utf-8")


__all__ = ["FabricEnvelopeOutbox", "JsonlFabricEnvelopeOutbox", "OUTBOX_DROP_POLICIES", "PublishFunc"]
