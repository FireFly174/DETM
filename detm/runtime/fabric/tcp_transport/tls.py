"""TLS helpers for TCP fabric transport."""

from __future__ import annotations

import socket
import ssl


def maybe_wrap_client_tls_socket(
    sock: socket.socket,
    *,
    host: str,
    tls_enabled: bool,
    tls_server_hostname: str | None,
    tls_ca_file: str | None,
    tls_cert_file: str | None,
    tls_key_file: str | None,
    tls_insecure_skip_verify: bool,
) -> socket.socket:
    if not bool(tls_enabled):
        return sock
    ca_file = None if tls_ca_file is None else str(tls_ca_file).strip() or None
    cert_file = None if tls_cert_file is None else str(tls_cert_file).strip() or None
    key_file = None if tls_key_file is None else str(tls_key_file).strip() or None
    server_hostname = (
        None if tls_server_hostname is None else str(tls_server_hostname).strip() or None
    ) or str(host).strip() or None
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
    if cert_file is not None:
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    if bool(tls_insecure_skip_verify):
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context.wrap_socket(sock, server_hostname=server_hostname)


def normalize_tls_identity_source(raw: str | object) -> str:
    source = str(raw).strip().lower()
    if source not in {"auto", "cn", "san", "fingerprint"}:
        raise ValueError("tls_identity_source must be one of: auto|cn|san|fingerprint")
    return source


__all__ = ["maybe_wrap_client_tls_socket", "normalize_tls_identity_source"]
