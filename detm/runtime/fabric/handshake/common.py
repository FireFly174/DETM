"""Shared helpers for fabric handshake runtime."""

from __future__ import annotations


def norm_mode(value: str | None) -> str | None:
    if value is None:
        return None
    mode = str(value).strip().lower()
    return mode or None


__all__ = ["norm_mode"]
