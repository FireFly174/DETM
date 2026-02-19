from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AntiGoodhartThresholds:
    target_signal: str = "operator_reuse"
    min_target_delta: float = 0.0
    min_degraded_signals: int = 2
    degradation_epsilon: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_signal": str(self.target_signal),
            "min_target_delta": float(self.min_target_delta),
            "min_degraded_signals": int(max(1, self.min_degraded_signals)),
            "degradation_epsilon": float(max(0.0, self.degradation_epsilon)),
        }


def evaluate_anti_goodhart(
    *,
    panel: Mapping[str, Any],
    previous_panel: Mapping[str, Any] | None,
    thresholds: AntiGoodhartThresholds,
) -> dict[str, Any]:
    target_signal = str(thresholds.target_signal)
    min_target_delta = float(thresholds.min_target_delta)
    min_degraded_signals = int(max(1, thresholds.min_degraded_signals))
    degradation_epsilon = float(max(0.0, thresholds.degradation_epsilon))

    if previous_panel is None:
        return {
            "goodhart_flag": False,
            "target_signal": target_signal,
            "target_delta": 0.0,
            "degraded_signals": [],
            "degraded_signal_count": 0,
            "thresholds": thresholds.to_dict(),
            "rule": "goodhart_flag=(d_target>min_target_delta) and (degraded_signals>=min_degraded_signals)",
            "policy_reaction": {
                "apply": False,
                "actions": [],
            },
            "applicability": "cold_start",
        }

    current_target = float(panel.get(target_signal, 0.0))
    previous_target = float(previous_panel.get(target_signal, 0.0))
    target_delta = float(current_target - previous_target)
    target_rising = bool(target_delta > min_target_delta)

    degraded_signals: list[str] = []
    for signal_name in ("hold_rate", "transferability", "torsion_health"):
        current_value = float(panel.get(signal_name, 0.0))
        previous_value = float(previous_panel.get(signal_name, 0.0))
        if (current_value - previous_value) < -degradation_epsilon:
            degraded_signals.append(signal_name)

    degraded_signal_count = int(len(degraded_signals))
    goodhart_flag = bool(target_rising and degraded_signal_count >= min_degraded_signals)
    return {
        "goodhart_flag": goodhart_flag,
        "target_signal": target_signal,
        "target_delta": float(target_delta),
        "degraded_signals": degraded_signals,
        "degraded_signal_count": degraded_signal_count,
        "thresholds": thresholds.to_dict(),
        "rule": "goodhart_flag=(d_target>min_target_delta) and (degraded_signals>=min_degraded_signals)",
        "policy_reaction": {
            "apply": goodhart_flag,
            "actions": (
                [
                    "downweight_target_signal",
                    "enable_extended_outerfields_audit",
                    "prefer_stability_runtime_profile",
                ]
                if goodhart_flag
                else []
            ),
        },
        "applicability": "runtime_panel",
    }


__all__ = ["AntiGoodhartThresholds", "evaluate_anti_goodhart"]
