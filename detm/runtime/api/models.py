"""Runtime API observation models."""

from __future__ import annotations

from dataclasses import dataclass

from detm.runtime.signature import DETMSignature


@dataclass(frozen=True)
class FieldSummaries:
    energy: dict[str, float]
    entropy: dict[str, float]
    internal_time: dict[str, float]


@dataclass(frozen=True)
class Observables:
    signature: DETMSignature
    field_summaries: FieldSummaries
    events: list[dict[str, object]]
    cost: dict[str, float]
    quality: dict[str, float]


__all__ = ["FieldSummaries", "Observables"]
