"""Idempotency helpers for fabric transport ingress deduplication."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from detm.runtime.fabric import FabricEnvelope


def envelope_idempotency_key(envelope: FabricEnvelope) -> str | None:
    """Build a stable idempotency key for transport ingress dedup."""
    delivery_id = str(envelope.delivery_id or "").strip()
    if delivery_id:
        return f"delivery:{delivery_id}"
    commit_ref = str(envelope.commit_ref or "").strip()
    if commit_ref:
        return (
            "commit_ref:"
            + f"{str(envelope.message_type)}|{commit_ref}|{str(envelope.sender)}|"
            + f"{str(envelope.channel)}|{str(envelope.mode)}|{str(envelope.payload_ref)}"
        )
    return None


@dataclass
class EnvelopeIdempotencyCache:
    """Small TTL/LRU cache used to drop duplicate envelopes on ingress."""

    enabled: bool = False
    ttl_ms: int = 30_000
    max_entries: int = 10_000
    seen_total: int = 0
    duplicates_total: int = 0
    _rows: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.ttl_ms = max(1, int(self.ttl_ms))
        self.max_entries = max(1, int(self.max_entries))

    def allow(self, envelope: FabricEnvelope, *, now_ms: int | None = None) -> bool:
        if not bool(self.enabled):
            return True
        key = envelope_idempotency_key(envelope)
        if key is None:
            return True
        now = int(now_ms) if now_ms is not None else int(time.time() * 1000)
        self._evict(now)
        last_seen = self._rows.get(key)
        self._rows[key] = now
        self.seen_total += 1
        if last_seen is None:
            return True
        if (now - int(last_seen)) <= int(self.ttl_ms):
            self.duplicates_total += 1
            return False
        return True

    def snapshot(self) -> dict[str, int | bool]:
        return {
            "enabled": bool(self.enabled),
            "ttl_ms": int(self.ttl_ms),
            "max_entries": int(self.max_entries),
            "pending_keys": len(self._rows),
            "seen_total": int(self.seen_total),
            "duplicates_total": int(self.duplicates_total),
        }

    def _evict(self, now_ms: int) -> None:
        if not self._rows:
            return
        ttl = max(1, int(self.ttl_ms))
        stale = [k for k, ts in list(self._rows.items()) if (int(now_ms) - int(ts)) > ttl]
        for key in stale:
            self._rows.pop(key, None)
        overflow = len(self._rows) - int(self.max_entries)
        if overflow <= 0:
            return
        oldest = sorted(self._rows.items(), key=lambda item: int(item[1]))[:overflow]
        for key, _ts in oldest:
            self._rows.pop(key, None)


__all__ = ["EnvelopeIdempotencyCache", "envelope_idempotency_key"]
