"""File-backed pattern record store."""

from __future__ import annotations

import json
from pathlib import Path

from detm.runtime.pattern_memory.record import PatternRecord


class FilePatternStore:
    """File-backed stub store (single JSON object on disk)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, PatternRecord]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        out: dict[str, PatternRecord] = {}
        for raw in payload.values():
            if not isinstance(raw, dict):
                continue
            record = PatternRecord.from_dict(raw)
            if record.key:
                out[str(record.key)] = record
        return out

    def upsert(self, record: PatternRecord) -> None:
        records = self.load()
        records[str(record.key)] = record
        self._write(records)

    def prune(self, *, error_threshold: float, deviation_threshold: float) -> int:
        records = self.load()
        kept: dict[str, PatternRecord] = {}
        removed = 0
        for key, record in records.items():
            if float(record.error) > float(error_threshold) or float(record.deviation) > float(deviation_threshold):
                removed += 1
                continue
            kept[key] = record
        if removed > 0:
            self._write(kept)
        return int(removed)

    def _write(self, records: dict[str, PatternRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {key: record.to_dict() for key, record in records.items()}
        self.path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = ["FilePatternStore"]
