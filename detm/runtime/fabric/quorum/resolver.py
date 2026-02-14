"""Ack resolution helpers for quorum coordinator."""

from __future__ import annotations

from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FabricEnvelope


def ack_from_envelope_inline(envelope: FabricEnvelope) -> ProofAck | TrustAck | None:
    payload = envelope.payload_inline
    if not isinstance(payload, dict):
        return None
    try:
        if envelope.message_type == "proof_ack":
            return ProofAck.from_dict(payload)
        if envelope.message_type == "trust_ack":
            return TrustAck.from_dict(payload)
    except Exception:
        return None
    return None


__all__ = ["ack_from_envelope_inline"]


