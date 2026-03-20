"""Pure helpers for pattern memory runtime."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from detm.runtime.pattern_memory.scope import normalize_reuse_scope


def normalize_context_token(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return "*"
    return token.replace("|", "/")


def scoped_key(*, base_key: str, level: str, mode: str) -> str:
    level_token = normalize_context_token(level)
    mode_token = normalize_context_token(mode)
    return f"lvl={level_token}|mode={mode_token}|{str(base_key)}"


def lookup_candidates(*, base_key: str, level: str, mode: str, scope: str) -> tuple[str, ...]:
    exact = scoped_key(base_key=base_key, level=level, mode=mode)
    level_wild = scoped_key(base_key=base_key, level=level, mode="*")
    mode_wild = scoped_key(base_key=base_key, level="*", mode=mode)
    global_scoped = scoped_key(base_key=base_key, level="*", mode="*")
    legacy = str(base_key)
    out: list[str] = []

    def _push(value: str) -> None:
        if value not in out:
            out.append(value)

    if str(scope) == "global":
        _push(legacy)
        _push(global_scoped)
        _push(exact)
        return tuple(out)

    _push(exact)
    if str(scope) == "portable":
        _push(level_wild)
        _push(mode_wild)
        _push(global_scoped)
        _push(legacy)
        return tuple(out)

    _push(legacy)
    return tuple(out)


def remember_key(*, base_key: str, level: str, mode: str, scope: str) -> str:
    if str(scope) == "global":
        return str(base_key)
    if str(scope) == "portable":
        return scoped_key(base_key=base_key, level="*", mode="*")
    return scoped_key(base_key=base_key, level=level, mode=mode)


def extract_patch(energy: np.ndarray, *, center_x: int, center_y: int, radius: int, boundary: str) -> np.ndarray:
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


def compute_pattern_key(*, energy: np.ndarray, center_x: int, center_y: int, radius: int, boundary: str) -> str:
    patch = extract_patch(
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


def is_reusable_record(*, record: Any, prune_error_threshold: float, prune_deviation_threshold: float) -> bool:
    return bool(
        float(record.error) <= float(prune_error_threshold)
        and float(record.deviation) <= float(prune_deviation_threshold)
    )


def runtime_key_from_config(config: Any) -> tuple[Any, ...]:
    multiscale = getattr(config, "multiscale_catalog", None)
    return (
        bool(getattr(config, "pattern_reuse_enabled", True)),
        normalize_reuse_scope(getattr(config, "pattern_reuse_scope", "portable")),
        int(getattr(config, "pattern_cache_capacity", 128)),
        int(getattr(config, "pattern_cache_ttl_steps", 4096)),
        float(getattr(config, "pattern_prune_error_threshold", 0.05)),
        float(getattr(config, "pattern_prune_deviation_threshold", 0.5)),
        None
        if getattr(config, "pattern_store_path", None) is None
        else str(getattr(config, "pattern_store_path")),
        bool(getattr(multiscale, "enabled", False)),
        str(getattr(multiscale, "mode", "observe")),
        None if getattr(multiscale, "redis_url", None) in (None, "") else str(getattr(multiscale, "redis_url")),
        int(getattr(multiscale, "window_ticks", 10)),
        int(getattr(multiscale, "patch_radius", 1)),
        tuple(int(value) for value in tuple(getattr(multiscale, "horizons", (1,)))),
        float(getattr(multiscale, "quantization", 0.05)),
        int(getattr(multiscale, "candidate_min_support", 3)),
        float(getattr(multiscale, "candidate_min_confidence", 0.75)),
        float(getattr(multiscale, "jump_max_error", 0.05)),
        bool(getattr(multiscale, "commit_only_sampling", True)),
    )


__all__ = [
    "compute_pattern_key",
    "extract_patch",
    "is_reusable_record",
    "lookup_candidates",
    "normalize_context_token",
    "remember_key",
    "runtime_key_from_config",
    "scoped_key",
]
