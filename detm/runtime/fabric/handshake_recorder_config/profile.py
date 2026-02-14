"""Profile overlays for handshake recorder attach config."""

from __future__ import annotations

from typing import Any


def apply_handshake_profile(cfg: dict[str, Any]) -> dict[str, Any]:
    profile = str(cfg.get("handshake_profile", "mvp"))
    if profile != "production":
        return cfg

    required_validator_ids = [str(v).strip() for v in list(cfg.get("required_validator_ids", [])) if str(v).strip()]
    if not required_validator_ids:
        raise ValueError("handshake_profile=production requires non-empty required_validator_ids")

    auth_map = dict(cfg.get("validator_auth_key_ids", {}))
    transport_map = dict(cfg.get("validator_transport_identities", {}))
    if not auth_map and not transport_map:
        raise ValueError(
            "handshake_profile=production requires validator_auth_key_ids and/or validator_transport_identities"
        )

    if auth_map:
        missing_auth = [validator_id for validator_id in required_validator_ids if validator_id not in auth_map]
        if missing_auth:
            raise ValueError(
                "handshake_profile=production requires auth key-id bindings for required validators: "
                + ", ".join(sorted(missing_auth))
            )
        cfg["enforce_ack_auth_key_id_binding"] = True

    if transport_map:
        missing_transport = [
            validator_id for validator_id in required_validator_ids if validator_id not in transport_map
        ]
        if missing_transport:
            raise ValueError(
                "handshake_profile=production requires transport identity bindings for required validators: "
                + ", ".join(sorted(missing_transport))
            )
        cfg["enforce_ack_transport_identity_binding"] = True

    cfg["enforce_required_validator_ids"] = True
    cfg["enforce_active_validator_membership"] = True
    cfg["enforce_ack_sender_validator_match"] = True
    cfg["reject_on_any_reject"] = True
    return cfg


__all__ = ["apply_handshake_profile"]
