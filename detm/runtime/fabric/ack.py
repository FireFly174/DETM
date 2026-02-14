"""Validator acknowledgements for fabric commit flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from detm.runtime.schemas import DETM_FABRIC_ACK_V1

# ARCH-MARKERS:
# - LAYER_BAND: L4-L5
# - ABSTRACT_DISTANCE: 0 (ack contracts explicitly separated from transport/validation)
# - OOP_TECH_DEBT: signed witness bundles and quorum metadata


ACK_STATUS = {"accepted", "rejected"}


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
class ProofAck:
    """Acknowledgement that proof checks were executed for a commit."""

    schema_version: str = DETM_FABRIC_ACK_V1
    ack_type: str = "proof_ack"
    validator_id: str = "validator.local"
    node_id: str = "node.local"
    commit_ref: str = "commit:0"
    status: str = "accepted"  # accepted | rejected
    reason: str | None = None
    proof_ref: str | None = None
    epoch: int | None = None
    watermark: int | None = None
    signature: str = "sig:unsigned"
    created_at_ms: int = 0

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProofAck":
        data = dict(payload)
        ack = cls(
            schema_version=str(data.get("schema_version", DETM_FABRIC_ACK_V1)),
            ack_type=str(data.get("ack_type", "proof_ack")).strip().lower(),
            validator_id=_require_non_empty_str(data.get("validator_id", ""), field_name="validator_id"),
            node_id=_require_non_empty_str(data.get("node_id", ""), field_name="node_id"),
            commit_ref=_require_non_empty_str(data.get("commit_ref", ""), field_name="commit_ref"),
            status=str(data.get("status", "accepted")).strip().lower(),
            reason=None
            if data.get("reason") is None
            else _require_non_empty_str(data.get("reason"), field_name="reason"),
            proof_ref=None
            if data.get("proof_ref") is None
            else _require_non_empty_str(data.get("proof_ref"), field_name="proof_ref"),
            epoch=None if data.get("epoch") is None else _as_non_negative_int(data.get("epoch"), field_name="epoch"),
            watermark=None
            if data.get("watermark") is None
            else _as_non_negative_int(data.get("watermark"), field_name="watermark"),
            signature=_require_non_empty_str(data.get("signature", ""), field_name="signature"),
            created_at_ms=_as_non_negative_int(data.get("created_at_ms", 0), field_name="created_at_ms"),
        )
        ack.validate()
        return ack

    def validate(self) -> None:
        if self.ack_type != "proof_ack":
            raise ValueError("ack_type must be proof_ack for ProofAck")
        if self.status not in ACK_STATUS:
            raise ValueError(f"status must be one of {sorted(ACK_STATUS)}")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "schema_version": str(self.schema_version),
            "ack_type": str(self.ack_type),
            "validator_id": str(self.validator_id),
            "node_id": str(self.node_id),
            "commit_ref": str(self.commit_ref),
            "status": str(self.status),
            "reason": self.reason,
            "proof_ref": self.proof_ref,
            "epoch": self.epoch,
            "watermark": self.watermark,
            "signature": str(self.signature),
            "created_at_ms": int(self.created_at_ms),
        }


@dataclass(frozen=True)
class TrustAck:
    """Acknowledgement that trust checks passed for a commit/node tuple."""

    schema_version: str = DETM_FABRIC_ACK_V1
    ack_type: str = "trust_ack"
    validator_id: str = "validator.local"
    node_id: str = "node.local"
    commit_ref: str = "commit:0"
    status: str = "accepted"  # accepted | rejected
    reason: str | None = None
    trust_ref: str | None = None
    signature: str = "sig:unsigned"
    created_at_ms: int = 0

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrustAck":
        data = dict(payload)
        ack = cls(
            schema_version=str(data.get("schema_version", DETM_FABRIC_ACK_V1)),
            ack_type=str(data.get("ack_type", "trust_ack")).strip().lower(),
            validator_id=_require_non_empty_str(data.get("validator_id", ""), field_name="validator_id"),
            node_id=_require_non_empty_str(data.get("node_id", ""), field_name="node_id"),
            commit_ref=_require_non_empty_str(data.get("commit_ref", ""), field_name="commit_ref"),
            status=str(data.get("status", "accepted")).strip().lower(),
            reason=None
            if data.get("reason") is None
            else _require_non_empty_str(data.get("reason"), field_name="reason"),
            trust_ref=None
            if data.get("trust_ref") is None
            else _require_non_empty_str(data.get("trust_ref"), field_name="trust_ref"),
            signature=_require_non_empty_str(data.get("signature", ""), field_name="signature"),
            created_at_ms=_as_non_negative_int(data.get("created_at_ms", 0), field_name="created_at_ms"),
        )
        ack.validate()
        return ack

    def validate(self) -> None:
        if self.ack_type != "trust_ack":
            raise ValueError("ack_type must be trust_ack for TrustAck")
        if self.status not in ACK_STATUS:
            raise ValueError(f"status must be one of {sorted(ACK_STATUS)}")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "schema_version": str(self.schema_version),
            "ack_type": str(self.ack_type),
            "validator_id": str(self.validator_id),
            "node_id": str(self.node_id),
            "commit_ref": str(self.commit_ref),
            "status": str(self.status),
            "reason": self.reason,
            "trust_ref": self.trust_ref,
            "signature": str(self.signature),
            "created_at_ms": int(self.created_at_ms),
        }


__all__ = ["ACK_STATUS", "ProofAck", "TrustAck"]
