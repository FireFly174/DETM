"""Report composition for local fabric validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric.validation.checks import (
    compute_epoch_watermark,
    validate_audit_proofs,
    validate_commit_chain,
)
from detm.runtime.fabric.validation.io import load_commit_packets


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


__all__ = ["build_local_fabric_validation_report", "validate_commit_paths"]

