"""Generic migration graph helpers for state payload versions."""

from __future__ import annotations

from collections import deque
from typing import Callable, Dict, TypeVar

TPayload = TypeVar("TPayload", bound=dict)
MigrationAdapter = Callable[[TPayload], TPayload]
MigrationRegistry = Dict[tuple[str, str], MigrationAdapter]


def register_migration(registry: MigrationRegistry, from_version: str, to_version: str):
    def _decorator(fn: MigrationAdapter) -> MigrationAdapter:
        registry[(str(from_version), str(to_version))] = fn
        return fn

    return _decorator


def migration_path(registry: MigrationRegistry, *, from_version: str, to_version: str) -> list[tuple[str, str]]:
    if str(from_version) == str(to_version):
        return []

    queue: deque[str] = deque([str(from_version)])
    prev: dict[str, tuple[str, str] | None] = {str(from_version): None}
    while queue:
        current = queue.popleft()
        for edge_from, edge_to in registry.keys():
            if edge_from != current:
                continue
            if edge_to in prev:
                continue
            prev[edge_to] = (edge_from, edge_to)
            if edge_to == str(to_version):
                queue.clear()
                break
            queue.append(edge_to)

    if str(to_version) not in prev:
        raise ValueError(f"no state migration path: {from_version} -> {to_version}")

    edges: list[tuple[str, str]] = []
    cursor = str(to_version)
    while True:
        edge = prev.get(cursor)
        if edge is None:
            break
        edges.append(edge)
        cursor = edge[0]
    edges.reverse()
    return edges


def migrate_payload(
    payload: TPayload,
    *,
    from_version: str,
    to_version: str,
    registry: MigrationRegistry,
) -> TPayload:
    out = dict(payload)
    for edge in migration_path(registry, from_version=from_version, to_version=to_version):
        adapter = registry.get(edge)
        if adapter is None:
            raise ValueError(f"missing migration adapter: {edge[0]} -> {edge[1]}")
        out = adapter(out)  # type: ignore[assignment]
    return out  # type: ignore[return-value]


__all__ = ["MigrationAdapter", "MigrationRegistry", "migrate_payload", "migration_path", "register_migration"]
