"""Scope normalization helpers for pattern reuse."""

from __future__ import annotations

from typing import Any


def normalize_reuse_scope(raw: Any) -> str:
    scope = str(raw).strip().lower()
    if scope in {"global", "portable", "strict"}:
        return scope
    return "portable"


__all__ = ["normalize_reuse_scope"]
