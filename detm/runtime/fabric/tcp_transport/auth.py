"""Auth helpers for TCP fabric transport payload signing and verification."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def compute_auth_sig(*, auth_key: str | None, payload: dict[str, object]) -> str:
    key = str(auth_key or "").encode("utf-8")
    canonical = dict(payload)
    canonical.pop("auth_sig", None)
    # Relay can inject transport identity metadata after sender-side signing.
    canonical.pop("transport_identity", None)
    body = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def attach_auth_payload(transport: Any, payload: dict[str, object]) -> dict[str, object]:
    out = dict(payload)
    key_id = str(getattr(transport, "auth_key_id", "") or "").strip()
    if key_id:
        out["auth_key_id"] = key_id
    out["auth_sig"] = compute_auth_sig(auth_key=getattr(transport, "auth_key", None), payload=out)
    return out


def verify_auth_payload(transport: Any, payload: dict[str, object]) -> bool:
    raw_sig = str(payload.get("auth_sig", "")).strip()
    if not raw_sig:
        transport._auth_missing_total += 1
        transport._auth_rejected_total += 1
        return False
    expected_key_id = str(getattr(transport, "auth_key_id", "") or "").strip()
    actual_key_id = str(payload.get("auth_key_id", "")).strip()
    if expected_key_id and actual_key_id and actual_key_id != expected_key_id:
        transport._auth_bad_key_id_total += 1
        transport._auth_rejected_total += 1
        return False
    expected_sig = compute_auth_sig(auth_key=getattr(transport, "auth_key", None), payload=payload)
    ok = hmac.compare_digest(expected_sig, raw_sig)
    if ok:
        transport._auth_verified_total += 1
        return True
    transport._auth_rejected_total += 1
    return False


__all__ = ["attach_auth_payload", "compute_auth_sig", "verify_auth_payload"]
