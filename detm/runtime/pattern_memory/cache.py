"""In-memory LRU/TTL cache for pattern records."""

from __future__ import annotations

from collections import OrderedDict

from detm.runtime.pattern_memory.record import PatternRecord


class PatternCache:
    def __init__(self, *, capacity: int, ttl_steps: int) -> None:
        self.capacity = max(1, int(capacity))
        self.ttl_steps = max(1, int(ttl_steps))
        self._records: "OrderedDict[str, PatternRecord]" = OrderedDict()

    def get(self, key: str, *, step_count: int) -> PatternRecord | None:
        self._expire(step_count=step_count)
        if key not in self._records:
            return None
        record = self._records.pop(key)
        self._records[key] = record
        return record

    def put(self, record: PatternRecord) -> None:
        key = str(record.key)
        if key in self._records:
            self._records.pop(key)
        self._records[key] = record
        while len(self._records) > self.capacity:
            self._records.popitem(last=False)

    def prune(self, *, error_threshold: float, deviation_threshold: float) -> int:
        removed = 0
        keys = list(self._records.keys())
        for key in keys:
            record = self._records[key]
            if float(record.error) > float(error_threshold) or float(record.deviation) > float(deviation_threshold):
                self._records.pop(key, None)
                removed += 1
        return int(removed)

    def __len__(self) -> int:
        return int(len(self._records))

    def _expire(self, *, step_count: int) -> None:
        keys = list(self._records.keys())
        for key in keys:
            record = self._records[key]
            age = int(step_count) - int(record.updated_step)
            if age > self.ttl_steps:
                self._records.pop(key, None)


__all__ = ["PatternCache"]
