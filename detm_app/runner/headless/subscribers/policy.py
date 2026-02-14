"""Storage policy helpers for headless subscribers."""

from __future__ import annotations

from detm.runtime.config import DETMConfig


def storage_policy(*, config: DETMConfig, level_name: str, artifact: str) -> dict[str, int]:
    return config.resolve_artifact_storage_policy(artifact=str(artifact), level=str(level_name))


__all__ = ["storage_policy"]
