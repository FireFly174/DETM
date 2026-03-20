"""Artifact-first watch contract for read-only subscribers.

This contract defines a minimal machine-readable payload that links:
- canonical `trace_ref`
- `OuterFields` artifact reference
- operator-facing metrics/events/signature projection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _require_non_empty_str(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _require_int_at_least(value: Any, *, field_name: str, min_value: int) -> int:
    out = int(value)
    if out < int(min_value):
        raise ValueError(f"{field_name} must be >= {int(min_value)}")
    return out


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    return bool(default)


def _coerce_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return int(default)


def _coerce_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, tuple):
        return [str(x) for x in list(value)]
    return []


@dataclass(frozen=True)
class AntiGoodhartReaction:
    apply: bool = False
    actions: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "AntiGoodhartReaction":
        payload = dict(data or {})
        return cls(
            apply=_coerce_bool(payload.get("apply", False), default=False),
            actions=_coerce_str_list(payload.get("actions", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "apply": bool(self.apply),
            "actions": [str(x) for x in list(self.actions)],
        }


@dataclass(frozen=True)
class AntiGoodhartSnapshot:
    goodhart_flag: bool = False
    target_signal: str = ""
    target_delta: float = 0.0
    degraded_signals: List[str] = field(default_factory=list)
    degraded_signal_count: int = 0
    thresholds: Dict[str, Any] = field(default_factory=dict)
    policy_reaction: AntiGoodhartReaction = field(default_factory=AntiGoodhartReaction)
    policy_reaction_enabled: bool = False
    preferred_runtime_profile: str = ""
    runtime_profile_applied: bool = False
    applicability: str = "unavailable"

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "AntiGoodhartSnapshot":
        payload = dict(data or {})
        degraded_signals = _coerce_str_list(payload.get("degraded_signals", []))
        degraded_count = _require_int_at_least(
            payload.get("degraded_signal_count", len(degraded_signals)),
            field_name="degraded_signal_count",
            min_value=0,
        )
        thresholds_raw = payload.get("thresholds", {})
        thresholds_dict = dict(thresholds_raw) if isinstance(thresholds_raw, dict) else {}
        target_signal = str(payload.get("target_signal", ""))
        thresholds = {
            "target_signal": str(thresholds_dict.get("target_signal", target_signal)),
            "min_target_delta": _coerce_float(thresholds_dict.get("min_target_delta", 0.0), default=0.0),
            "min_degraded_signals": max(0, _coerce_int(thresholds_dict.get("min_degraded_signals", 0), default=0)),
            "degradation_epsilon": _coerce_float(
                thresholds_dict.get("degradation_epsilon", 0.0),
                default=0.0,
            ),
        }
        return cls(
            goodhart_flag=_coerce_bool(payload.get("goodhart_flag", False), default=False),
            target_signal=target_signal,
            target_delta=_coerce_float(payload.get("target_delta", 0.0), default=0.0),
            degraded_signals=degraded_signals,
            degraded_signal_count=max(int(degraded_count), len(degraded_signals)),
            thresholds=thresholds,
            policy_reaction=AntiGoodhartReaction.from_dict(dict(payload.get("policy_reaction", {}))),
            policy_reaction_enabled=_coerce_bool(payload.get("policy_reaction_enabled", False), default=False),
            preferred_runtime_profile=str(payload.get("preferred_runtime_profile", "")),
            runtime_profile_applied=_coerce_bool(payload.get("runtime_profile_applied", False), default=False),
            applicability=str(payload.get("applicability", "unavailable")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goodhart_flag": bool(self.goodhart_flag),
            "target_signal": str(self.target_signal),
            "target_delta": float(self.target_delta),
            "degraded_signals": [str(x) for x in list(self.degraded_signals)],
            "degraded_signal_count": int(max(int(self.degraded_signal_count), len(self.degraded_signals))),
            "thresholds": {
                "target_signal": str(dict(self.thresholds).get("target_signal", "")),
                "min_target_delta": _coerce_float(dict(self.thresholds).get("min_target_delta", 0.0), default=0.0),
                "min_degraded_signals": max(
                    0,
                    _coerce_int(dict(self.thresholds).get("min_degraded_signals", 0), default=0),
                ),
                "degradation_epsilon": _coerce_float(
                    dict(self.thresholds).get("degradation_epsilon", 0.0),
                    default=0.0,
                ),
            },
            "policy_reaction": self.policy_reaction.to_dict(),
            "policy_reaction_enabled": bool(self.policy_reaction_enabled),
            "preferred_runtime_profile": str(self.preferred_runtime_profile),
            "runtime_profile_applied": bool(self.runtime_profile_applied),
            "applicability": str(self.applicability),
        }


@dataclass(frozen=True)
class ExplorationHorizonSnapshot:
    exploration_horizon_ticks: int = 0
    horizon_start_tick: int = 0
    horizon_break_reason: str = ""
    horizon_recovery_cost_ticks: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "ExplorationHorizonSnapshot":
        payload = dict(data or {})
        return cls(
            exploration_horizon_ticks=max(
                0,
                _coerce_int(payload.get("exploration_horizon_ticks", 0), default=0),
            ),
            horizon_start_tick=max(
                0,
                _coerce_int(payload.get("horizon_start_tick", 0), default=0),
            ),
            horizon_break_reason=str(payload.get("horizon_break_reason", "")),
            horizon_recovery_cost_ticks=max(
                0,
                _coerce_int(payload.get("horizon_recovery_cost_ticks", 0), default=0),
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exploration_horizon_ticks": int(max(0, self.exploration_horizon_ticks)),
            "horizon_start_tick": int(max(0, self.horizon_start_tick)),
            "horizon_break_reason": str(self.horizon_break_reason),
            "horizon_recovery_cost_ticks": int(max(0, self.horizon_recovery_cost_ticks)),
        }


@dataclass(frozen=True)
class OuterFieldsRef:
    """Reference to an OuterFields artifact."""

    kind: str
    level_src: str
    base_level: str
    tick: int
    window_ticks: int
    stride_ticks: int
    uri: str
    schema: str = "OUTERFIELDS_V1"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OuterFieldsRef":
        kind = _require_non_empty_str(data.get("kind"), field_name="kind")
        if kind != "outerfields":
            raise ValueError("kind must be 'outerfields'")
        return cls(
            kind=kind,
            level_src=_require_non_empty_str(data.get("level_src"), field_name="level_src"),
            base_level=_require_non_empty_str(data.get("base_level"), field_name="base_level"),
            tick=_require_int_at_least(data.get("tick", 0), field_name="tick", min_value=0),
            window_ticks=_require_int_at_least(
                data.get("window_ticks", 1),
                field_name="window_ticks",
                min_value=1,
            ),
            stride_ticks=_require_int_at_least(
                data.get("stride_ticks", 1),
                field_name="stride_ticks",
                min_value=1,
            ),
            uri=_require_non_empty_str(data.get("uri"), field_name="uri"),
            schema=_require_non_empty_str(
                data.get("schema", "OUTERFIELDS_V1"),
                field_name="schema",
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": str(self.kind),
            "level_src": str(self.level_src),
            "base_level": str(self.base_level),
            "tick": int(self.tick),
            "window_ticks": int(self.window_ticks),
            "stride_ticks": int(self.stride_ticks),
            "uri": str(self.uri),
            "schema": str(self.schema),
        }


@dataclass(frozen=True)
class WatchContractPacket:
    """Projection payload consumed by watch/read-only subscribers."""

    tick: int
    trace_ref: str
    outerfields_ref: OuterFieldsRef
    signature: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    event_types: List[str] = field(default_factory=list)
    event_count: int = 0
    policy: Dict[str, Any] = field(default_factory=dict)
    schema: str = "WATCH_CONTRACT_V1"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WatchContractPacket":
        events_raw = data.get("events", [])
        if not isinstance(events_raw, list):
            raise ValueError("events must be a list")
        events = [dict(event) for event in events_raw if isinstance(event, dict)]
        event_types_raw = data.get("event_types", [])
        if not isinstance(event_types_raw, list):
            raise ValueError("event_types must be a list")
        event_types = [str(x) for x in event_types_raw]
        metrics = dict(data.get("metrics", {}))
        watchpoints = dict(metrics.get("watchpoints", {}))
        watch_anti = AntiGoodhartSnapshot.from_dict(dict(watchpoints.get("anti_goodhart", {})))
        watchpoints["anti_goodhart"] = watch_anti.to_dict()
        watchpoints["anti_goodhart_flag"] = bool(watch_anti.goodhart_flag)
        watchpoints["anti_goodhart_degraded_signal_count"] = int(watch_anti.degraded_signal_count)
        watchpoints["anti_goodhart_policy_reaction_applied"] = bool(
            watch_anti.policy_reaction.apply
        )
        watchpoints["anti_goodhart_runtime_profile_applied"] = bool(watch_anti.runtime_profile_applied)
        watch_horizon = ExplorationHorizonSnapshot.from_dict(dict(watchpoints.get("exploration_horizon", {})))
        watchpoints["exploration_horizon"] = watch_horizon.to_dict()
        watchpoints["exploration_horizon_ticks"] = int(watch_horizon.exploration_horizon_ticks)
        watchpoints["horizon_start_tick"] = int(watch_horizon.horizon_start_tick)
        watchpoints["horizon_break_reason"] = str(watch_horizon.horizon_break_reason)
        watchpoints["horizon_recovery_cost_ticks"] = int(watch_horizon.horizon_recovery_cost_ticks)
        metrics["watchpoints"] = watchpoints

        policy = dict(data.get("policy", {}))
        policy_anti = AntiGoodhartSnapshot.from_dict(dict(policy.get("anti_goodhart", {})))
        policy["anti_goodhart"] = policy_anti.to_dict()
        policy_horizon = ExplorationHorizonSnapshot.from_dict(dict(policy.get("exploration_horizon", {})))
        policy["exploration_horizon"] = policy_horizon.to_dict()
        return cls(
            tick=_require_int_at_least(data.get("tick", 0), field_name="tick", min_value=0),
            trace_ref=_require_non_empty_str(data.get("trace_ref"), field_name="trace_ref"),
            outerfields_ref=OuterFieldsRef.from_dict(dict(data.get("outerfields_ref", {}))),
            signature=dict(data.get("signature", {})),
            metrics=metrics,
            events=events,
            event_types=event_types,
            event_count=_require_int_at_least(
                data.get("event_count", len(event_types)),
                field_name="event_count",
                min_value=0,
            ),
            policy=policy,
            schema=_require_non_empty_str(
                data.get("schema", "WATCH_CONTRACT_V1"),
                field_name="schema",
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": str(self.schema),
            "type": "watch_contract_step",
            "tick": int(self.tick),
            "trace_ref": str(self.trace_ref),
            "outerfields_ref": self.outerfields_ref.to_dict(),
            "signature": dict(self.signature),
            "metrics": dict(self.metrics),
            "events": [dict(event) for event in list(self.events)],
            "event_types": [str(x) for x in list(self.event_types)],
            "event_count": int(self.event_count),
            "policy": dict(self.policy),
        }


__all__ = [
    "AntiGoodhartReaction",
    "AntiGoodhartSnapshot",
    "ExplorationHorizonSnapshot",
    "OuterFieldsRef",
    "WatchContractPacket",
]
