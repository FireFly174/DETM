"""Factory for fabric transport adapters."""

from __future__ import annotations

from detm.runtime.fabric.tcp_transport.transport import TcpFabricTransport
from detm.runtime.fabric import FabricTransportAdapter


def open_fabric_transport(
    *,
    transport: str = "memory",
    host: str = "127.0.0.1",
    port: int = 0,
    connect: bool = False,
    keep_open: bool = False,
    dedup_ingress_enabled: bool = False,
    dedup_ttl_ms: int = 30_000,
    dedup_max_entries: int = 10_000,
    auth_enabled: bool = False,
    auth_key: str | None = None,
    auth_key_id: str | None = None,
    tls_enabled: bool = False,
    tls_server_hostname: str | None = None,
    tls_ca_file: str | None = None,
    tls_cert_file: str | None = None,
    tls_key_file: str | None = None,
    tls_require_client_cert: bool = False,
    tls_client_ca_file: str | None = None,
    tls_insecure_skip_verify: bool = False,
    tls_identity_source: str = "auto",
    tls_identity_fallback_to_fingerprint: bool = False,
) -> FabricTransportAdapter:
    name = str(transport).strip().lower()
    if name in {"memory", "inmemory", "local"}:
        from detm.runtime.fabric import InMemoryFabricBus

        return InMemoryFabricBus(
            dedup_ingress_enabled=bool(dedup_ingress_enabled),
            dedup_ttl_ms=int(dedup_ttl_ms),
            dedup_max_entries=int(dedup_max_entries),
        )
    if name == "tcp":
        if connect:
            if int(port) <= 0:
                raise ValueError("TCP fabric connect requires fixed port > 0")
            return TcpFabricTransport.connect(
                host=host,
                port=int(port),
                dedup_ingress_enabled=bool(dedup_ingress_enabled),
                dedup_ttl_ms=int(dedup_ttl_ms),
                dedup_max_entries=int(dedup_max_entries),
                auth_enabled=bool(auth_enabled),
                auth_key=auth_key,
                auth_key_id=auth_key_id,
                tls_enabled=bool(tls_enabled),
                tls_server_hostname=tls_server_hostname,
                tls_ca_file=tls_ca_file,
                tls_cert_file=tls_cert_file,
                tls_key_file=tls_key_file,
                tls_require_client_cert=bool(tls_require_client_cert),
                tls_client_ca_file=tls_client_ca_file,
                tls_insecure_skip_verify=bool(tls_insecure_skip_verify),
                tls_identity_source=tls_identity_source,
                tls_identity_fallback_to_fingerprint=bool(tls_identity_fallback_to_fingerprint),
            )
        return TcpFabricTransport.start_local(
            host=host,
            port=int(port),
            keep_open=keep_open,
            dedup_ingress_enabled=bool(dedup_ingress_enabled),
            dedup_ttl_ms=int(dedup_ttl_ms),
            dedup_max_entries=int(dedup_max_entries),
            auth_enabled=bool(auth_enabled),
            auth_key=auth_key,
            auth_key_id=auth_key_id,
            tls_enabled=bool(tls_enabled),
            tls_server_hostname=tls_server_hostname,
            tls_ca_file=tls_ca_file,
            tls_cert_file=tls_cert_file,
            tls_key_file=tls_key_file,
            tls_require_client_cert=bool(tls_require_client_cert),
            tls_client_ca_file=tls_client_ca_file,
            tls_insecure_skip_verify=bool(tls_insecure_skip_verify),
            tls_identity_source=tls_identity_source,
            tls_identity_fallback_to_fingerprint=bool(tls_identity_fallback_to_fingerprint),
        )
    raise ValueError(f"Unknown fabric transport: {transport}")


__all__ = ["open_fabric_transport"]



