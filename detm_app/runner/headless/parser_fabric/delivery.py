"""Delivery-tracking fabric parser arguments."""

from __future__ import annotations

import argparse

_FABRIC_DELIVERY_GUARANTEE_CHOICES = (
    "best_effort",
    "at_least_once",
    "at_least_once_idempotent",
)


def add_delivery_arguments(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--fabric-delivery-outbox-path",
        default=None,
        help="Path to file-backed fabric delivery outbox (default: <run>/fabric_delivery_outbox.jsonl)",
    )
    ap.add_argument(
        "--fabric-delivery-outbox-max-entries",
        type=int,
        default=None,
        help="Max number of pending envelopes kept in delivery outbox (default: unlimited)",
    )
    ap.add_argument(
        "--fabric-delivery-outbox-flush-limit",
        type=int,
        default=None,
        help="Max queued envelopes flushed per publish attempt (default: all pending)",
    )
    ap.add_argument(
        "--fabric-delivery-outbox-drop-policy",
        choices=["audit_first", "oldest", "newest"],
        default=None,
        help="Outbox overflow policy: prefer dropping audit envelopes or FIFO/LIFO style",
    )
    ap.add_argument(
        "--fabric-split-mode-channels",
        dest="fabric_split_mode_channels",
        action="store_true",
        default=None,
        help="Use separate fabric channels for realtime/audit envelopes",
    )
    ap.add_argument(
        "--fabric-no-split-mode-channels",
        dest="fabric_split_mode_channels",
        action="store_false",
        help="Use shared fabric channels for realtime/audit envelopes",
    )
    ap.add_argument(
        "--fabric-delivery-required-receipts",
        type=int,
        default=None,
        help="Required number of delivery_ack receipts per commit envelope (0 disables receipt tracking)",
    )
    ap.add_argument(
        "--fabric-delivery-guarantee-mode",
        choices=sorted(_FABRIC_DELIVERY_GUARANTEE_CHOICES),
        default=None,
        help="Delivery semantics mode: best_effort | at_least_once | at_least_once_idempotent",
    )
    ap.add_argument(
        "--fabric-delivery-validator-set",
        default=None,
        help="Comma-separated required validator ids for delivery receipts",
    )
    ap.add_argument(
        "--fabric-delivery-enforce-validator-set",
        dest="fabric_delivery_enforce_validator_set",
        action="store_true",
        default=None,
        help="Require delivery receipts from all ids listed in --fabric-delivery-validator-set",
    )
    ap.add_argument(
        "--fabric-no-delivery-enforce-validator-set",
        dest="fabric_delivery_enforce_validator_set",
        action="store_false",
        help="Do not enforce full delivery validator set",
    )
    ap.add_argument(
        "--fabric-delivery-reject-on-any-reject",
        dest="fabric_delivery_reject_on_any_reject",
        action="store_true",
        default=None,
        help="Reject tracked delivery when any delivery_ack has rejected/error status",
    )
    ap.add_argument(
        "--fabric-no-delivery-reject-on-any-reject",
        dest="fabric_delivery_reject_on_any_reject",
        action="store_false",
        help="Do not reject tracked delivery on single rejected/error receipt",
    )
    ap.add_argument(
        "--fabric-delivery-retry-interval-ms",
        type=int,
        default=None,
        help="Retry interval in ms for pending delivery receipts",
    )
    ap.add_argument(
        "--fabric-delivery-max-attempts",
        type=int,
        default=None,
        help="Maximum publish attempts per tracked commit delivery",
    )
    ap.add_argument(
        "--fabric-delivery-timeout-ms",
        type=int,
        default=None,
        help="Timeout in ms for tracked commit delivery receipts",
    )
    ap.add_argument(
        "--fabric-delivery-tracking-state-path",
        default=None,
        help="Path to persisted delivery tracking/receipt state file (default: <run>/fabric_delivery_tracking_state.json)",
    )
    ap.add_argument(
        "--fabric-delivery-ack-channel",
        default=None,
        help="Channel for delivery_ack envelopes",
    )
    ap.add_argument(
        "--fabric-delivery-emit-ack",
        dest="fabric_delivery_emit_ack",
        action="store_true",
        default=None,
        help="Emit delivery_ack envelopes on commit receive",
    )
    ap.add_argument(
        "--fabric-no-delivery-emit-ack",
        dest="fabric_delivery_emit_ack",
        action="store_false",
        help="Disable delivery_ack envelope emission on commit receive",
    )


__all__ = ["add_delivery_arguments"]
