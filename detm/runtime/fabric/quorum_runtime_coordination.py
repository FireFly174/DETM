"""Replicated validator-coordination state helpers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def validator_coordination_paths(runtime: Any) -> list[Path]:
    replica_paths = [
        Path(str(path).strip())
        for path in list(getattr(runtime, "validator_coordination_replica_paths", ()) or [])
        if str(path).strip()
    ]
    if replica_paths:
        return replica_paths
    state_path = getattr(runtime, "validator_coordination_state_path", None)
    if state_path is None:
        return []
    text = str(state_path).strip()
    if not text:
        return []
    return [Path(text)]


def validator_coordination_quorums(runtime: Any, replica_count: int) -> tuple[int, int]:
    if int(replica_count) <= 0:
        return 0, 0
    if int(replica_count) == 1:
        return 1, 1
    default_quorum = int(replica_count // 2) + 1
    read_quorum = (
        default_quorum
        if getattr(runtime, "validator_coordination_replica_read_quorum", None) is None
        else int(getattr(runtime, "validator_coordination_replica_read_quorum"))
    )
    write_quorum = (
        default_quorum
        if getattr(runtime, "validator_coordination_replica_write_quorum", None) is None
        else int(getattr(runtime, "validator_coordination_replica_write_quorum"))
    )
    return (
        max(1, min(int(replica_count), int(read_quorum))),
        max(1, min(int(replica_count), int(write_quorum))),
    )


def validator_coordination_snapshot(runtime: Any) -> dict[str, object]:
    paths = validator_coordination_paths(runtime)
    read_quorum, write_quorum = validator_coordination_quorums(runtime, len(paths))
    if len(paths) == 0:
        return {
            "enabled": False,
            "mode": "memory",
            "state_path": None,
            "replica_paths": [],
            "read_quorum": 0,
            "write_quorum": 0,
            "read_quorum_reached": False,
            "write_quorum_reached": False,
            "generation": int(getattr(runtime, "validator_coordination_generation", 0)),
            "last_sync_ts_ms": int(getattr(runtime, "validator_coordination_last_sync_ts_ms", 0)),
            "last_sync_error": getattr(runtime, "validator_coordination_last_sync_error", None),
        }
    return {
        "enabled": True,
        "mode": str(getattr(runtime, "validator_coordination_mode", "memory")),
        "state_path": str(paths[0]) if len(paths) == 1 else None,
        "replica_paths": [str(path) for path in paths] if len(paths) > 1 else [],
        "read_quorum": int(read_quorum),
        "write_quorum": int(write_quorum),
        "read_quorum_reached": bool(getattr(runtime, "validator_coordination_read_quorum_reached", False)),
        "write_quorum_reached": bool(getattr(runtime, "validator_coordination_write_quorum_reached", False)),
        "generation": int(getattr(runtime, "validator_coordination_generation", 0)),
        "last_sync_ts_ms": int(getattr(runtime, "validator_coordination_last_sync_ts_ms", 0)),
        "last_sync_error": getattr(runtime, "validator_coordination_last_sync_error", None),
    }


def load_validator_coordination_state(runtime: Any) -> None:
    paths = validator_coordination_paths(runtime)
    runtime.validator_coordination_mode = "memory" if len(paths) == 0 else ("single_file" if len(paths) == 1 else "replicated")
    if len(paths) == 0:
        return

    rows: list[dict[str, object]] = []
    read_errors: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                rows.append(dict(payload))
        except Exception as exc:
            read_errors.append(f"{path}: {exc}")

    read_quorum, _write_quorum = validator_coordination_quorums(runtime, len(paths))
    reached = bool(len(rows) >= read_quorum)
    if len(paths) == 1:
        reached = bool(len(rows) >= 1)
    runtime.validator_coordination_read_quorum_reached = reached
    if not reached:
        if read_errors:
            runtime.validator_coordination_last_sync_error = "; ".join(read_errors)
        elif len(paths) > 1:
            runtime.validator_coordination_last_sync_error = (
                f"validator coordination read quorum not reached ({len(rows)}/{read_quorum})"
            )
        return
    if not rows:
        return

    rows = sorted(
        rows,
        key=lambda row: (
            int(dict(row).get("generation", 0)),
            int(dict(row).get("updated_at_ms", 0)),
        ),
    )
    payload = dict(rows[-1])
    payload_validator_ids = sorted(str(v) for v in list(payload.get("required_validator_ids", [])))
    current_validator_ids = sorted(str(v) for v in runtime.validator_registry.required_validator_ids())
    if payload_validator_ids and payload_validator_ids != current_validator_ids:
        runtime.validator_coordination_last_sync_error = (
            "validator coordination state validator-set mismatch; ignoring persisted counters"
        )
        return
    hardening = dict(payload.get("membership_hardening_counts", {}))
    runtime.dropped_inactive_validator_total = max(0, int(hardening.get("dropped_inactive_validator_total", 0)))
    runtime.dropped_sender_mismatch_total = max(0, int(hardening.get("dropped_sender_mismatch_total", 0)))
    runtime.dropped_invalid_inline_ack_total = max(0, int(hardening.get("dropped_invalid_inline_ack_total", 0)))
    runtime.dropped_missing_auth_key_id_total = max(0, int(hardening.get("dropped_missing_auth_key_id_total", 0)))
    runtime.dropped_auth_key_id_mismatch_total = max(0, int(hardening.get("dropped_auth_key_id_mismatch_total", 0)))
    runtime.dropped_missing_transport_identity_total = max(
        0,
        int(hardening.get("dropped_missing_transport_identity_total", 0)),
    )
    runtime.dropped_transport_identity_mismatch_total = max(
        0,
        int(hardening.get("dropped_transport_identity_mismatch_total", 0)),
    )
    runtime.validator_coordination_generation = max(0, int(payload.get("generation", 0)))
    runtime.validator_coordination_last_sync_ts_ms = int(time.time() * 1000)
    runtime.validator_coordination_last_sync_error = None


def persist_validator_coordination_state(runtime: Any) -> None:
    paths = validator_coordination_paths(runtime)
    if len(paths) == 0:
        return
    read_quorum, write_quorum = validator_coordination_quorums(runtime, len(paths))
    required_write = 1 if len(paths) == 1 else int(write_quorum)
    now_ms = int(time.time() * 1000)
    next_generation = int(getattr(runtime, "validator_coordination_generation", 0)) + 1
    payload = {
        "schema_version": "detm.fabric.validator_coordination_state.v1",
        "generation": int(next_generation),
        "updated_at_ms": int(now_ms),
        "required_validator_ids": sorted(str(v) for v in runtime.validator_registry.required_validator_ids()),
        "membership_hardening_counts": {
            "dropped_inactive_validator_total": int(runtime.dropped_inactive_validator_total),
            "dropped_sender_mismatch_total": int(runtime.dropped_sender_mismatch_total),
            "dropped_invalid_inline_ack_total": int(runtime.dropped_invalid_inline_ack_total),
            "dropped_missing_auth_key_id_total": int(runtime.dropped_missing_auth_key_id_total),
            "dropped_auth_key_id_mismatch_total": int(runtime.dropped_auth_key_id_mismatch_total),
            "dropped_missing_transport_identity_total": int(runtime.dropped_missing_transport_identity_total),
            "dropped_transport_identity_mismatch_total": int(runtime.dropped_transport_identity_mismatch_total),
        },
    }
    written = 0
    write_errors: list[str] = []
    for path in paths:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(path)
            written += 1
        except Exception as exc:
            write_errors.append(f"{path}: {exc}")

    runtime.validator_coordination_write_quorum_reached = bool(int(written) >= int(required_write))
    if len(paths) == 1:
        runtime.validator_coordination_read_quorum_reached = bool(int(written) >= 1)
    else:
        runtime.validator_coordination_read_quorum_reached = bool(int(written) >= int(read_quorum))
    runtime.validator_coordination_last_sync_ts_ms = int(now_ms)
    if runtime.validator_coordination_write_quorum_reached:
        runtime.validator_coordination_generation = int(next_generation)
        runtime.validator_coordination_last_sync_error = None
    else:
        runtime.validator_coordination_last_sync_error = (
            f"validator coordination write quorum not reached ({written}/{required_write})"
        )
        if write_errors:
            runtime.validator_coordination_last_sync_error += f"; errors: {'; '.join(write_errors)}"


__all__ = [
    "load_validator_coordination_state",
    "persist_validator_coordination_state",
    "validator_coordination_paths",
    "validator_coordination_quorums",
    "validator_coordination_snapshot",
]
