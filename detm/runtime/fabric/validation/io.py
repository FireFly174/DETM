"""I/O helpers for commit validation inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

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


__all__ = ["load_commit_packets"]
