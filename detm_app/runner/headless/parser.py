"""CLI parser factory for DETM headless runner."""

from __future__ import annotations

import argparse

from detm.presets import preset_names

_FABRIC_DELIVERY_GUARANTEE_CHOICES = (
    "best_effort",
    "at_least_once",
    "at_least_once_idempotent",
)
_FABRIC_REPLAY_POLICY_TIER_CHOICES = (
    "off",
    "sampled",
    "strict_window",
)
_FABRIC_HANDSHAKE_PROFILE_CHOICES = (
    "mvp",
    "production",
)

def build_headless_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preset", default="default", choices=sorted(set(preset_names())), help="Packaged preset name")
    ap.add_argument("--config", default=None, help="Path to override config (.json or .py; may include `runner` defaults)")

    ap.add_argument("--backend", default=None, choices=["torch", "numpy"], help="Override backend")
    ap.add_argument("--device", default=None, help="Override device (e.g. cuda/cpu)")
    ap.add_argument("--width", type=int, default=None, help="Override lattice width")
    ap.add_argument("--height", type=int, default=None, help="Override lattice height")
    ap.add_argument("--boundary", default=None, choices=["periodic", "open"], help="Override boundary condition")

    ap.add_argument("--seed", type=int, default=None, help="Seed")
    ap.add_argument("--seed0", type=int, default=None, help="Seed start for --batch")
    ap.add_argument("--batch", type=int, default=None, help="Run N episodes with seeds seed0..seed0+N-1")

    ap.add_argument("--steps", type=int, default=None, help="Tick budget (see --steps-mode)")
    ap.add_argument(
        "--steps-mode",
        type=str,
        default=None,
        choices=["total", "per_symbol"],
        help="How to apply --steps: total budget or per symbol",
    )
    ap.add_argument("--symbols", nargs="*", default=None, help="Symbol IDs to apply (default: all)")
    ap.add_argument("--out", default=None, help="Output directory root (default: runs/out/run_<timestamp>)")

    ap.add_argument(
        "--viz",
        dest="viz",
        action="store_true",
        default=None,
        help="Start a local viz daemon and stream state updates",
    )
    ap.add_argument(
        "--no-viz",
        dest="viz",
        action="store_false",
        help="Disable viz streaming (overrides config)",
    )
    ap.add_argument("--viz-transport", default=None, choices=["tcp", "none"], help="Visualization transport")
    ap.add_argument(
        "--viz-connect",
        dest="viz_connect",
        action="store_true",
        default=None,
        help="Connect to an existing viz daemon (requires --viz-host/--viz-port)",
    )
    ap.add_argument("--viz-host", default=None, help="Viz daemon host (default: localhost)")
    ap.add_argument("--viz-port", type=int, default=None, help="Viz daemon port (0 = auto when starting locally)")
    ap.add_argument(
        "--viz-keep-open",
        dest="viz_keep_open",
        action="store_true",
        default=None,
        help="Do not terminate the locally started viz daemon after the run finishes",
    )
    ap.add_argument("--viz-every-steps", type=int, default=None, help="Send viz updates every N step_count increments")

    ap.add_argument(
        "--record-fields",
        dest="record_fields",
        action="store_true",
        default=None,
        help="Write `fields_hist.npz` with E/S/tau (+J approx) history",
    )
    ap.add_argument("--no-record-fields", dest="record_fields", action="store_false", help="Disable fields recording")
    ap.add_argument("--fields-every-steps", type=int, default=None, help="Record fields every N step_count increments")

    ap.add_argument(
        "--invariant-stream",
        action="append",
        default=None,
        help="Add invariant stream spec (e.g. inv0=1/10). Repeatable; comma-separated also accepted.",
    )
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
    ap.add_argument(
        "--fabric-transport",
        default=None,
        choices=["memory", "tcp"],
        help="Fabric transport adapter for handshake wiring",
    )
    ap.add_argument("--fabric-transport-host", default=None, help="Fabric transport host")
    ap.add_argument("--fabric-transport-port", type=int, default=None, help="Fabric transport port")
    ap.add_argument(
        "--fabric-transport-connect",
        dest="fabric_transport_connect",
        action="store_true",
        default=None,
        help="Connect to existing fabric relay (tcp only)",
    )
    ap.add_argument(
        "--fabric-transport-keep-open",
        dest="fabric_transport_keep_open",
        action="store_true",
        default=None,
        help="Keep local fabric relay open after run (tcp local start)",
    )
    ap.add_argument(
        "--fabric-transport-backpressure-max-pending",
        type=int,
        default=None,
        help="Max pending envelopes in live transport buffer (default: disabled)",
    )
    ap.add_argument(
        "--fabric-transport-backpressure-policy",
        choices=["block", "drop_oldest", "drop_newest", "fail"],
        default=None,
        help="Backpressure policy for live transport buffer overflow",
    )
    ap.add_argument(
        "--fabric-transport-backpressure-block-timeout-ms",
        type=int,
        default=None,
        help="Block policy timeout in ms for live transport buffer",
    )
    ap.add_argument(
        "--fabric-transport-dedup-ingress",
        dest="fabric_transport_dedup_ingress_enabled",
        action="store_true",
        default=None,
        help="Enable ingress idempotency/dedup cache for fabric transport",
    )
    ap.add_argument(
        "--fabric-no-transport-dedup-ingress",
        dest="fabric_transport_dedup_ingress_enabled",
        action="store_false",
        help="Disable ingress idempotency/dedup cache for fabric transport",
    )
    ap.add_argument(
        "--fabric-transport-dedup-ttl-ms",
        type=int,
        default=None,
        help="TTL in ms for transport ingress dedup cache entries",
    )
    ap.add_argument(
        "--fabric-transport-dedup-max-entries",
        type=int,
        default=None,
        help="Max entry count for transport ingress dedup cache",
    )
    ap.add_argument(
        "--fabric-transport-auth",
        dest="fabric_transport_auth_enabled",
        action="store_true",
        default=None,
        help="Enable TCP envelope auth (HMAC-SHA256)",
    )
    ap.add_argument(
        "--fabric-no-transport-auth",
        dest="fabric_transport_auth_enabled",
        action="store_false",
        help="Disable TCP envelope auth",
    )
    ap.add_argument(
        "--fabric-transport-auth-key",
        default=None,
        help="Shared auth key for TCP envelope HMAC",
    )
    ap.add_argument(
        "--fabric-transport-auth-key-id",
        default=None,
        help="Optional key id attached to signed TCP envelopes",
    )
    ap.add_argument(
        "--fabric-transport-tls",
        dest="fabric_transport_tls_enabled",
        action="store_true",
        default=None,
        help="Enable TLS for TCP fabric transport",
    )
    ap.add_argument(
        "--fabric-no-transport-tls",
        dest="fabric_transport_tls_enabled",
        action="store_false",
        help="Disable TLS for TCP fabric transport",
    )
    ap.add_argument(
        "--fabric-transport-tls-server-hostname",
        default=None,
        help="TLS server hostname override for certificate validation",
    )
    ap.add_argument(
        "--fabric-transport-tls-ca-file",
        default=None,
        help="CA bundle path for TCP TLS server verification",
    )
    ap.add_argument(
        "--fabric-transport-tls-cert-file",
        default=None,
        help="Client cert chain path for TCP TLS (optional mTLS)",
    )
    ap.add_argument(
        "--fabric-transport-tls-key-file",
        default=None,
        help="Client cert private key path for TCP TLS (optional mTLS)",
    )
    ap.add_argument(
        "--fabric-transport-tls-require-client-cert",
        dest="fabric_transport_tls_require_client_cert",
        action="store_true",
        default=None,
        help="Require client certificate verification on locally started TCP TLS relay",
    )
    ap.add_argument(
        "--fabric-no-transport-tls-require-client-cert",
        dest="fabric_transport_tls_require_client_cert",
        action="store_false",
        help="Do not require client certificate verification on local TCP TLS relay",
    )
    ap.add_argument(
        "--fabric-transport-tls-client-ca-file",
        default=None,
        help="CA bundle used by local TCP TLS relay to verify client certificates",
    )
    ap.add_argument(
        "--fabric-transport-tls-insecure-skip-verify",
        dest="fabric_transport_tls_insecure_skip_verify",
        action="store_true",
        default=None,
        help="Disable certificate and hostname verification for TCP TLS (dev only)",
    )
    ap.add_argument(
        "--fabric-no-transport-tls-insecure-skip-verify",
        dest="fabric_transport_tls_insecure_skip_verify",
        action="store_false",
        help="Enable certificate and hostname verification for TCP TLS",
    )
    ap.add_argument(
        "--fabric-transport-tls-identity-source",
        choices=["auto", "cn", "san", "fingerprint"],
        default=None,
        help="Identity source injected into transport_identity for TLS peers",
    )
    ap.add_argument(
        "--fabric-transport-tls-fallback-to-fingerprint",
        dest="fabric_transport_tls_identity_fallback_to_fingerprint",
        action="store_true",
        default=None,
        help="Fallback to cert fingerprint when selected identity source is missing",
    )
    ap.add_argument(
        "--fabric-no-transport-tls-fallback-to-fingerprint",
        dest="fabric_transport_tls_identity_fallback_to_fingerprint",
        action="store_false",
        help="Disable fingerprint fallback when selected identity source is missing",
    )
    ap.add_argument(
        "--fabric-artifact-dir",
        default=None,
        help="Shared artifact directory for durable commit/ack resolver (default: disabled)",
    )
    ap.add_argument(
        "--fabric-inline-bridge",
        dest="fabric_inline_bridge",
        action="store_true",
        default=None,
        help="Enable inline payload bridge in fabric envelopes (default: enabled)",
    )
    ap.add_argument(
        "--fabric-no-inline-bridge",
        dest="fabric_inline_bridge",
        action="store_false",
        help="Disable inline payload bridge in fabric envelopes (requires shared artifact resolver)",
    )
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

    ap.add_argument("--list-symbols", action="store_true", help="Print known symbol IDs and exit")
    return ap


__all__ = ["build_headless_parser"]
