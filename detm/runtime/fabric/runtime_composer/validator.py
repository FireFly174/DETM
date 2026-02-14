"""Validator builders for fabric runtime composition."""

from __future__ import annotations

from typing import Any

from detm.runtime.fabric import LocalFabricValidator, ReplaySamplePolicy
from detm.runtime.fabric.validator.policies import normalize_replay_policy_tier


def build_validator(*, rec: Any, artifact_resolver: Any) -> LocalFabricValidator:
    replay_tier = normalize_replay_policy_tier(getattr(rec, "replay_policy_tier", "sampled"))
    replay_stride = max(1, int(getattr(rec, "replay_sample_stride", 1) or 1))
    replay_enabled = bool(
        replay_tier == "strict_window"
        or (replay_tier == "sampled" and int(getattr(rec, "replay_sample_stride", 0)) > 0)
    )
    return LocalFabricValidator(
        validator_id=f"validator.{rec.node_id}",
        replay_policy=ReplaySamplePolicy(
            tier=replay_tier,
            enabled=bool(replay_enabled),
            sample_stride=replay_stride,
            sample_offset=0,
            strict_window_size=max(1, int(getattr(rec, "replay_strict_window_size", 128))),
        ),
        replay_checker=artifact_resolver.replay_check if replay_enabled else None,
    )


__all__ = ["build_validator"]
