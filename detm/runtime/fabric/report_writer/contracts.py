"""Contracts and helper primitives for runtime fabric report writer."""

from __future__ import annotations

from typing import Protocol


class DeadLetterSource(Protocol):
    @property
    def dead_letters(self) -> list[dict[str, str]]:
        ...


def effective_storage_limit(*, retention_window: int, compaction_budget: int) -> int:
    retention = max(0, int(retention_window))
    budget = max(0, int(compaction_budget))
    if retention > 0 and budget > 0:
        return min(retention, budget)
    return max(retention, budget)


__all__ = ["DeadLetterSource", "effective_storage_limit"]
