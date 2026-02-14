"""Handshake/quorum fabric parser arguments."""

from __future__ import annotations

import argparse

_FABRIC_HANDSHAKE_PROFILE_CHOICES = (
    "mvp",
    "production",
)


def add_handshake_arguments(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--fabric-handshake",
        dest="fabric_handshake",
        action="store_true",
        default=None,
        help="Enable local fabric handshake artifacts (`fabric_acks.jsonl` + envelopes)",
    )
    ap.add_argument(
        "--no-fabric-handshake",
        dest="fabric_handshake",
        action="store_false",
        help="Disable local fabric handshake artifacts",
    )
    ap.add_argument(
        "--fabric-proof-quorum",
        type=int,
        default=None,
        help="Required number of accepted proof_ack for quorum (default: 1)",
    )
    ap.add_argument(
        "--fabric-trust-quorum",
        type=int,
        default=None,
        help="Required number of accepted trust_ack for quorum (default: 1)",
    )
    ap.add_argument(
        "--fabric-unique-proof-validators",
        type=int,
        default=None,
        help="Required number of unique validators in accepted proof_ack set (default: 1)",
    )
    ap.add_argument(
        "--fabric-unique-trust-validators",
        type=int,
        default=None,
        help="Required number of unique validators in accepted trust_ack set (default: 1)",
    )
    ap.add_argument(
        "--fabric-validator-set",
        default=None,
        help="Comma-separated required validator ids (used when enforce flag is enabled)",
    )
    ap.add_argument(
        "--fabric-handshake-profile",
        choices=sorted(_FABRIC_HANDSHAKE_PROFILE_CHOICES),
        default=None,
        help="Handshake hardening profile: mvp | production",
    )
    ap.add_argument(
        "--fabric-enforce-validator-set",
        dest="fabric_enforce_validator_set",
        action="store_true",
        default=None,
        help="Enforce presence of validator ids from --fabric-validator-set in proof and trust ack sets",
    )
    ap.add_argument(
        "--fabric-enforce-active-validator-membership",
        dest="fabric_enforce_active_validator_membership",
        action="store_true",
        default=None,
        help="Drop ack envelopes from validator ids outside active validator registry",
    )
    ap.add_argument(
        "--fabric-no-enforce-active-validator-membership",
        dest="fabric_enforce_active_validator_membership",
        action="store_false",
        help="Allow ack envelopes from validator ids outside active validator registry",
    )
    ap.add_argument(
        "--fabric-enforce-ack-sender-validator-match",
        dest="fabric_enforce_ack_sender_validator_match",
        action="store_true",
        default=None,
        help="Require envelope sender to match ack.validator_id for inline ack payloads",
    )
    ap.add_argument(
        "--fabric-no-enforce-ack-sender-validator-match",
        dest="fabric_enforce_ack_sender_validator_match",
        action="store_false",
        help="Do not enforce sender==ack.validator_id binding for inline ack payloads",
    )
    ap.add_argument(
        "--fabric-enforce-ack-auth-key-id-binding",
        dest="fabric_enforce_ack_auth_key_id_binding",
        action="store_true",
        default=None,
        help="Require envelope auth_key_id to match configured key ids for each validator",
    )
    ap.add_argument(
        "--fabric-no-enforce-ack-auth-key-id-binding",
        dest="fabric_enforce_ack_auth_key_id_binding",
        action="store_false",
        help="Disable validator/auth_key_id binding checks on ack ingress",
    )
    ap.add_argument(
        "--fabric-validator-auth-key-id",
        action="append",
        default=None,
        help="Validator/auth key-id binding rule (format: validator_id=key_id, repeatable, comma-separated supported)",
    )
    ap.add_argument(
        "--fabric-enforce-ack-transport-identity-binding",
        dest="fabric_enforce_ack_transport_identity_binding",
        action="store_true",
        default=None,
        help="Require envelope transport_identity to match configured identities per validator",
    )
    ap.add_argument(
        "--fabric-no-enforce-ack-transport-identity-binding",
        dest="fabric_enforce_ack_transport_identity_binding",
        action="store_false",
        help="Disable validator/transport_identity binding checks on ack ingress",
    )
    ap.add_argument(
        "--fabric-validator-transport-identity",
        action="append",
        default=None,
        help="Validator/transport identity binding rule (format: validator_id=identity, repeatable, comma-separated supported)",
    )
    ap.add_argument(
        "--fabric-reject-on-any-reject",
        dest="fabric_reject_on_any_reject",
        action="store_true",
        default=None,
        help="Reject commit quorum if any ack is rejected",
    )
    ap.add_argument(
        "--fabric-retry-attempts",
        type=int,
        default=None,
        help="Ack envelope publish retry attempts (default: 2)",
    )
    ap.add_argument(
        "--fabric-commit-retry-attempts",
        type=int,
        default=None,
        help="Commit envelope publish retry attempts (default: 2)",
    )
    ap.add_argument(
        "--fabric-pending-timeout-ms",
        type=int,
        default=None,
        help="Pending quorum timeout in ms (default: disabled)",
    )


__all__ = ["add_handshake_arguments"]
