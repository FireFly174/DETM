"""TCP client transport with local subscriptions and channel dispatch."""

from __future__ import annotations

import json
import socket
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import FabricHandler
from detm.runtime.fabric.tcp_transport.auth import (
    attach_auth_payload,
    compute_auth_sig,
    verify_auth_payload,
)
from detm.runtime.fabric.tcp_transport.flow import (
    close_transport,
    connect_tcp_socket,
    dispatch_envelope,
    normalize_transport_config,
    run_read_loop,
    snapshot_transport,
    start_local_relay_and_socket,
)
from detm.runtime.fabric.tcp_transport.relay import TcpFabricRelay
from detm.runtime.fabric.tcp_transport.tls import (
    maybe_wrap_client_tls_socket,
    normalize_tls_identity_source,
)
from detm.runtime.fabric.transport.idempotency import EnvelopeIdempotencyCache


@dataclass
class TcpFabricTransport:
    """TCP client transport with local subscriptions and channel dispatch."""

    _sock: socket.socket
    _relay: TcpFabricRelay | None = None
    _keep_open: bool = False
    dedup_ingress_enabled: bool = False
    dedup_ttl_ms: int = 30_000
    dedup_max_entries: int = 10_000
    auth_enabled: bool = False
    auth_key: str | None = None
    auth_key_id: str | None = None
    tls_enabled: bool = False
    tls_server_hostname: str | None = None
    tls_ca_file: str | None = None
    tls_cert_file: str | None = None
    tls_key_file: str | None = None
    tls_require_client_cert: bool = False
    tls_client_ca_file: str | None = None
    tls_insecure_skip_verify: bool = False
    tls_identity_source: str = "auto"
    tls_identity_fallback_to_fingerprint: bool = False
    _running: bool = True
    _reader: threading.Thread | None = None
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _handlers: dict[tuple[str, str | None], list[FabricHandler]] = None  # type: ignore[assignment]
    _dedup: EnvelopeIdempotencyCache = field(init=False)
    _auth_verified_total: int = 0
    _auth_rejected_total: int = 0
    _auth_missing_total: int = 0
    _auth_bad_key_id_total: int = 0

    def __post_init__(self) -> None:
        self._handlers = defaultdict(list)
        normalize_transport_config(self)
        self.tls_identity_source = self._normalize_tls_identity_source(self.tls_identity_source)
        self._dedup = EnvelopeIdempotencyCache(
            enabled=bool(self.dedup_ingress_enabled),
            ttl_ms=int(self.dedup_ttl_ms),
            max_entries=int(self.dedup_max_entries),
        )
        self._reader = threading.Thread(target=self._read_loop, name="fabric-tcp-reader", daemon=True)
        self._reader.start()

    @classmethod
    def connect(
        cls,
        host: str,
        port: int,
        *,
        timeout_s: float = 2.0,
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
    ) -> "TcpFabricTransport":
        sock = connect_tcp_socket(
            host=str(host),
            port=int(port),
            timeout_s=float(timeout_s),
            tls_enabled=bool(tls_enabled),
            tls_server_hostname=tls_server_hostname,
            tls_ca_file=tls_ca_file,
            tls_cert_file=tls_cert_file,
            tls_key_file=tls_key_file,
            tls_insecure_skip_verify=bool(tls_insecure_skip_verify),
        )
        transport = cls(
            sock,
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
        transport._await_relay_registration()
        return transport

    @classmethod
    def start_local(
        cls,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        keep_open: bool = False,
        timeout_s: float = 2.0,
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
    ) -> "TcpFabricTransport":
        sock, relay = start_local_relay_and_socket(
            host=str(host),
            port=int(port),
            timeout_s=float(timeout_s),
            tls_enabled=bool(tls_enabled),
            tls_server_hostname=tls_server_hostname,
            tls_ca_file=tls_ca_file,
            tls_cert_file=tls_cert_file,
            tls_key_file=tls_key_file,
            tls_require_client_cert=bool(tls_require_client_cert),
            tls_client_ca_file=tls_client_ca_file,
            tls_insecure_skip_verify=bool(tls_insecure_skip_verify),
            tls_identity_source=str(tls_identity_source),
            tls_identity_fallback_to_fingerprint=bool(tls_identity_fallback_to_fingerprint),
        )
        transport = cls(
            sock,
            _relay=relay,
            _keep_open=bool(keep_open),
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
        transport._await_relay_registration()
        return transport

    @property
    def address(self) -> tuple[str, int]:
        if self._relay is not None:
            return self._relay.address
        host, port = self._sock.getpeername()
        return str(host), int(port)

    def subscribe(self, channel: str, handler: FabricHandler, *, mode: str | None = None) -> None:
        key = (str(channel), None if mode is None else str(mode).strip().lower())
        with self._lock:
            self._handlers[key].append(handler)

    def unsubscribe(self, channel: str, handler: FabricHandler, *, mode: str | None = None) -> bool:
        key = (str(channel), None if mode is None else str(mode).strip().lower())
        with self._lock:
            handlers = self._handlers.get(key)
            if not handlers:
                return False
            for idx, existing in enumerate(list(handlers)):
                if existing is handler:
                    del handlers[idx]
                    if not handlers:
                        self._handlers.pop(key, None)
                    return True
        return False

    def publish(self, envelope: FabricEnvelope) -> int:
        envelope.validate()
        payload_obj = envelope.to_dict()
        if bool(self.auth_enabled):
            payload_obj = self._attach_auth(payload_obj)
        payload = json.dumps(payload_obj, ensure_ascii=False) + "\n"
        self._sock.sendall(payload.encode("utf-8"))
        return 1

    def _read_loop(self) -> None:
        run_read_loop(self)

    def _dispatch(self, envelope: FabricEnvelope) -> None:
        dispatch_envelope(self, envelope)

    def close(self) -> None:
        close_transport(self)

    def snapshot(self) -> dict[str, object]:
        return snapshot_transport(self)

    def _attach_auth(self, payload: dict[str, object]) -> dict[str, object]:
        return attach_auth_payload(self, payload)

    def _verify_auth_payload(self, payload: dict[str, object]) -> bool:
        return verify_auth_payload(self, payload)

    def _compute_auth_sig(self, payload: dict[str, object]) -> str:
        return compute_auth_sig(auth_key=self.auth_key, payload=payload)

    def _await_relay_registration(self, *, timeout_s: float = 0.3) -> None:
        """Best-effort local readiness handshake to reduce first-message races."""
        channel = "__fabric.transport.ready__"
        marker = f"transport://ready/{id(self)}:{time.perf_counter_ns()}"
        ready = threading.Event()

        def _on_ready(envelope: FabricEnvelope) -> None:
            if str(envelope.payload_ref) == marker:
                ready.set()

        self.subscribe(channel, _on_ready, mode="realtime")
        try:
            self.publish(
                FabricEnvelope.from_dict(
                    {
                        "message_type": "transport_ready",
                        "channel": channel,
                        "mode": "realtime",
                        "sender": "tcp-transport",
                        "payload_ref": marker,
                    }
                )
            )
            ready.wait(timeout=max(float(timeout_s), 0.0))
        except Exception:
            # Ready handshake is best-effort and must not break connect semantics.
            pass
        finally:
            self.unsubscribe(channel, _on_ready, mode="realtime")

    @staticmethod
    def _maybe_wrap_client_tls_socket(
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
        return maybe_wrap_client_tls_socket(
            sock,
            host=host,
            tls_enabled=bool(tls_enabled),
            tls_server_hostname=tls_server_hostname,
            tls_ca_file=tls_ca_file,
            tls_cert_file=tls_cert_file,
            tls_key_file=tls_key_file,
            tls_insecure_skip_verify=bool(tls_insecure_skip_verify),
        )

    @staticmethod
    def _normalize_tls_identity_source(raw: str | object) -> str:
        return normalize_tls_identity_source(raw)


__all__ = ["TcpFabricTransport"]



