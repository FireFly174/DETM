"""Metric plugin protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from detm.runtime import api
from detm.runtime.influence import DETMInfluence
from detm.runtime.state import DETMState


@dataclass(frozen=True)
class MetricContext:
    """Context passed to metric plugins."""

    state: DETMState
    observables: api.Observables
    influence: DETMInfluence | None
    n_ticks: int
    get_state_blob: Any | None = None  # optional callable for lazy serialization


class MetricPlugin(Protocol):
    name: str

    def compute(self, ctx: MetricContext) -> Dict[str, Any]: ...


__all__ = ["MetricContext", "MetricPlugin"]

