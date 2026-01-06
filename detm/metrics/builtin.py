"""Built-in metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from detm.metrics.base import MetricContext, MetricPlugin


@dataclass(frozen=True)
class BuiltinMetrics:
    """Small stable set of extra metrics derived from existing observables."""

    name: str = "builtin"

    def compute(self, ctx: MetricContext) -> Dict[str, Any]:
        obs = ctx.observables
        # Keep this flat and JSON-friendly.
        out: Dict[str, Any] = {
            "tick": int(ctx.state.step_count),
            "signature_version": str(obs.signature.version),
            "signature_summary": dict(obs.signature.summary),
            "quality": dict(obs.quality),
            "cost": dict(obs.cost),
            "events_count": int(len(obs.events)),
        }
        # A bit of structure for quick dashboards
        out["attractor_count"] = int(sum(1 for e in obs.events if e.get("type") == "attractor"))
        if ctx.influence is not None:
            out["influence_symbol_id"] = str(ctx.influence.symbol_id)
            out["influence_amplitude"] = float(ctx.influence.amplitude)
        return out


def default_metric_plugins() -> List[MetricPlugin]:
    return [BuiltinMetrics()]


__all__ = ["BuiltinMetrics", "default_metric_plugins"]

