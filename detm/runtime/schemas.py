"""Schema registry and version helpers for DETM integration (`detm.runtime`)."""

from __future__ import annotations

DETM_CONFIG_V1 = "1.24.0"
DETM_STATE_V1 = "1.0.0"
DETM_SIGNATURE_V1 = "1.0.0"
DETM_LEVEL_POLICY_V1 = "1.16.0"
DETM_COMMIT_PACKET_V1 = "1.0.0"
DETM_FABRIC_ENVELOPE_V1 = "1.0.0"
DETM_FABRIC_ACK_V1 = "1.0.0"


def get_schema_versions() -> dict[str, str]:
    """Return a mapping of public schemas exposed by DETM.

    The registry can be queried by external runtimes to ensure compatibility
    without importing heavy dependencies. New schemas should bump the minor
    version when adding fields in a backward-compatible way and the major
    version for breaking changes.
    """

    return {
        "config": DETM_CONFIG_V1,
        "state": DETM_STATE_V1,
        "signature": DETM_SIGNATURE_V1,
        "level_policy": DETM_LEVEL_POLICY_V1,
        "commit_packet": DETM_COMMIT_PACKET_V1,
        "fabric_envelope": DETM_FABRIC_ENVELOPE_V1,
        "fabric_ack": DETM_FABRIC_ACK_V1,
    }


__all__ = [
    "DETM_COMMIT_PACKET_V1",
    "DETM_CONFIG_V1",
    "DETM_FABRIC_ACK_V1",
    "DETM_FABRIC_ENVELOPE_V1",
    "DETM_LEVEL_POLICY_V1",
    "DETM_SIGNATURE_V1",
    "DETM_STATE_V1",
    "get_schema_versions",
]
