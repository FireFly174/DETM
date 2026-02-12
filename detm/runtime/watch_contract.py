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
        return cls(
            tick=_require_int_at_least(data.get("tick", 0), field_name="tick", min_value=0),
            trace_ref=_require_non_empty_str(data.get("trace_ref"), field_name="trace_ref"),
            outerfields_ref=OuterFieldsRef.from_dict(dict(data.get("outerfields_ref", {}))),
            signature=dict(data.get("signature", {})),
            metrics=dict(data.get("metrics", {})),
            events=events,
            event_types=event_types,
            event_count=_require_int_at_least(
                data.get("event_count", len(event_types)),
                field_name="event_count",
                min_value=0,
            ),
            policy=dict(data.get("policy", {})),
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


__all__ = ["OuterFieldsRef", "WatchContractPacket"]
