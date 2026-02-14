"""Pattern memory runtime orchestration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from detm.runtime.pattern_memory.cache import PatternCache
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
        patch = self._extract_patch(
            energy=energy,
            center_x=int(center_x),
            center_y=int(center_y),
            radius=int(radius),
            boundary=str(boundary),
        )
        quant = np.round(np.asarray(patch, dtype=float), 3)
        digest = hashlib.sha1()
        digest.update(quant.tobytes())
        digest.update(f"|r={int(radius)}|b={str(boundary)}".encode("utf-8"))
        return digest.hexdigest()

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
        return bool(
            float(record.error) <= float(self.prune_error_threshold)
            and float(record.deviation) <= float(self.prune_deviation_threshold)
        )

    @staticmethod
    def _normalize_context_token(value: str) -> str:
        token = str(value or "").strip()
        if not token:
            return "*"
        # Prevent delimiter collisions in serialized scoped keys.
        return token.replace("|", "/")

    def _scoped_key(self, *, base_key: str, level: str, mode: str) -> str:
        level_token = self._normalize_context_token(level)
        mode_token = self._normalize_context_token(mode)
        return f"lvl={level_token}|mode={mode_token}|{str(base_key)}"

    def _lookup_candidates(self, *, base_key: str, level: str, mode: str) -> tuple[str, ...]:
        scope = str(self.reuse_scope)
        exact = self._scoped_key(base_key=base_key, level=level, mode=mode)
        level_wild = self._scoped_key(base_key=base_key, level=level, mode="*")
        mode_wild = self._scoped_key(base_key=base_key, level="*", mode=mode)
        global_scoped = self._scoped_key(base_key=base_key, level="*", mode="*")
        legacy = str(base_key)
        out: list[str] = []

        def _push(value: str) -> None:
            if value not in out:
                out.append(value)

        if scope == "global":
            _push(legacy)
            _push(global_scoped)
            _push(exact)
            return tuple(out)

        _push(exact)
        if scope == "portable":
            _push(level_wild)
            _push(mode_wild)
            _push(global_scoped)
            _push(legacy)
            return tuple(out)

        # strict scope: exact scoped key plus legacy compatibility fallback.
        _push(legacy)
        return tuple(out)

    def _remember_key(self, *, base_key: str, level: str, mode: str) -> str:
        scope = str(self.reuse_scope)
        if scope == "global":
            return str(base_key)
        if scope == "portable":
            return self._scoped_key(base_key=base_key, level="*", mode="*")
        return self._scoped_key(base_key=base_key, level=level, mode=mode)

    @staticmethod
    def _extract_patch(energy: np.ndarray, *, center_x: int, center_y: int, radius: int, boundary: str) -> np.ndarray:
        h, w = int(energy.shape[0]), int(energy.shape[1])
        r = max(0, int(radius))
        if r <= 0:
            return np.asarray([[float(energy[center_y % h, center_x % w])]], dtype=float)
        if str(boundary) == "periodic":
            ys = (np.arange(center_y - r, center_y + r + 1, dtype=np.int32) % h).astype(np.int64)
            xs = (np.arange(center_x - r, center_x + r + 1, dtype=np.int32) % w).astype(np.int64)
            return np.asarray(energy[np.ix_(ys, xs)], dtype=float)
        padded = np.pad(np.asarray(energy, dtype=float), ((r, r), (r, r)), mode="edge")
        yy = int(center_y) + r
        xx = int(center_x) + r
        return np.asarray(padded[yy - r : yy + r + 1, xx - r : xx + r + 1], dtype=float)


def get_pattern_runtime_for_state(*, state: Any, config: Any) -> PatternMemoryRuntime:
    runtime_key = (
        bool(getattr(config, "pattern_reuse_enabled", True)),
        normalize_reuse_scope(getattr(config, "pattern_reuse_scope", "portable")),
        int(getattr(config, "pattern_cache_capacity", 128)),
        int(getattr(config, "pattern_cache_ttl_steps", 4096)),
        float(getattr(config, "pattern_prune_error_threshold", 0.05)),
        float(getattr(config, "pattern_prune_deviation_threshold", 0.5)),
        None
        if getattr(config, "pattern_store_path", None) is None
        else str(getattr(config, "pattern_store_path")),
    )
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
