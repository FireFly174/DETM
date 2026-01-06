"""Schema registry and version helpers for DETM integration."""

from __future__ import annotations

DETM_CONFIG_V1 = "1.1.0"
DETM_STATE_V1 = "1.0.0"
DETM_SIGNATURE_V1 = "1.0.0"


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
    }


__all__ = ["DETM_CONFIG_V1", "DETM_SIGNATURE_V1", "DETM_STATE_V1", "get_schema_versions"]
