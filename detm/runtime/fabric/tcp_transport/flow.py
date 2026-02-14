"""Execution helpers for TCP fabric transport."""

from __future__ import annotations

import json
import socket
from typing import Any

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric.tcp_transport.relay import TcpFabricRelay
from detm.runtime.fabric.tcp_transport.tls import maybe_wrap_client_tls_socket


def normalize_transport_config(transport: Any) -> None:
    transport.auth_key = None if transport.auth_key is None else str(transport.auth_key)
    transport.auth_key_id = None if transport.auth_key_id is None else str(transport.auth_key_id).strip() or None
    transport.tls_server_hostname = (
        None if transport.tls_server_hostname is None else str(transport.tls_server_hostname).strip() or None
    )
    transport.tls_ca_file = None if transport.tls_ca_file is None else str(transport.tls_ca_file).strip() or None
    transport.tls_cert_file = None if transport.tls_cert_file is None else str(transport.tls_cert_file).strip() or None
    transport.tls_key_file = None if transport.tls_key_file is None else str(transport.tls_key_file).strip() or None
    transport.tls_client_ca_file = (
        None if transport.tls_client_ca_file is None else str(transport.tls_client_ca_file).strip() or None
    )
    if bool(transport.auth_enabled) and not str(transport.auth_key or ""):
        raise ValueError("auth_key must be non-empty when auth_enabled=true")
    transport._sock.settimeout(0.2)


def connect_tcp_socket(
    *,
    host: str,
    port: int,
    timeout_s: float,
    tls_enabled: bool,
    tls_server_hostname: str | None,
    tls_ca_file: str | None,
    tls_cert_file: str | None,
    tls_key_file: str | None,
    tls_insecure_skip_verify: bool,
) -> socket.socket:
    sock = socket.create_connection((str(host), int(port)), timeout=float(timeout_s))
    try:
        sock = maybe_wrap_client_tls_socket(
            sock,
            host=str(host),
            tls_enabled=bool(tls_enabled),
            tls_server_hostname=tls_server_hostname,
            tls_ca_file=tls_ca_file,
            tls_cert_file=tls_cert_file,
            tls_key_file=tls_key_file,
            tls_insecure_skip_verify=bool(tls_insecure_skip_verify),
        )
    except Exception:
        try:
            sock.close()
        except OSError:
            pass
        raise
    return sock


def start_local_relay_and_socket(
    *,
    host: str,
    port: int,
    timeout_s: float,
    tls_enabled: bool,
    tls_server_hostname: str | None,
    tls_ca_file: str | None,
    tls_cert_file: str | None,
    tls_key_file: str | None,
    tls_require_client_cert: bool,
    tls_client_ca_file: str | None,
    tls_insecure_skip_verify: bool,
    tls_identity_source: str,
    tls_identity_fallback_to_fingerprint: bool,
) -> tuple[socket.socket, TcpFabricRelay]:
    relay = TcpFabricRelay(
        host=host,
        port=int(port),
        tls_enabled=bool(tls_enabled),
        tls_cert_file=tls_cert_file,
        tls_key_file=tls_key_file,
        tls_require_client_cert=bool(tls_require_client_cert),
        tls_client_ca_file=tls_client_ca_file,
        tls_identity_source=tls_identity_source,
        tls_identity_fallback_to_fingerprint=bool(tls_identity_fallback_to_fingerprint),
    )
    relay.start()
    r_host, r_port = relay.address
    sock = socket.create_connection((r_host, int(r_port)), timeout=float(timeout_s))
    try:
        sock = maybe_wrap_client_tls_socket(
            sock,
            host=str(r_host),
            tls_enabled=bool(tls_enabled),
            tls_server_hostname=tls_server_hostname,
            tls_ca_file=tls_ca_file,
            tls_cert_file=tls_cert_file,
            tls_key_file=tls_key_file,
            tls_insecure_skip_verify=bool(tls_insecure_skip_verify),
        )
    except Exception:
        relay.stop()
        try:
            sock.close()
        except OSError:
            pass
        raise
    return sock, relay


def run_read_loop(transport: Any) -> None:
    buf = b""
    while transport._running:
        try:
            chunk = transport._sock.recv(4096)
        except TimeoutError:
            continue
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            if bool(transport.auth_enabled) and not transport._verify_auth_payload(payload):
                continue
            try:
                envelope = FabricEnvelope.from_dict(payload)
            except Exception:
                continue
            if not transport._dedup.allow(envelope):
                continue
            dispatch_envelope(transport, envelope)


def dispatch_envelope(transport: Any, envelope: FabricEnvelope) -> None:
    keys = [
        (envelope.channel, None),
        (envelope.channel, envelope.mode),
        ("*", None),
        ("*", envelope.mode),
    ]
    for key in keys:
        with transport._lock:
            handlers = list(transport._handlers.get(key, []))
        for handler in handlers:
            handler(envelope)


def close_transport(transport: Any) -> None:
    transport._running = False
    try:
        transport._sock.close()
    except OSError:
        pass
    if transport._reader is not None:
        transport._reader.join(timeout=0.5)
        transport._reader = None
    if transport._relay is not None and not transport._keep_open:
        transport._relay.stop()
        transport._relay = None
    with transport._lock:
        transport._handlers.clear()


def snapshot_transport(transport: Any) -> dict[str, object]:
    with transport._lock:
        return {
            "enabled": True,
            "kind": "tcp",
            "address": {"host": str(transport.address[0]), "port": int(transport.address[1])},
            "subscription_count": int(sum(len(v) for v in transport._handlers.values())),
            "dedup": transport._dedup.snapshot(),
            "auth": {
                "enabled": bool(transport.auth_enabled),
                "key_id": transport.auth_key_id,
                "verified_total": int(transport._auth_verified_total),
                "rejected_total": int(transport._auth_rejected_total),
                "missing_total": int(transport._auth_missing_total),
                "bad_key_id_total": int(transport._auth_bad_key_id_total),
            },
            "tls": {
                "enabled": bool(transport.tls_enabled),
                "server_hostname": transport.tls_server_hostname,
                "ca_file": transport.tls_ca_file,
                "cert_file": transport.tls_cert_file,
                "key_file": transport.tls_key_file,
                "require_client_cert": bool(transport.tls_require_client_cert),
                "client_ca_file": transport.tls_client_ca_file,
                "insecure_skip_verify": bool(transport.tls_insecure_skip_verify),
                "identity_source": transport.tls_identity_source,
                "identity_fallback_to_fingerprint": bool(transport.tls_identity_fallback_to_fingerprint),
            },
        }


__all__ = [
    "close_transport",
    "connect_tcp_socket",
    "dispatch_envelope",
    "normalize_transport_config",
    "run_read_loop",
    "snapshot_transport",
    "start_local_relay_and_socket",
]
