from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict

import numpy as np

def _trace_ref_for_tick(tick: int) -> str:
    return f"trace://L0/{int(tick)}"

def _snapshot_digest(get_state_blob: Any | None) -> Dict[str, Any]:
    if not callable(get_state_blob):
        return {}
    blob = get_state_blob()
    if not isinstance(blob, (bytes, bytearray)):
        return {}
    return {
        "snapshot_sha256": hashlib.sha256(bytes(blob)).hexdigest(),
        "snapshot_bytes": int(len(blob)),
    }

def _tail_limit(path: Path, *, max_entries: int) -> None:
    limit = max(0, int(max_entries))
    if limit <= 0 or not path.exists():
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) <= limit:
        return
    path.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")

def _effective_storage_limit(*, retention_window: int, compaction_budget: int) -> int:
    retention = max(0, int(retention_window))
    budget = max(0, int(compaction_budget))
    if retention > 0 and budget > 0:
        return min(retention, budget)
    return max(retention, budget)

def _to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)
