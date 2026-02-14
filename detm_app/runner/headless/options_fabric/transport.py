"""Transport/auth/tls fabric option resolution."""

from __future__ import annotations

from typing import Any


def resolve_transport_fabric_options(*, args: Any, runner_defaults: dict[str, Any]) -> dict[str, Any]:
    fabric_transport = (
        str(args.fabric_transport)
        if args.fabric_transport is not None
        else str(runner_defaults.get("fabric_transport", "memory"))
    )
    fabric_transport_host = (
        str(args.fabric_transport_host)
        if args.fabric_transport_host is not None
        else str(runner_defaults.get("fabric_transport_host", "127.0.0.1"))
    )
    raw_transport_port = runner_defaults.get("fabric_transport_port", 0)
    fabric_transport_port = (
        int(args.fabric_transport_port)
        if args.fabric_transport_port is not None
        else int(0 if raw_transport_port is None else raw_transport_port)
    )
    fabric_transport_connect = (
        bool(args.fabric_transport_connect)
        if args.fabric_transport_connect is not None
        else bool(runner_defaults.get("fabric_transport_connect", False))
    )
    fabric_transport_keep_open = (
        bool(args.fabric_transport_keep_open)
        if args.fabric_transport_keep_open is not None
        else bool(runner_defaults.get("fabric_transport_keep_open", False))
    )
    raw_transport_backpressure_max_pending = runner_defaults.get("fabric_transport_backpressure_max_pending")
    fabric_transport_backpressure_max_pending = (
        int(args.fabric_transport_backpressure_max_pending)
        if args.fabric_transport_backpressure_max_pending is not None
        else (
            None
            if raw_transport_backpressure_max_pending is None
            else int(raw_transport_backpressure_max_pending)
        )
    )
    fabric_transport_backpressure_policy = (
        str(args.fabric_transport_backpressure_policy)
        if args.fabric_transport_backpressure_policy is not None
        else str(runner_defaults.get("fabric_transport_backpressure_policy", "block"))
    )
    fabric_transport_backpressure_block_timeout_ms = (
        int(args.fabric_transport_backpressure_block_timeout_ms)
        if args.fabric_transport_backpressure_block_timeout_ms is not None
        else int(runner_defaults.get("fabric_transport_backpressure_block_timeout_ms", 200))
    )
    fabric_transport_dedup_ingress_enabled = (
        bool(args.fabric_transport_dedup_ingress_enabled)
        if args.fabric_transport_dedup_ingress_enabled is not None
        else bool(runner_defaults.get("fabric_transport_dedup_ingress_enabled", False))
    )
    fabric_transport_dedup_ttl_ms = (
        int(args.fabric_transport_dedup_ttl_ms)
        if args.fabric_transport_dedup_ttl_ms is not None
        else int(runner_defaults.get("fabric_transport_dedup_ttl_ms", 30000))
    )
    fabric_transport_dedup_max_entries = (
        int(args.fabric_transport_dedup_max_entries)
        if args.fabric_transport_dedup_max_entries is not None
        else int(runner_defaults.get("fabric_transport_dedup_max_entries", 10000))
    )
    fabric_transport_auth_enabled = (
        bool(args.fabric_transport_auth_enabled)
        if args.fabric_transport_auth_enabled is not None
        else bool(runner_defaults.get("fabric_transport_auth_enabled", False))
    )
    fabric_transport_auth_key = (
        str(args.fabric_transport_auth_key)
        if args.fabric_transport_auth_key is not None
        else (
            None
            if runner_defaults.get("fabric_transport_auth_key") is None
            else str(runner_defaults.get("fabric_transport_auth_key"))
        )
    )
    fabric_transport_auth_key_id = (
        str(args.fabric_transport_auth_key_id)
        if args.fabric_transport_auth_key_id is not None
        else (
            None
            if runner_defaults.get("fabric_transport_auth_key_id") is None
            else str(runner_defaults.get("fabric_transport_auth_key_id"))
        )
    )
    fabric_transport_tls_enabled = (
        bool(args.fabric_transport_tls_enabled)
        if args.fabric_transport_tls_enabled is not None
        else bool(runner_defaults.get("fabric_transport_tls_enabled", False))
    )
    fabric_transport_tls_server_hostname = (
        str(args.fabric_transport_tls_server_hostname)
        if args.fabric_transport_tls_server_hostname is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_server_hostname") is None
            else str(runner_defaults.get("fabric_transport_tls_server_hostname"))
        )
    )
    fabric_transport_tls_ca_file = (
        str(args.fabric_transport_tls_ca_file)
        if args.fabric_transport_tls_ca_file is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_ca_file") is None
            else str(runner_defaults.get("fabric_transport_tls_ca_file"))
        )
    )
    fabric_transport_tls_cert_file = (
        str(args.fabric_transport_tls_cert_file)
        if args.fabric_transport_tls_cert_file is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_cert_file") is None
            else str(runner_defaults.get("fabric_transport_tls_cert_file"))
        )
    )
    fabric_transport_tls_key_file = (
        str(args.fabric_transport_tls_key_file)
        if args.fabric_transport_tls_key_file is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_key_file") is None
            else str(runner_defaults.get("fabric_transport_tls_key_file"))
        )
    )
    fabric_transport_tls_require_client_cert = (
        bool(args.fabric_transport_tls_require_client_cert)
        if args.fabric_transport_tls_require_client_cert is not None
        else bool(runner_defaults.get("fabric_transport_tls_require_client_cert", False))
    )
    fabric_transport_tls_client_ca_file = (
        str(args.fabric_transport_tls_client_ca_file)
        if args.fabric_transport_tls_client_ca_file is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_client_ca_file") is None
            else str(runner_defaults.get("fabric_transport_tls_client_ca_file"))
        )
    )
    fabric_transport_tls_insecure_skip_verify = (
        bool(args.fabric_transport_tls_insecure_skip_verify)
        if args.fabric_transport_tls_insecure_skip_verify is not None
        else bool(runner_defaults.get("fabric_transport_tls_insecure_skip_verify", False))
    )
    fabric_transport_tls_identity_source = (
        str(args.fabric_transport_tls_identity_source)
        if args.fabric_transport_tls_identity_source is not None
        else str(runner_defaults.get("fabric_transport_tls_identity_source", "auto"))
    )
    fabric_transport_tls_identity_fallback_to_fingerprint = (
        bool(args.fabric_transport_tls_identity_fallback_to_fingerprint)
        if args.fabric_transport_tls_identity_fallback_to_fingerprint is not None
        else bool(runner_defaults.get("fabric_transport_tls_identity_fallback_to_fingerprint", False))
    )
    fabric_artifact_dir = (
        str(args.fabric_artifact_dir)
        if args.fabric_artifact_dir is not None
        else (
            None
            if runner_defaults.get("fabric_artifact_dir") is None
            else str(runner_defaults.get("fabric_artifact_dir"))
        )
    )
    fabric_inline_bridge = (
        bool(args.fabric_inline_bridge)
        if args.fabric_inline_bridge is not None
        else bool(runner_defaults.get("fabric_inline_bridge", True))
    )
    return {
        "fabric_transport": fabric_transport,
        "fabric_transport_host": fabric_transport_host,
        "fabric_transport_port": fabric_transport_port,
        "fabric_transport_connect": bool(fabric_transport_connect),
        "fabric_transport_keep_open": bool(fabric_transport_keep_open),
        "fabric_transport_backpressure_max_pending": fabric_transport_backpressure_max_pending,
        "fabric_transport_backpressure_policy": fabric_transport_backpressure_policy,
        "fabric_transport_backpressure_block_timeout_ms": fabric_transport_backpressure_block_timeout_ms,
        "fabric_transport_dedup_ingress_enabled": bool(fabric_transport_dedup_ingress_enabled),
        "fabric_transport_dedup_ttl_ms": fabric_transport_dedup_ttl_ms,
        "fabric_transport_dedup_max_entries": fabric_transport_dedup_max_entries,
        "fabric_transport_auth_enabled": bool(fabric_transport_auth_enabled),
        "fabric_transport_auth_key": fabric_transport_auth_key,
        "fabric_transport_auth_key_id": fabric_transport_auth_key_id,
        "fabric_transport_tls_enabled": bool(fabric_transport_tls_enabled),
        "fabric_transport_tls_server_hostname": fabric_transport_tls_server_hostname,
        "fabric_transport_tls_ca_file": fabric_transport_tls_ca_file,
        "fabric_transport_tls_cert_file": fabric_transport_tls_cert_file,
        "fabric_transport_tls_key_file": fabric_transport_tls_key_file,
        "fabric_transport_tls_require_client_cert": bool(fabric_transport_tls_require_client_cert),
        "fabric_transport_tls_client_ca_file": fabric_transport_tls_client_ca_file,
        "fabric_transport_tls_insecure_skip_verify": bool(fabric_transport_tls_insecure_skip_verify),
        "fabric_transport_tls_identity_source": fabric_transport_tls_identity_source,
        "fabric_transport_tls_identity_fallback_to_fingerprint": bool(
            fabric_transport_tls_identity_fallback_to_fingerprint
        ),
        "fabric_artifact_dir": fabric_artifact_dir,
        "fabric_inline_bridge": bool(fabric_inline_bridge),
    }


__all__ = ["resolve_transport_fabric_options"]
