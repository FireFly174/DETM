"""Replay/coordination fabric parser arguments."""

from __future__ import annotations

import argparse

_FABRIC_REPLAY_POLICY_TIER_CHOICES = (
    "off",
    "sampled",
    "strict_window",
)


def add_coordination_arguments(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--fabric-replay-sample-stride",
        type=int,
        default=None,
        help="Replay-check sampling stride for validator (0 disables sampling)",
    )
    ap.add_argument(
        "--fabric-replay-policy-tier",
        choices=sorted(_FABRIC_REPLAY_POLICY_TIER_CHOICES),
        default=None,
        help="Replay policy tier for validator checks: off | sampled | strict_window",
    )
    ap.add_argument(
        "--fabric-replay-strict-window-size",
        type=int,
        default=None,
        help="Window size in ticks for strict_window replay policy (default: 128)",
    )
    ap.add_argument(
        "--fabric-validator-coordination-state-path",
        default=None,
        help="Path to persisted validator coordination state file (default: in-memory)",
    )
    ap.add_argument(
        "--fabric-validator-coordination-replica-state",
        action="append",
        default=None,
        help="Replica validator-coordination state file path (repeatable, also accepts comma-separated values)",
    )
    ap.add_argument(
        "--fabric-validator-coordination-read-quorum",
        type=int,
        default=None,
        help="Read quorum for replicated validator coordination state (default: majority)",
    )
    ap.add_argument(
        "--fabric-validator-coordination-write-quorum",
        type=int,
        default=None,
        help="Write quorum for replicated validator coordination state (default: majority)",
    )
    ap.add_argument(
        "--fabric-epoch-state-path",
        default=None,
        help="Shared epoch/watermark state file path for distributed coordinator (default: in-memory)",
    )
    ap.add_argument(
        "--fabric-epoch-replica-state",
        action="append",
        default=None,
        help="Replica epoch-state file path (repeatable, also accepts comma-separated values)",
    )
    ap.add_argument(
        "--fabric-epoch-read-quorum",
        type=int,
        default=None,
        help="Read quorum for replicated epoch coordinator (default: majority)",
    )
    ap.add_argument(
        "--fabric-epoch-write-quorum",
        type=int,
        default=None,
        help="Write quorum for replicated epoch coordinator (default: majority)",
    )
    ap.add_argument(
        "--fabric-epoch-lock-timeout-ms",
        type=int,
        default=None,
        help="Epoch-state lock timeout in ms for file coordinator (default: 5000)",
    )
    ap.add_argument(
        "--fabric-epoch-lock-poll-ms",
        type=int,
        default=None,
        help="Epoch-state lock poll interval in ms (default: 10)",
    )
    ap.add_argument(
        "--fabric-epoch-lock-stale-ms",
        type=int,
        default=None,
        help="Epoch-state stale lock threshold in ms (default: 30000, <=0 disables stale cleanup)",
    )
    ap.add_argument(
        "--fabric-epoch-consensus",
        dest="fabric_epoch_consensus_enabled",
        action="store_true",
        default=None,
        help="Enable transport-based pre-consensus for epoch decisions",
    )
    ap.add_argument(
        "--fabric-no-epoch-consensus",
        dest="fabric_epoch_consensus_enabled",
        action="store_false",
        help="Disable transport-based pre-consensus for epoch decisions",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-required-total-accepts",
        type=int,
        default=None,
        help="Total accepts (including local) required for epoch consensus (default: 1)",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-timeout-ms",
        type=int,
        default=None,
        help="Timeout in ms for epoch consensus proposal collection (default: 200)",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-max-attempts",
        type=int,
        default=None,
        help="Maximum retry attempts for epoch consensus proposal rounds (default: 1)",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-reject-on-any-reject",
        dest="fabric_epoch_consensus_reject_on_any_reject",
        action="store_true",
        default=None,
        help="Reject epoch proposal if any peer vote is rejected",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-channel",
        default=None,
        help="Transport channel for epoch consensus proposals/votes (default: fabric.epoch)",
    )
__all__ = ["add_coordination_arguments"]
