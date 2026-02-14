"""Replay/coordination fabric option resolution."""

from __future__ import annotations

from typing import Any

from detm_app.runner.headless.helpers import as_list, flatten_list_args


def resolve_coordination_fabric_options(*, args: Any, runner_defaults: dict[str, Any]) -> dict[str, Any]:
    fabric_replay_sample_stride = (
        int(args.fabric_replay_sample_stride)
        if args.fabric_replay_sample_stride is not None
        else int(runner_defaults.get("fabric_replay_sample_stride", 0))
    )
    fabric_replay_policy_tier = (
        str(args.fabric_replay_policy_tier)
        if args.fabric_replay_policy_tier is not None
        else str(runner_defaults.get("fabric_replay_policy_tier", "sampled"))
    )
    fabric_replay_strict_window_size = (
        int(args.fabric_replay_strict_window_size)
        if args.fabric_replay_strict_window_size is not None
        else int(runner_defaults.get("fabric_replay_strict_window_size", 128))
    )
    fabric_validator_coordination_state_path = (
        str(args.fabric_validator_coordination_state_path)
        if args.fabric_validator_coordination_state_path is not None
        else (
            None
            if runner_defaults.get("fabric_validator_coordination_state_path") is None
            else str(runner_defaults.get("fabric_validator_coordination_state_path"))
        )
    )
    if args.fabric_validator_coordination_replica_state is not None:
        fabric_validator_coordination_replica_state_paths = flatten_list_args(
            list(args.fabric_validator_coordination_replica_state)
        )
    else:
        fabric_validator_coordination_replica_state_paths = as_list(
            runner_defaults.get("fabric_validator_coordination_replica_state_paths")
        )
    raw_validator_read_quorum = runner_defaults.get("fabric_validator_coordination_replica_read_quorum")
    fabric_validator_coordination_replica_read_quorum = (
        int(args.fabric_validator_coordination_read_quorum)
        if args.fabric_validator_coordination_read_quorum is not None
        else (None if raw_validator_read_quorum is None else int(raw_validator_read_quorum))
    )
    raw_validator_write_quorum = runner_defaults.get("fabric_validator_coordination_replica_write_quorum")
    fabric_validator_coordination_replica_write_quorum = (
        int(args.fabric_validator_coordination_write_quorum)
        if args.fabric_validator_coordination_write_quorum is not None
        else (None if raw_validator_write_quorum is None else int(raw_validator_write_quorum))
    )
    fabric_epoch_state_path = (
        str(args.fabric_epoch_state_path)
        if args.fabric_epoch_state_path is not None
        else (
            None
            if runner_defaults.get("fabric_epoch_state_path") is None
            else str(runner_defaults.get("fabric_epoch_state_path"))
        )
    )
    if args.fabric_epoch_replica_state is not None:
        fabric_epoch_replica_state_paths = flatten_list_args(list(args.fabric_epoch_replica_state))
    else:
        fabric_epoch_replica_state_paths = as_list(runner_defaults.get("fabric_epoch_replica_state_paths"))
    raw_epoch_read_quorum = runner_defaults.get("fabric_epoch_replica_read_quorum")
    fabric_epoch_replica_read_quorum = (
        int(args.fabric_epoch_read_quorum)
        if args.fabric_epoch_read_quorum is not None
        else (None if raw_epoch_read_quorum is None else int(raw_epoch_read_quorum))
    )
    raw_epoch_write_quorum = runner_defaults.get("fabric_epoch_replica_write_quorum")
    fabric_epoch_replica_write_quorum = (
        int(args.fabric_epoch_write_quorum)
        if args.fabric_epoch_write_quorum is not None
        else (None if raw_epoch_write_quorum is None else int(raw_epoch_write_quorum))
    )
    fabric_epoch_lock_timeout_ms = (
        int(args.fabric_epoch_lock_timeout_ms)
        if args.fabric_epoch_lock_timeout_ms is not None
        else int(runner_defaults.get("fabric_epoch_lock_timeout_ms", 5000))
    )
    fabric_epoch_lock_poll_ms = (
        int(args.fabric_epoch_lock_poll_ms)
        if args.fabric_epoch_lock_poll_ms is not None
        else int(runner_defaults.get("fabric_epoch_lock_poll_ms", 10))
    )
    raw_stale = (
        args.fabric_epoch_lock_stale_ms
        if args.fabric_epoch_lock_stale_ms is not None
        else runner_defaults.get("fabric_epoch_lock_stale_ms", 30000)
    )
    fabric_epoch_lock_stale_ms = None if raw_stale is None or int(raw_stale) <= 0 else int(raw_stale)
    fabric_epoch_consensus_enabled = (
        bool(args.fabric_epoch_consensus_enabled)
        if args.fabric_epoch_consensus_enabled is not None
        else bool(runner_defaults.get("fabric_epoch_consensus_enabled", False))
    )
    fabric_epoch_consensus_required_total_accepts = (
        int(args.fabric_epoch_consensus_required_total_accepts)
        if args.fabric_epoch_consensus_required_total_accepts is not None
        else int(runner_defaults.get("fabric_epoch_consensus_required_total_accepts", 1))
    )
    fabric_epoch_consensus_timeout_ms = (
        int(args.fabric_epoch_consensus_timeout_ms)
        if args.fabric_epoch_consensus_timeout_ms is not None
        else int(runner_defaults.get("fabric_epoch_consensus_timeout_ms", 200))
    )
    fabric_epoch_consensus_max_attempts = (
        int(args.fabric_epoch_consensus_max_attempts)
        if args.fabric_epoch_consensus_max_attempts is not None
        else int(runner_defaults.get("fabric_epoch_consensus_max_attempts", 1))
    )
    fabric_epoch_consensus_reject_on_any_reject = (
        bool(args.fabric_epoch_consensus_reject_on_any_reject)
        if args.fabric_epoch_consensus_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_epoch_consensus_reject_on_any_reject", False))
    )
    fabric_epoch_consensus_channel = (
        str(args.fabric_epoch_consensus_channel)
        if args.fabric_epoch_consensus_channel is not None
        else str(runner_defaults.get("fabric_epoch_consensus_channel", "fabric.epoch"))
    )
    fabric_split_mode_channels = (
        bool(args.fabric_split_mode_channels)
        if args.fabric_split_mode_channels is not None
        else bool(runner_defaults.get("fabric_split_mode_channels", False))
    )
    return {
        "fabric_replay_sample_stride": fabric_replay_sample_stride,
        "fabric_replay_policy_tier": fabric_replay_policy_tier,
        "fabric_replay_strict_window_size": fabric_replay_strict_window_size,
        "fabric_validator_coordination_state_path": fabric_validator_coordination_state_path,
        "fabric_validator_coordination_replica_state_paths": fabric_validator_coordination_replica_state_paths,
        "fabric_validator_coordination_replica_read_quorum": fabric_validator_coordination_replica_read_quorum,
        "fabric_validator_coordination_replica_write_quorum": fabric_validator_coordination_replica_write_quorum,
        "fabric_epoch_state_path": fabric_epoch_state_path,
        "fabric_epoch_replica_state_paths": fabric_epoch_replica_state_paths,
        "fabric_epoch_replica_read_quorum": fabric_epoch_replica_read_quorum,
        "fabric_epoch_replica_write_quorum": fabric_epoch_replica_write_quorum,
        "fabric_epoch_lock_timeout_ms": fabric_epoch_lock_timeout_ms,
        "fabric_epoch_lock_poll_ms": fabric_epoch_lock_poll_ms,
        "fabric_epoch_lock_stale_ms": fabric_epoch_lock_stale_ms,
        "fabric_epoch_consensus_enabled": bool(fabric_epoch_consensus_enabled),
        "fabric_epoch_consensus_required_total_accepts": fabric_epoch_consensus_required_total_accepts,
        "fabric_epoch_consensus_timeout_ms": fabric_epoch_consensus_timeout_ms,
        "fabric_epoch_consensus_max_attempts": fabric_epoch_consensus_max_attempts,
        "fabric_epoch_consensus_reject_on_any_reject": bool(fabric_epoch_consensus_reject_on_any_reject),
        "fabric_epoch_consensus_channel": fabric_epoch_consensus_channel,
        "fabric_split_mode_channels": bool(fabric_split_mode_channels),
    }


__all__ = ["resolve_coordination_fabric_options"]
