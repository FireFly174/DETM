"""Validation checks for commit streams and proofs."""

from __future__ import annotations

from typing import Any, Dict, Sequence

from detm.runtime.commit_packet import CommitPacket


def validate_commit_chain(
    packets: Sequence[CommitPacket],
    *,
    expected_mode: str | None = None,
    expected_commit_type: str | None = None,
) -> Dict[str, Any]:
    issues: list[str] = []
    seen_ids: set[str] = set()
    prev_commit_id: str | None = None
    prev_tick: int | None = None

    for idx, packet in enumerate(packets):
        if expected_mode is not None and packet.mode != expected_mode:
            issues.append(f"entry[{idx}] mode={packet.mode} != {expected_mode}")
        if expected_commit_type is not None and packet.commit_type != expected_commit_type:
            issues.append(f"entry[{idx}] commit_type={packet.commit_type} != {expected_commit_type}")
        if packet.commit_id in seen_ids:
            issues.append(f"entry[{idx}] duplicate commit_id={packet.commit_id}")
        seen_ids.add(packet.commit_id)

        if prev_commit_id is None:
            if packet.parent_ref is not None:
                issues.append(f"entry[{idx}] first parent_ref must be null")
        else:
            if packet.parent_ref != prev_commit_id:
                issues.append(
                    f"entry[{idx}] broken parent chain: expected {prev_commit_id}, got {packet.parent_ref}"
                )
        prev_commit_id = packet.commit_id

        tick = int(packet.tick_ref.tick)
        if prev_tick is not None and tick <= prev_tick:
            issues.append(f"entry[{idx}] tick must be strictly increasing: prev={prev_tick}, got={tick}")
        prev_tick = tick

        if not str(packet.trace_ref).startswith("trace://"):
            issues.append(f"entry[{idx}] trace_ref must start with trace://")

    return {
        "count": len(packets),
        "last_tick": None if not packets else int(packets[-1].tick_ref.tick),
        "ok": len(issues) == 0,
        "issues": issues,
    }


def validate_audit_proofs(packets: Sequence[CommitPacket]) -> Dict[str, Any]:
    issues: list[str] = []
    for idx, packet in enumerate(packets):
        summary = dict(packet.summary)
        if packet.invariants_ref is None:
            issues.append(f"entry[{idx}] proof commit missing invariants_ref")
        digest = summary.get("snapshot_sha256")
        if not isinstance(digest, str) or len(digest.strip()) == 0:
            issues.append(f"entry[{idx}] audit summary missing snapshot_sha256")
        size = summary.get("snapshot_bytes")
        if not isinstance(size, int) or size <= 0:
            issues.append(f"entry[{idx}] audit summary missing positive snapshot_bytes")
    return {"ok": len(issues) == 0, "issues": issues}


def compute_epoch_watermark(
    realtime_last_tick: int | None,
    audit_last_tick: int | None,
) -> Dict[str, Any]:
    if realtime_last_tick is None and audit_last_tick is None:
        return {"tick": None, "epoch": None, "lag_realtime_vs_audit": None}
    if audit_last_tick is None:
        watermark_tick = int(realtime_last_tick) if realtime_last_tick is not None else None
        return {"tick": watermark_tick, "epoch": watermark_tick, "lag_realtime_vs_audit": None}
    if realtime_last_tick is None:
        watermark_tick = int(audit_last_tick)
        return {"tick": watermark_tick, "epoch": watermark_tick, "lag_realtime_vs_audit": 0}

    rt = int(realtime_last_tick)
    au = int(audit_last_tick)
    watermark_tick = min(rt, au)
    return {"tick": watermark_tick, "epoch": watermark_tick, "lag_realtime_vs_audit": rt - au}


__all__ = ["compute_epoch_watermark", "validate_audit_proofs", "validate_commit_chain"]
