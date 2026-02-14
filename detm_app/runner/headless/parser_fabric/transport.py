"""Transport/auth/tls fabric parser arguments."""

from __future__ import annotations

import argparse


def add_transport_arguments(ap: argparse.ArgumentParser) -> None:
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


__all__ = ["add_transport_arguments"]
