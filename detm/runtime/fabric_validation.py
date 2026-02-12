"""Validation helpers for commit streams and local fabric watermark."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from detm.runtime.commit_packet import CommitPacket


def load_commit_packets(path: Path) -> Tuple[List[CommitPacket], List[str]]:
    """Load commit packets from jsonl, collecting parse/validation issues."""

    packets: List[CommitPacket] = []
    issues: List[str] = []
    if not path.exists():
        return packets, issues

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception as exc:
            issues.append(f"{path.name}:{lineno}: invalid json ({exc})")
            continue
        if not isinstance(payload, dict):
            issues.append(f"{path.name}:{lineno}: payload must be object")
            continue
        try:
            packets.append(CommitPacket.from_dict(payload))
        except Exception as exc:
            issues.append(f"{path.name}:{lineno}: invalid commit packet ({exc})")
    return packets, issues


def validate_commit_chain(
    packets: Sequence[CommitPacket],
    *,
    expected_mode: str | None = None,
    expected_commit_type: str | None = None,
) -> Dict[str, Any]:
    issues: List[str] = []
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
    issues: List[str] = []
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


def build_local_fabric_validation_report(
    *,
    realtime_packets: Sequence[CommitPacket],
    audit_packets: Sequence[CommitPacket],
    parse_issues: Iterable[str] = (),
) -> Dict[str, Any]:
    parse_issues_list = [str(x) for x in parse_issues]

    realtime = validate_commit_chain(realtime_packets, expected_mode="realtime", expected_commit_type="state")
    audit = validate_commit_chain(audit_packets, expected_mode="audit", expected_commit_type="proof")
    audit_proofs = validate_audit_proofs(audit_packets)
    watermark = compute_epoch_watermark(
        realtime_last_tick=realtime.get("last_tick"),
        audit_last_tick=audit.get("last_tick"),
    )

    issues = parse_issues_list + list(realtime.get("issues", [])) + list(audit.get("issues", [])) + list(
        audit_proofs.get("issues", [])
    )
    return {
        "status": "ok" if len(issues) == 0 else "error",
        "issues": issues,
        "streams": {
            "realtime": {
                "count": int(realtime.get("count", 0)),
                "last_tick": realtime.get("last_tick"),
                "ok": bool(realtime.get("ok", False)),
            },
            "audit": {
                "count": int(audit.get("count", 0)),
                "last_tick": audit.get("last_tick"),
                "ok_chain": bool(audit.get("ok", False)),
                "ok_proofs": bool(audit_proofs.get("ok", False)),
            },
        },
        "watermark": watermark,
    }


def validate_commit_paths(
    *,
    realtime_path: Path,
    audit_path: Path,
) -> Dict[str, Any]:
    rt_packets, rt_parse_issues = load_commit_packets(realtime_path)
    au_packets, au_parse_issues = load_commit_packets(audit_path)
    return build_local_fabric_validation_report(
        realtime_packets=rt_packets,
        audit_packets=au_packets,
        parse_issues=[*rt_parse_issues, *au_parse_issues],
    )


__all__ = [
    "build_local_fabric_validation_report",
    "compute_epoch_watermark",
    "load_commit_packets",
    "validate_audit_proofs",
    "validate_commit_chain",
    "validate_commit_paths",
]
