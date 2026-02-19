from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from detm_app.runtime.anti_goodhart import AntiGoodhartThresholds, evaluate_anti_goodhart


@dataclass(frozen=True)
class PortabilityThresholds:
    hold_rate_min: float = 0.9
    operator_reuse_min: float = 0.3
    transferability_min: float = 0.25

    def to_dict(self) -> dict[str, float]:
        return {
            "hold_rate_min": float(max(0.0, self.hold_rate_min)),
            "operator_reuse_min": float(max(0.0, self.operator_reuse_min)),
            "transferability_min": float(max(0.0, self.transferability_min)),
        }


def evaluate_portability_acceptance(
    *,
    panel: Mapping[str, Any],
    thresholds: PortabilityThresholds,
) -> dict[str, Any]:
    hold_rate = float(panel.get("hold_rate", 0.0))
    operator_reuse = float(panel.get("operator_reuse", 0.0))
    transferability = float(panel.get("transferability", 0.0))
    failed_signals: list[str] = []
    if hold_rate < float(thresholds.hold_rate_min):
        failed_signals.append("hold_rate")
    if operator_reuse < float(thresholds.operator_reuse_min):
        failed_signals.append("operator_reuse")
    if transferability < float(thresholds.transferability_min):
        failed_signals.append("transferability")
    return {
        "passed": len(failed_signals) == 0,
        "failed_signals": failed_signals,
    }


__all__ = [
    "AntiGoodhartThresholds",
    "PortabilityThresholds",
    "evaluate_anti_goodhart",
    "evaluate_portability_acceptance",
]
