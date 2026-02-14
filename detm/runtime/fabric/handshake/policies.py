"""Policy primitives for fabric handshake."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Publish retry controls for handshake envelopes."""

    max_attempts: int = 1


__all__ = ["RetryPolicy"]
