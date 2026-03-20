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

@dataclass(frozen=True)
class BridgeRecordSource:
    source_id: str
    schema_version: str = "bridge_record_source/v1"
    level_src: str = "L0"
    level_dst: str = "L0+1"
    window_signature: str = ""
    interface_signature: str = ""
    horizon_k: int = 1
    result_signature: str = ""
    window_geometry: Dict[str, Any] = field(default_factory=dict)
    invariants_preserved: tuple[str, ...] = field(default_factory=tuple)
    forward_body: Dict[str, Any] = field(default_factory=dict)
    reverse_body: Dict[str, Any] = field(default_factory=dict)
    validity_envelope: Dict[str, Any] = field(default_factory=dict)
    verification_summary: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    status: str = "observed"
    db_refs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": str(self.source_id),
            "schema_version": str(self.schema_version),
            "level_src": str(self.level_src),
            "level_dst": str(self.level_dst),
            "window_signature": str(self.window_signature),
            "interface_signature": str(self.interface_signature),
            "horizon_k": int(self.horizon_k),
            "result_signature": str(self.result_signature),
            "window_geometry": dict(self.window_geometry),
            "invariants_preserved": [str(value) for value in tuple(self.invariants_preserved)],
            "forward_body": dict(self.forward_body),
            "reverse_body": dict(self.reverse_body),
            "validity_envelope": dict(self.validity_envelope),
            "verification_summary": dict(self.verification_summary),
            "provenance": dict(self.provenance),
            "status": str(self.status),
            "db_refs": dict(self.db_refs),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BridgeRecordSource":
        data = dict(payload)
        return cls(
            source_id=str(data.get("source_id", "")),
            schema_version=str(data.get("schema_version", "bridge_record_source/v1")),
            level_src=str(data.get("level_src", "L0")),
            level_dst=str(data.get("level_dst", "L0+1")),
            window_signature=str(data.get("window_signature", "")),
            interface_signature=str(data.get("interface_signature", "")),
            horizon_k=max(1, int(data.get("horizon_k", 1))),
            result_signature=str(data.get("result_signature", "")),
            window_geometry=dict(data.get("window_geometry", {})),
            invariants_preserved=tuple(str(value) for value in list(data.get("invariants_preserved", ()))),
            forward_body=dict(data.get("forward_body", {})),
            reverse_body=dict(data.get("reverse_body", {})),
            validity_envelope=dict(data.get("validity_envelope", {})),
            verification_summary=dict(data.get("verification_summary", {})),
            provenance=dict(data.get("provenance", {})),
            status=str(data.get("status", "observed")),
            db_refs=dict(data.get("db_refs", {})),
        )

@dataclass(frozen=True)
class VerificationRun:
    verification_id: str
    schema_version: str = "verification_run/v1"
    source_id: str = ""
    tick: int = 0
    trace_ref: str = ""
    level: str = "L0"
    window_signature: str = ""
    interface_signature: str = ""
    result_signature: str = ""
    matched: bool | None = None
    status: str = "observed"
    confidence: float = 0.0
    support: int = 0
    usage_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verification_id": str(self.verification_id),
            "schema_version": str(self.schema_version),
            "source_id": str(self.source_id),
            "tick": int(self.tick),
            "trace_ref": str(self.trace_ref),
            "level": str(self.level),
            "window_signature": str(self.window_signature),
            "interface_signature": str(self.interface_signature),
            "result_signature": str(self.result_signature),
            "matched": self.matched,
            "status": str(self.status),
            "confidence": float(self.confidence),
            "support": int(self.support),
            "usage_count": int(self.usage_count),
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "VerificationRun":
        data = dict(payload)
        matched = data.get("matched")
        return cls(
            verification_id=str(data.get("verification_id", "")),
            schema_version=str(data.get("schema_version", "verification_run/v1")),
            source_id=str(data.get("source_id", "")),
            tick=max(0, int(data.get("tick", 0))),
            trace_ref=str(data.get("trace_ref", "")),
            level=str(data.get("level", "L0")),
            window_signature=str(data.get("window_signature", "")),
            interface_signature=str(data.get("interface_signature", "")),
            result_signature=str(data.get("result_signature", "")),
            matched=None if matched is None else bool(matched),
            status=str(data.get("status", "observed")),
            confidence=min(1.0, max(0.0, float(data.get("confidence", 0.0)))),
            support=max(0, int(data.get("support", 0))),
            usage_count=max(0, int(data.get("usage_count", 0))),
            details=dict(data.get("details", {})),
        )


__all__ = ["BridgeRecord", "BridgeRecordSource", "PatternRecord", "VerificationRun"]
