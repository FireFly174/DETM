"""TCP client transport with local subscriptions and channel dispatch."""

from __future__ import annotations

import hashlib
import hmac
import json
import socket
import ssl
import threading
from collections import defaultdict
from dataclasses import dataclass, field

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric.tcp_transport.relay import TcpFabricRelay
from detm.runtime.fabric import FabricHandler
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
        self.auth_key = None if self.auth_key is None else str(self.auth_key)
        self.auth_key_id = None if self.auth_key_id is None else str(self.auth_key_id).strip() or None
        self.tls_server_hostname = (
            None if self.tls_server_hostname is None else str(self.tls_server_hostname).strip() or None
        )
        self.tls_ca_file = None if self.tls_ca_file is None else str(self.tls_ca_file).strip() or None
        self.tls_cert_file = None if self.tls_cert_file is None else str(self.tls_cert_file).strip() or None
        self.tls_key_file = None if self.tls_key_file is None else str(self.tls_key_file).strip() or None
        self.tls_client_ca_file = None if self.tls_client_ca_file is None else str(self.tls_client_ca_file).strip() or None
        self.tls_identity_source = self._normalize_tls_identity_source(self.tls_identity_source)
        if bool(self.auth_enabled) and not str(self.auth_key or ""):
            raise ValueError("auth_key must be non-empty when auth_enabled=true")
        self._dedup = EnvelopeIdempotencyCache(
            enabled=bool(self.dedup_ingress_enabled),
            ttl_ms=int(self.dedup_ttl_ms),
            max_entries=int(self.dedup_max_entries),
        )
        self._sock.settimeout(0.2)
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
        sock = socket.create_connection((str(host), int(port)), timeout=float(timeout_s))
        try:
            sock = cls._maybe_wrap_client_tls_socket(
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
        return cls(
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
            sock = cls._maybe_wrap_client_tls_socket(
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
        return cls(
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
        buf = b""
        while self._running:
            try:
                chunk = self._sock.recv(4096)
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
                if bool(self.auth_enabled) and not self._verify_auth_payload(payload):
                    continue
                try:
                    envelope = FabricEnvelope.from_dict(payload)
                except Exception:
                    continue
                if not self._dedup.allow(envelope):
                    continue
                self._dispatch(envelope)

    def _dispatch(self, envelope: FabricEnvelope) -> None:
        keys = [
            (envelope.channel, None),
            (envelope.channel, envelope.mode),
            ("*", None),
            ("*", envelope.mode),
        ]
        for key in keys:
            with self._lock:
                handlers = list(self._handlers.get(key, []))
            for handler in handlers:
                handler(envelope)

    def close(self) -> None:
        self._running = False
        try:
            self._sock.close()
        except OSError:
            pass
        if self._reader is not None:
            self._reader.join(timeout=0.5)
            self._reader = None
        if self._relay is not None and not self._keep_open:
            self._relay.stop()
            self._relay = None
        with self._lock:
            self._handlers.clear()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "enabled": True,
                "kind": "tcp",
                "address": {"host": str(self.address[0]), "port": int(self.address[1])},
                "subscription_count": int(sum(len(v) for v in self._handlers.values())),
                "dedup": self._dedup.snapshot(),
                "auth": {
                    "enabled": bool(self.auth_enabled),
                    "key_id": self.auth_key_id,
                    "verified_total": int(self._auth_verified_total),
                    "rejected_total": int(self._auth_rejected_total),
                    "missing_total": int(self._auth_missing_total),
                    "bad_key_id_total": int(self._auth_bad_key_id_total),
                },
                "tls": {
                    "enabled": bool(self.tls_enabled),
                    "server_hostname": self.tls_server_hostname,
                    "ca_file": self.tls_ca_file,
                    "cert_file": self.tls_cert_file,
                    "key_file": self.tls_key_file,
                    "require_client_cert": bool(self.tls_require_client_cert),
                    "client_ca_file": self.tls_client_ca_file,
                    "insecure_skip_verify": bool(self.tls_insecure_skip_verify),
                    "identity_source": self.tls_identity_source,
                    "identity_fallback_to_fingerprint": bool(self.tls_identity_fallback_to_fingerprint),
                },
            }

    def _attach_auth(self, payload: dict[str, object]) -> dict[str, object]:
        out = dict(payload)
        key_id = str(self.auth_key_id or "").strip()
        if key_id:
            out["auth_key_id"] = key_id
        out["auth_sig"] = self._compute_auth_sig(out)
        return out

    def _verify_auth_payload(self, payload: dict[str, object]) -> bool:
        raw_sig = str(payload.get("auth_sig", "")).strip()
        if not raw_sig:
            self._auth_missing_total += 1
            self._auth_rejected_total += 1
            return False
        expected_key_id = str(self.auth_key_id or "").strip()
        actual_key_id = str(payload.get("auth_key_id", "")).strip()
        if expected_key_id and actual_key_id and actual_key_id != expected_key_id:
            self._auth_bad_key_id_total += 1
            self._auth_rejected_total += 1
            return False
        expected_sig = self._compute_auth_sig(payload)
        ok = hmac.compare_digest(expected_sig, raw_sig)
        if ok:
            self._auth_verified_total += 1
            return True
        self._auth_rejected_total += 1
        return False

    def _compute_auth_sig(self, payload: dict[str, object]) -> str:
        key = str(self.auth_key or "").encode("utf-8")
        canonical = dict(payload)
        canonical.pop("auth_sig", None)
        # Relay can inject transport identity metadata after sender-side signing.
        canonical.pop("transport_identity", None)
        body = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(key, body, hashlib.sha256).hexdigest()

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

    @staticmethod
    def _normalize_tls_identity_source(raw: str | object) -> str:
        source = str(raw).strip().lower()
        if source not in {"auto", "cn", "san", "fingerprint"}:
            raise ValueError("tls_identity_source must be one of: auto|cn|san|fingerprint")
        return source


__all__ = ["TcpFabricTransport"]



