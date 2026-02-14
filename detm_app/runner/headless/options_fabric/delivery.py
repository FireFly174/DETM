"""Delivery-tracking fabric option resolution."""

from __future__ import annotations

from typing import Any

from detm_app.runner.headless.helpers import as_list


def resolve_delivery_fabric_options(*, args: Any, runner_defaults: dict[str, Any]) -> dict[str, Any]:
    fabric_delivery_required_receipts = (
        int(args.fabric_delivery_required_receipts)
        if args.fabric_delivery_required_receipts is not None
        else int(runner_defaults.get("fabric_delivery_required_receipts", 0))
    )
    fabric_delivery_guarantee_mode = (
        str(args.fabric_delivery_guarantee_mode)
        if args.fabric_delivery_guarantee_mode is not None
        else str(runner_defaults.get("fabric_delivery_guarantee_mode", "at_least_once_idempotent"))
    )
    if args.fabric_delivery_validator_set is not None:
        fabric_delivery_required_validator_ids = as_list(args.fabric_delivery_validator_set)
    else:
        fabric_delivery_required_validator_ids = as_list(runner_defaults.get("fabric_delivery_required_validator_ids"))
    fabric_delivery_enforce_required_validator_ids = (
        bool(args.fabric_delivery_enforce_validator_set)
        if args.fabric_delivery_enforce_validator_set is not None
        else bool(runner_defaults.get("fabric_delivery_enforce_required_validator_ids", False))
    )
    fabric_delivery_reject_on_any_reject = (
        bool(args.fabric_delivery_reject_on_any_reject)
        if args.fabric_delivery_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_delivery_reject_on_any_reject", False))
    )
    fabric_delivery_retry_interval_ms = (
        int(args.fabric_delivery_retry_interval_ms)
        if args.fabric_delivery_retry_interval_ms is not None
        else int(runner_defaults.get("fabric_delivery_retry_interval_ms", 100))
    )
    fabric_delivery_max_attempts = (
        int(args.fabric_delivery_max_attempts)
        if args.fabric_delivery_max_attempts is not None
        else int(runner_defaults.get("fabric_delivery_max_attempts", 3))
    )
    fabric_delivery_timeout_ms = (
        int(args.fabric_delivery_timeout_ms)
        if args.fabric_delivery_timeout_ms is not None
        else int(runner_defaults.get("fabric_delivery_timeout_ms", 500))
    )
    fabric_delivery_tracking_state_path = (
        str(args.fabric_delivery_tracking_state_path)
        if args.fabric_delivery_tracking_state_path is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_tracking_state_path") is None
            else str(runner_defaults.get("fabric_delivery_tracking_state_path"))
        )
    )
    fabric_delivery_ack_channel = (
        str(args.fabric_delivery_ack_channel)
        if args.fabric_delivery_ack_channel is not None
        else str(runner_defaults.get("fabric_delivery_ack_channel", "fabric.delivery.ack"))
    )
    fabric_delivery_emit_ack = (
        bool(args.fabric_delivery_emit_ack)
        if args.fabric_delivery_emit_ack is not None
        else bool(runner_defaults.get("fabric_delivery_emit_ack", True))
    )
    fabric_delivery_outbox_path = (
        str(args.fabric_delivery_outbox_path)
        if args.fabric_delivery_outbox_path is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_outbox_path") is None
            else str(runner_defaults.get("fabric_delivery_outbox_path"))
        )
    )
    raw_delivery_outbox_max_entries = runner_defaults.get("fabric_delivery_outbox_max_entries")
    fabric_delivery_outbox_max_entries = (
        int(args.fabric_delivery_outbox_max_entries)
        if args.fabric_delivery_outbox_max_entries is not None
        else (None if raw_delivery_outbox_max_entries is None else int(raw_delivery_outbox_max_entries))
    )
    raw_delivery_outbox_flush_limit = runner_defaults.get("fabric_delivery_outbox_flush_limit")
    fabric_delivery_outbox_flush_limit = (
        int(args.fabric_delivery_outbox_flush_limit)
        if args.fabric_delivery_outbox_flush_limit is not None
        else (None if raw_delivery_outbox_flush_limit is None else int(raw_delivery_outbox_flush_limit))
    )
    fabric_delivery_outbox_drop_policy = (
        str(args.fabric_delivery_outbox_drop_policy)
        if args.fabric_delivery_outbox_drop_policy is not None
        else str(runner_defaults.get("fabric_delivery_outbox_drop_policy", "audit_first"))
    )
    return {
        "fabric_delivery_required_receipts": fabric_delivery_required_receipts,
        "fabric_delivery_guarantee_mode": fabric_delivery_guarantee_mode,
        "fabric_delivery_required_validator_ids": fabric_delivery_required_validator_ids,
        "fabric_delivery_enforce_required_validator_ids": bool(fabric_delivery_enforce_required_validator_ids),
        "fabric_delivery_reject_on_any_reject": bool(fabric_delivery_reject_on_any_reject),
        "fabric_delivery_retry_interval_ms": fabric_delivery_retry_interval_ms,
        "fabric_delivery_max_attempts": fabric_delivery_max_attempts,
        "fabric_delivery_timeout_ms": fabric_delivery_timeout_ms,
        "fabric_delivery_tracking_state_path": fabric_delivery_tracking_state_path,
        "fabric_delivery_ack_channel": fabric_delivery_ack_channel,
        "fabric_delivery_emit_ack": bool(fabric_delivery_emit_ack),
        "fabric_delivery_outbox_path": fabric_delivery_outbox_path,
        "fabric_delivery_outbox_max_entries": fabric_delivery_outbox_max_entries,
        "fabric_delivery_outbox_flush_limit": fabric_delivery_outbox_flush_limit,
        "fabric_delivery_outbox_drop_policy": fabric_delivery_outbox_drop_policy,
    }


__all__ = ["resolve_delivery_fabric_options"]
