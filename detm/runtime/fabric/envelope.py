"""Fabric transport envelope for node-to-node routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from detm.runtime.schemas import DETM_FABRIC_ENVELOPE_V1

# ARCH-MARKERS:
# - LAYER_BAND: L4-L5
# - ABSTRACT_DISTANCE: 0 (contract class complete for current scope)
# - OOP_TECH_DEBT: envelope signing/encryption profile policy


FABRIC_MODES = {"realtime", "audit"}


def _require_non_empty_str(value: Any, *, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


@dataclass(frozen=True)
class FabricEnvelope:
    """Transport envelope decoupling routing metadata from payload format."""

    schema_version: str = DETM_FABRIC_ENVELOPE_V1
    message_type: str = "commit"
    channel: str = "fabric.default"
    mode: str = "realtime"  # realtime | audit
    sender: str = "local"
    recipient: str | None = None
    payload_ref: str = "artifact://payload/0"
    payload_inline: Dict[str, Any] | None = None
    trace_ref: str | None = None
    commit_ref: str | None = None
    delivery_id: str | None = None
    auth_key_id: str | None = None
    transport_identity: str | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FabricEnvelope":
        data = dict(payload)
        payload_inline_raw = data.get("payload_inline")
        if payload_inline_raw is not None and not isinstance(payload_inline_raw, Mapping):
            raise ValueError("payload_inline must be an object when provided")
        envelope = cls(
            schema_version=str(data.get("schema_version", DETM_FABRIC_ENVELOPE_V1)),
            message_type=_require_non_empty_str(data.get("message_type", ""), field_name="message_type"),
            channel=_require_non_empty_str(data.get("channel", ""), field_name="channel"),
            mode=str(data.get("mode", "realtime")).strip().lower(),
            sender=_require_non_empty_str(data.get("sender", ""), field_name="sender"),
            recipient=None
            if data.get("recipient") is None
            else _require_non_empty_str(data.get("recipient"), field_name="recipient"),
            payload_ref=_require_non_empty_str(data.get("payload_ref", ""), field_name="payload_ref"),
            payload_inline=None
            if payload_inline_raw is None
            else dict(payload_inline_raw),
            trace_ref=None
            if data.get("trace_ref") is None
            else _require_non_empty_str(data.get("trace_ref"), field_name="trace_ref"),
            commit_ref=None
            if data.get("commit_ref") is None
            else _require_non_empty_str(data.get("commit_ref"), field_name="commit_ref"),
            delivery_id=None
            if data.get("delivery_id") is None
            else _require_non_empty_str(data.get("delivery_id"), field_name="delivery_id"),
            auth_key_id=None
            if data.get("auth_key_id") is None
            else _require_non_empty_str(data.get("auth_key_id"), field_name="auth_key_id"),
            transport_identity=None
            if data.get("transport_identity") is None
            else _require_non_empty_str(data.get("transport_identity"), field_name="transport_identity"),
        )
        envelope.validate()
        return envelope

    def validate(self) -> None:
        if self.mode not in FABRIC_MODES:
            raise ValueError(f"mode must be one of {sorted(FABRIC_MODES)}")
        if self.payload_inline is not None and not isinstance(self.payload_inline, dict):
            raise ValueError("payload_inline must be an object when provided")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "schema_version": str(self.schema_version),
            "message_type": str(self.message_type),
            "channel": str(self.channel),
            "mode": str(self.mode),
            "sender": str(self.sender),
            "recipient": self.recipient,
            "payload_ref": str(self.payload_ref),
            "payload_inline": None if self.payload_inline is None else dict(self.payload_inline),
            "trace_ref": self.trace_ref,
            "commit_ref": self.commit_ref,
            "delivery_id": self.delivery_id,
            "auth_key_id": self.auth_key_id,
            "transport_identity": self.transport_identity,
        }


__all__ = ["FABRIC_MODES", "FabricEnvelope"]
