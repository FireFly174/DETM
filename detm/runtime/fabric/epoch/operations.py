"""Shared epoch/watermark extraction helpers."""

from __future__ import annotations

from detm.runtime.commit_packet import CommitPacket


def commit_epoch(packet: CommitPacket) -> int:
    summary = dict(packet.summary or {})
    raw = summary.get("epoch", packet.tick_ref.tick)
    return max(0, int(raw))


def commit_watermark(packet: CommitPacket) -> int:
    summary = dict(packet.summary or {})
    raw = summary.get("watermark", packet.tick_ref.tick)
    return max(0, int(raw))


__all__ = ["commit_epoch", "commit_watermark"]
