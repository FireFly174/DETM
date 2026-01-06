"""Metric plugins for DETM runs.

Metrics are computed outside the core L0 dynamics and attached via EventBus
subscribers. This keeps the runtime API stable while allowing experiments to
add/replace observables.
"""

from __future__ import annotations

from detm.metrics.base import MetricPlugin
from detm.metrics.builtin import BuiltinMetrics, default_metric_plugins

__all__ = ["BuiltinMetrics", "MetricPlugin", "default_metric_plugins"]

