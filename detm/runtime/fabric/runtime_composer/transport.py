"""Transport builders for fabric runtime composition."""

from __future__ import annotations

from typing import Any, Callable

from detm.runtime.fabric import BACKPRESSURE_POLICIES, BufferedFabricTransport


def build_transport(*, rec: Any, open_transport_fn: Callable[..., Any]):
    transport = open_transport_fn(
        transport=str(rec.transport),
        host=str(rec.transport_host),
        port=int(rec.transport_port),
        connect=bool(rec.transport_connect),
        keep_open=bool(rec.transport_keep_open),
        dedup_ingress_enabled=bool(getattr(rec, "transport_dedup_ingress_enabled", False)),
        dedup_ttl_ms=int(getattr(rec, "transport_dedup_ttl_ms", 30_000)),
        dedup_max_entries=int(getattr(rec, "transport_dedup_max_entries", 10_000)),
        auth_enabled=bool(getattr(rec, "transport_auth_enabled", False)),
        auth_key=getattr(rec, "transport_auth_key", None),
        auth_key_id=getattr(rec, "transport_auth_key_id", None),
        tls_enabled=bool(getattr(rec, "transport_tls_enabled", False)),
        tls_server_hostname=getattr(rec, "transport_tls_server_hostname", None),
        tls_ca_file=getattr(rec, "transport_tls_ca_file", None),
        tls_cert_file=getattr(rec, "transport_tls_cert_file", None),
        tls_key_file=getattr(rec, "transport_tls_key_file", None),
        tls_require_client_cert=bool(getattr(rec, "transport_tls_require_client_cert", False)),
        tls_client_ca_file=getattr(rec, "transport_tls_client_ca_file", None),
        tls_insecure_skip_verify=bool(getattr(rec, "transport_tls_insecure_skip_verify", False)),
        tls_identity_source=getattr(rec, "transport_tls_identity_source", "auto"),
        tls_identity_fallback_to_fingerprint=bool(
            getattr(rec, "transport_tls_identity_fallback_to_fingerprint", False)
        ),
    )
    if rec.transport_backpressure_max_pending is not None:
        transport = BufferedFabricTransport(
            base=transport,
            max_pending=int(rec.transport_backpressure_max_pending),
            policy=(
                str(rec.transport_backpressure_policy).strip().lower()
                if str(rec.transport_backpressure_policy).strip().lower() in BACKPRESSURE_POLICIES
                else "block"
            ),
            block_timeout_ms=int(rec.transport_backpressure_block_timeout_ms),
            close_base_on_close=True,
        )
    return transport


__all__ = ["build_transport"]
