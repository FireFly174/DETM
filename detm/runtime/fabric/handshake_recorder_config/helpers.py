"""Helper normalizers for handshake recorder attach config."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def normalize_validator_auth_key_ids(
    raw: Mapping[str, Sequence[str] | str] | Sequence[str] | str | None,
) -> dict[str, list[str]]:
    out: dict[str, set[str]] = {}

    def _add_pair(raw_validator: object, raw_key: object) -> None:
        validator_id = str(raw_validator).strip()
        key_id = str(raw_key).strip()
        if not validator_id or not key_id:
            return
        out.setdefault(validator_id, set()).add(key_id)

    def _parse_binding(binding: object) -> None:
        text = str(binding).strip()
        if not text:
            return
        chunks = [chunk.strip() for chunk in text.split(",") if chunk.strip()]
        for chunk in chunks:
            if "=" in chunk:
                validator_id, key_id = chunk.split("=", 1)
            elif ":" in chunk:
                validator_id, key_id = chunk.split(":", 1)
            else:
                continue
            _add_pair(validator_id, key_id)

    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        for validator_id, key_values in dict(raw).items():
            if isinstance(key_values, str):
                for key_id in [chunk.strip() for chunk in str(key_values).split(",") if chunk.strip()]:
                    _add_pair(validator_id, key_id)
            elif isinstance(key_values, Sequence):
                for key_id in list(key_values):
                    _add_pair(validator_id, key_id)
            else:
                _add_pair(validator_id, key_values)
    elif isinstance(raw, str):
        _parse_binding(raw)
    elif isinstance(raw, Sequence):
        for row in list(raw):
            _parse_binding(row)
    else:
        _parse_binding(raw)

    return {
        validator_id: sorted(list(key_ids))
        for validator_id, key_ids in sorted(out.items())
        if key_ids
    }


def normalize_transport_tls_identity_source(raw: str | object) -> str:
    source = str(raw).strip().lower()
    if source not in {"auto", "cn", "san", "fingerprint"}:
        return "auto"
    return source


def normalize_handshake_profile(raw: str | object) -> str:
    profile = str(raw).strip().lower()
    aliases = {
        "mvp": "mvp",
        "default": "mvp",
        "baseline": "mvp",
        "production": "production",
        "prod": "production",
        "strict": "production",
    }
    return aliases.get(profile, "mvp")


def normalize_delivery_guarantee_mode(raw: str | object) -> str:
    mode = str(raw).strip().lower()
    aliases = {
        "best_effort": "best_effort",
        "best-effort": "best_effort",
        "at_least_once": "at_least_once",
        "at-least-once": "at_least_once",
        "at_least_once_idempotent": "at_least_once_idempotent",
        "at-least-once-idempotent": "at_least_once_idempotent",
        "at_least_once+idempotency": "at_least_once_idempotent",
        "at-least-once+idempotency": "at_least_once_idempotent",
    }
    return aliases.get(mode, "at_least_once_idempotent")


__all__ = [
    "normalize_delivery_guarantee_mode",
    "normalize_handshake_profile",
    "normalize_transport_tls_identity_source",
    "normalize_validator_auth_key_ids",
]
