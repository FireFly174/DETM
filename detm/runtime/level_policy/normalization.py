"""Normalization helpers for level-policy config parsing."""

from __future__ import annotations

from typing import Any, Tuple


def as_positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return int(default)
    return max(1, parsed)


def normalize_allowed_event_types(value: Any, *, allow_empty: bool = False) -> Tuple[str, ...]:
    if value is None:
        return tuple() if allow_empty else ("*",)
    if isinstance(value, str):
        chunk = value.strip()
        if chunk:
            return (chunk,)
        return tuple() if allow_empty else ("*",)
    if isinstance(value, (list, tuple, set)):
        out = tuple(str(v).strip() for v in value if str(v).strip())
        if out:
            return out
        return tuple() if allow_empty else ("*",)
    return tuple() if allow_empty else ("*",)


def as_non_negative_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return max(0, int(default))
    return max(0, parsed)


def as_non_negative_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return max(0.0, float(default))
    return max(0.0, float(parsed))


def as_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def normalize_string_tuple(value: Any) -> Tuple[str, ...]:
    if value is None:
        return tuple()
    if isinstance(value, str):
        chunk = value.strip()
        return (chunk,) if chunk else tuple()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    return tuple()


__all__ = [
    "as_int",
    "as_non_negative_float",
    "as_non_negative_int",
    "as_positive_int",
    "normalize_allowed_event_types",
    "normalize_string_tuple",
]
