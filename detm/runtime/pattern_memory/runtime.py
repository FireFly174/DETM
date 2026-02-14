"""Pattern memory runtime orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from detm.runtime.pattern_memory.cache import PatternCache
from detm.runtime.pattern_memory.flow import (
    compute_pattern_key as _compute_pattern_key_flow,
    extract_patch as _extract_patch_flow,
    is_reusable_record as _is_reusable_record_flow,
    lookup_candidates as _lookup_candidates_flow,
    normalize_context_token as _normalize_context_token_flow,
    remember_key as _remember_key_flow,
    runtime_key_from_config as _runtime_key_from_config_flow,
    scoped_key as _scoped_key_flow,
)
from detm.runtime.pattern_memory.record import PatternRecord
from detm.runtime.pattern_memory.scope import normalize_reuse_scope
from detm.runtime.pattern_memory.store import FilePatternStore


class PatternMemoryRuntime:
    def __init__(
        self,
        *,
        reuse_enabled: bool,
        cache_capacity: int,
        cache_ttl_steps: int,
        prune_error_threshold: float,
        prune_deviation_threshold: float,
        reuse_scope: str,
        store_path: str | None,
    ) -> None:
        self.reuse_enabled = bool(reuse_enabled)
        self.reuse_scope = normalize_reuse_scope(reuse_scope)
        self.prune_error_threshold = float(prune_error_threshold)
        self.prune_deviation_threshold = float(prune_deviation_threshold)
        self.cache = PatternCache(capacity=max(1, int(cache_capacity)), ttl_steps=max(1, int(cache_ttl_steps)))
        self.store = (
            None
            if store_path is None or not str(store_path).strip()
            else FilePatternStore(Path(str(store_path).strip()))
        )
        if self.store is not None:
            for record in self.store.load().values():
                self.cache.put(record)

    def make_key(self, *, energy: np.ndarray, center_x: int, center_y: int, radius: int, boundary: str) -> str:
        return _compute_pattern_key_flow(
            energy=energy,
            center_x=int(center_x),
            center_y=int(center_y),
            radius=int(radius),
            boundary=str(boundary),
        )

    def lookup(self, *, key: str, step_count: int) -> PatternRecord | None:
        return self.lookup_with_scope(
            key=key,
            step_count=step_count,
            level="L0",
            mode="minimal",
        )

    def lookup_with_scope(
        self,
        *,
        key: str,
        step_count: int,
        level: str,
        mode: str,
    ) -> PatternRecord | None:
        base_key = str(key)
        candidates = self._lookup_candidates(base_key=base_key, level=str(level), mode=str(mode))
        loaded_map: dict[str, PatternRecord] | None = None
        for candidate in candidates:
            record = self.cache.get(candidate, step_count=int(step_count))
            if record is not None and self._is_reusable_record(record):
                return record
            if record is not None:
                self.prune()
                continue
            if self.store is None:
                continue
            if loaded_map is None:
                loaded_map = self.store.load()
            loaded = loaded_map.get(candidate)
            if loaded is None:
                continue
            if not self._is_reusable_record(loaded):
                self.prune()
                continue
            self.cache.put(loaded)
            return loaded
        return None

    def remember(
        self,
        *,
        key: str,
        blend: float,
        error: float,
        deviation: float,
        step_count: int,
        base_hits: int = 0,
        level: str = "L0",
        mode: str = "minimal",
    ) -> PatternRecord:
        remembered_key = self._remember_key(base_key=str(key), level=str(level), mode=str(mode))
        record = PatternRecord(
            key=remembered_key,
            blend=float(blend),
            error=float(error),
            deviation=float(deviation),
            hits=max(1, int(base_hits) + 1),
            updated_step=max(0, int(step_count)),
        )
        self.cache.put(record)
        if self.store is not None:
            self.store.upsert(record)
        self.prune()
        return record

    def prune(self) -> int:
        removed = self.cache.prune(
            error_threshold=float(self.prune_error_threshold),
            deviation_threshold=float(self.prune_deviation_threshold),
        )
        if self.store is not None:
            removed += self.store.prune(
                error_threshold=float(self.prune_error_threshold),
                deviation_threshold=float(self.prune_deviation_threshold),
            )
        return int(removed)

    def cache_size(self) -> int:
        return int(len(self.cache))

    def _is_reusable_record(self, record: PatternRecord) -> bool:
        return _is_reusable_record_flow(
            record=record,
            prune_error_threshold=float(self.prune_error_threshold),
            prune_deviation_threshold=float(self.prune_deviation_threshold),
        )

    @staticmethod
    def _normalize_context_token(value: str) -> str:
        return _normalize_context_token_flow(value)

    def _scoped_key(self, *, base_key: str, level: str, mode: str) -> str:
        return _scoped_key_flow(base_key=base_key, level=level, mode=mode)

    def _lookup_candidates(self, *, base_key: str, level: str, mode: str) -> tuple[str, ...]:
        return _lookup_candidates_flow(
            base_key=base_key,
            level=level,
            mode=mode,
            scope=str(self.reuse_scope),
        )

    def _remember_key(self, *, base_key: str, level: str, mode: str) -> str:
        return _remember_key_flow(
            base_key=base_key,
            level=level,
            mode=mode,
            scope=str(self.reuse_scope),
        )

    @staticmethod
    def _extract_patch(energy: np.ndarray, *, center_x: int, center_y: int, radius: int, boundary: str) -> np.ndarray:
        return _extract_patch_flow(
            energy,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            boundary=boundary,
        )


def get_pattern_runtime_for_state(*, state: Any, config: Any) -> PatternMemoryRuntime:
    runtime_key = _runtime_key_from_config_flow(config)
    existing = getattr(state, "_pattern_runtime", None)
    existing_key = getattr(state, "_pattern_runtime_key", None)
    if existing is not None and existing_key == runtime_key:
        return existing

    runtime = PatternMemoryRuntime(
        reuse_enabled=bool(runtime_key[0]),
        reuse_scope=str(runtime_key[1]),
        cache_capacity=int(runtime_key[2]),
        cache_ttl_steps=int(runtime_key[3]),
        prune_error_threshold=float(runtime_key[4]),
        prune_deviation_threshold=float(runtime_key[5]),
        store_path=runtime_key[6],
    )
    setattr(state, "_pattern_runtime", runtime)
    setattr(state, "_pattern_runtime_key", runtime_key)
    return runtime


__all__ = ["PatternMemoryRuntime", "get_pattern_runtime_for_state"]
