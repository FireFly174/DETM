"""Commit packet contract for node/fabric synchronization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from detm.runtime.schemas import DETM_COMMIT_PACKET_V1


COMMIT_TYPES = {"state", "boundary", "coarsened", "proof"}
COMMIT_MODES = {"realtime", "audit"}


def _require_non_empty_str(value: Any, *, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _as_non_negative_int(value: Any, *, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return parsed


@dataclass(frozen=True)
class CommitTickRef:
    """Commit time coordinate."""

    base_level: str = "L0"
    tick: int = 0
    equiv_l0_ticks: int | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "CommitTickRef":
        data = dict(payload or {})
        equiv_raw = data.get("equiv_l0_ticks")
        return cls(
            base_level=_require_non_empty_str(data.get("base_level", "L0"), field_name="tick_ref.base_level"),
            tick=_as_non_negative_int(data.get("tick", 0), field_name="tick_ref.tick"),
            equiv_l0_ticks=None
            if equiv_raw is None
            else _as_non_negative_int(equiv_raw, field_name="tick_ref.equiv_l0_ticks"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "base_level": str(self.base_level),
            "tick": int(self.tick),
        }
        if self.equiv_l0_ticks is not None:
            payload["equiv_l0_ticks"] = int(self.equiv_l0_ticks)
        return payload


@dataclass(frozen=True)
class CommitPacket:
    """Machine-validatable commit packet for inter-node exchange."""

    schema_version: str = DETM_COMMIT_PACKET_V1
    commit_type: str = "state"  # state | boundary | coarsened | proof
    mode: str = "realtime"  # realtime | audit
    node_id: str = "local"
    commit_id: str = "commit:0"
    parent_ref: str | None = None
    tick_ref: CommitTickRef = field(default_factory=CommitTickRef)
    inputs_ref: str | None = None
    delta_ref: str | None = None
    invariants_ref: str | None = None
    trace_ref: str = "trace://local/0"
    summary: Dict[str, Any] = field(default_factory=dict)
    signature: str = "sig:unsigned"
    created_at_ms: int = 0

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CommitPacket":
        data = dict(payload)
        tick_ref_raw = data.get("tick_ref")
        if not isinstance(tick_ref_raw, Mapping):
            raise ValueError("tick_ref must be an object")

        packet = cls(
            schema_version=str(data.get("schema_version", DETM_COMMIT_PACKET_V1)),
            commit_type=str(data.get("commit_type", "state")).strip().lower(),
            mode=str(data.get("mode", "realtime")).strip().lower(),
            node_id=_require_non_empty_str(data.get("node_id", ""), field_name="node_id"),
            commit_id=_require_non_empty_str(data.get("commit_id", ""), field_name="commit_id"),
            parent_ref=None
            if data.get("parent_ref") is None
            else _require_non_empty_str(data.get("parent_ref"), field_name="parent_ref"),
            tick_ref=CommitTickRef.from_dict(tick_ref_raw),
            inputs_ref=None
            if data.get("inputs_ref") is None
            else _require_non_empty_str(data.get("inputs_ref"), field_name="inputs_ref"),
            delta_ref=None
            if data.get("delta_ref") is None
            else _require_non_empty_str(data.get("delta_ref"), field_name="delta_ref"),
            invariants_ref=None
            if data.get("invariants_ref") is None
            else _require_non_empty_str(data.get("invariants_ref"), field_name="invariants_ref"),
            trace_ref=_require_non_empty_str(data.get("trace_ref", ""), field_name="trace_ref"),
            summary=dict(data.get("summary", {})) if isinstance(data.get("summary", {}), Mapping) else {},
            signature=_require_non_empty_str(data.get("signature", ""), field_name="signature"),
            created_at_ms=_as_non_negative_int(data.get("created_at_ms", 0), field_name="created_at_ms"),
        )
        packet.validate()
        return packet

    def validate(self) -> None:
        if self.commit_type not in COMMIT_TYPES:
            raise ValueError(f"commit_type must be one of {sorted(COMMIT_TYPES)}")
        if self.mode not in COMMIT_MODES:
            raise ValueError(f"mode must be one of {sorted(COMMIT_MODES)}")
        if self.commit_type in {"state", "boundary", "coarsened"} and self.delta_ref is None:
            raise ValueError(f"{self.commit_type} commit requires delta_ref")
        if self.commit_type == "proof" and self.invariants_ref is None:
            raise ValueError("proof commit requires invariants_ref")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "schema_version": str(self.schema_version),
            "commit_type": str(self.commit_type),
            "mode": str(self.mode),
            "node_id": str(self.node_id),
            "commit_id": str(self.commit_id),
            "parent_ref": self.parent_ref,
            "tick_ref": self.tick_ref.to_dict(),
            "inputs_ref": self.inputs_ref,
            "delta_ref": self.delta_ref,
            "invariants_ref": self.invariants_ref,
            "trace_ref": str(self.trace_ref),
            "summary": dict(self.summary),
            "signature": str(self.signature),
            "created_at_ms": int(self.created_at_ms),
        }


__all__ = ["COMMIT_MODES", "COMMIT_TYPES", "CommitPacket", "CommitTickRef"]
