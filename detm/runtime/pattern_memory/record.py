"""Pattern memory record contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class PatternRecord:
    key: str
    blend: float
    error: float
    deviation: float
    hits: int = 1
    updated_step: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": str(self.key),
            "blend": float(self.blend),
            "error": float(self.error),
            "deviation": float(self.deviation),
            "hits": int(self.hits),
            "updated_step": int(self.updated_step),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PatternRecord":
        data = dict(payload)
        return cls(
            key=str(data.get("key", "")),
            blend=float(data.get("blend", 0.0)),
            error=float(data.get("error", 0.0)),
            deviation=float(data.get("deviation", 0.0)),
            hits=max(1, int(data.get("hits", 1))),
            updated_step=max(0, int(data.get("updated_step", 0))),
        )


@dataclass(frozen=True)
class BridgeRecord:
    record_id: str
    level: str
    window_signature: str
    interface_signature: str
    horizon_k: int
    result_signature: str
    error_bound: float = 0.0
    confidence: float = 0.0
    usage_count: int = 0
    support: int = 0
    first_seen_tick: int = 0
    last_seen_tick: int = 0
    forward_descriptor: Dict[str, Any] = field(default_factory=dict)
    reverse_descriptor_short: Dict[str, Any] = field(default_factory=dict)
    validity_envelope: Dict[str, Any] = field(default_factory=dict)
    verification_stats: Dict[str, Any] = field(default_factory=dict)
    db_refs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": str(self.record_id),
            "level": str(self.level),
            "window_signature": str(self.window_signature),
            "interface_signature": str(self.interface_signature),
            "horizon_k": int(self.horizon_k),
            "result_signature": str(self.result_signature),
            "error_bound": float(self.error_bound),
            "confidence": float(self.confidence),
            "usage_count": int(self.usage_count),
            "support": int(self.support),
            "first_seen_tick": int(self.first_seen_tick),
            "last_seen_tick": int(self.last_seen_tick),
            "forward_descriptor": dict(self.forward_descriptor),
            "reverse_descriptor_short": dict(self.reverse_descriptor_short),
            "validity_envelope": dict(self.validity_envelope),
            "verification_stats": dict(self.verification_stats),
            "db_refs": dict(self.db_refs),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BridgeRecord":
        data = dict(payload)
        return cls(
            record_id=str(data.get("record_id", "")),
            level=str(data.get("level", "L0")),
            window_signature=str(data.get("window_signature", "")),
            interface_signature=str(data.get("interface_signature", "")),
            horizon_k=max(1, int(data.get("horizon_k", 1))),
            result_signature=str(data.get("result_signature", "")),
            error_bound=max(0.0, float(data.get("error_bound", 0.0))),
            confidence=min(1.0, max(0.0, float(data.get("confidence", 0.0)))),
            usage_count=max(0, int(data.get("usage_count", 0))),
            support=max(0, int(data.get("support", 0))),
            first_seen_tick=max(0, int(data.get("first_seen_tick", 0))),
            last_seen_tick=max(0, int(data.get("last_seen_tick", 0))),
            forward_descriptor=dict(data.get("forward_descriptor", {})),
            reverse_descriptor_short=dict(data.get("reverse_descriptor_short", {})),
            validity_envelope=dict(data.get("validity_envelope", {})),
            verification_stats=dict(data.get("verification_stats", {})),
            db_refs=dict(data.get("db_refs", {})),
        )


__all__ = ["BridgeRecord", "PatternRecord"]
