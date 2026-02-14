"""TCP relay backend for fabric envelope broadcast."""

from __future__ import annotations

import hashlib
import json
import socket
import ssl
import threading

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (network adapter class exists)
# - OOP_TECH_DEBT: backpressure, durable message queue, mTLS hardening


class TcpFabricRelay:
    """Lightweight broadcast relay used by TCP fabric transports."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        *,
        tls_enabled: bool = False,
        tls_cert_file: str | None = None,
        tls_key_file: str | None = None,
        tls_require_client_cert: bool = False,
        tls_client_ca_file: str | None = None,
        tls_identity_source: str = "auto",
        tls_identity_fallback_to_fingerprint: bool = False,
    ) -> None:
        self._host = str(host)
        self._port = int(port)
        self._tls_enabled = bool(tls_enabled)
        self._tls_cert_file = None if tls_cert_file is None else str(tls_cert_file).strip() or None
        self._tls_key_file = None if tls_key_file is None else str(tls_key_file).strip() or None
        self._tls_require_client_cert = bool(tls_require_client_cert)
        self._tls_client_ca_file = None if tls_client_ca_file is None else str(tls_client_ca_file).strip() or None
        self._tls_identity_source = self._normalize_tls_identity_source(tls_identity_source)
        self._tls_identity_fallback_to_fingerprint = bool(tls_identity_fallback_to_fingerprint)
        self._server: socket.socket | None = None
        self._ssl_context: ssl.SSLContext | None = None
        self._running = False
        self._accept_thread: threading.Thread | None = None
        self._clients: set[socket.socket] = set()
        self._lock = threading.RLock()

    @property
    def address(self) -> tuple[str, int]:
        if self._server is None:
            return self._host, self._port
        host, port = self._server.getsockname()
        return str(host), int(port)

    def start(self) -> None:
        if self._running:
            return
        if self._tls_enabled and (self._tls_cert_file is None or self._tls_key_file is None):
            raise ValueError("tls_cert_file and tls_key_file are required when tls_enabled=true")
        if self._tls_enabled and self._tls_require_client_cert and self._tls_client_ca_file is None:
            raise ValueError("tls_client_ca_file is required when tls_require_client_cert=true")
        self._ssl_context = None
        if self._tls_enabled:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certfile=self._tls_cert_file, keyfile=self._tls_key_file)
            if self._tls_require_client_cert:
                context.verify_mode = ssl.CERT_REQUIRED
                context.load_verify_locations(cafile=self._tls_client_ca_file)
            self._ssl_context = context
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self._host, self._port))
        server.listen(8)
        server.settimeout(0.2)
        self._server = server
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, name="fabric-relay-accept", daemon=True)
        self._accept_thread.start()

    def _accept_loop(self) -> None:
        assert self._server is not None
        while self._running:
            try:
                conn, _addr = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            if self._ssl_context is not None:
                try:
                    conn = self._ssl_context.wrap_socket(conn, server_side=True)
                except ssl.SSLError:
                    try:
                        conn.close()
                    except OSError:
                        pass
                    continue
            conn.settimeout(0.2)
            with self._lock:
                self._clients.add(conn)
            transport_identity = self._extract_transport_identity(
                conn,
                source=self._tls_identity_source,
                allow_fingerprint_fallback=self._tls_identity_fallback_to_fingerprint,
            )
            threading.Thread(
                target=self._client_loop,
                args=(conn, transport_identity),
                name="fabric-relay-client",
                daemon=True,
            ).start()

    def _client_loop(self, conn: socket.socket, transport_identity: str | None) -> None:
        buf = b""
        try:
            while self._running:
                try:
                    chunk = conn.recv(4096)
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
                    payload = self._inject_transport_identity(raw, transport_identity)
                    self._broadcast(payload + b"\n")
        finally:
            with self._lock:
                self._clients.discard(conn)
            try:
                conn.close()
            except OSError:
                pass

    def _broadcast(self, payload: bytes) -> None:
        with self._lock:
            clients = list(self._clients)
        stale: list[socket.socket] = []
        for conn in clients:
            try:
                conn.sendall(payload)
            except OSError:
                stale.append(conn)
        if stale:
            with self._lock:
                for conn in stale:
                    self._clients.discard(conn)
                    try:
                        conn.close()
                    except OSError:
                        pass

    def stop(self) -> None:
        self._running = False
        server = self._server
        self._server = None
        self._ssl_context = None
        if server is not None:
            try:
                server.close()
            except OSError:
                pass
        with self._lock:
            clients = list(self._clients)
            self._clients.clear()
        for conn in clients:
            try:
                conn.close()
            except OSError:
                pass
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=0.5)
            self._accept_thread = None

    @staticmethod
    def _inject_transport_identity(payload_line: bytes, transport_identity: str | None) -> bytes:
        if transport_identity is None:
            return payload_line
        try:
            decoded = json.loads(payload_line.decode("utf-8"))
        except Exception:
            return payload_line
        if not isinstance(decoded, dict):
            return payload_line
        out = dict(decoded)
        out["transport_identity"] = str(transport_identity)
        return json.dumps(out, ensure_ascii=False).encode("utf-8")

    @classmethod
    def _extract_transport_identity(
        cls,
        conn: socket.socket,
        *,
        source: str = "auto",
        allow_fingerprint_fallback: bool = False,
    ) -> str | None:
        if not isinstance(conn, ssl.SSLSocket):
            return None
        cert = None
        cert_bin = None
        try:
            cert = conn.getpeercert()
        except Exception:
            cert = None
        try:
            cert_bin = conn.getpeercert(binary_form=True)
        except Exception:
            cert_bin = None
        return cls._select_transport_identity(
            cert=cert if isinstance(cert, dict) else None,
            cert_bin=cert_bin,
            source=source,
            allow_fingerprint_fallback=allow_fingerprint_fallback,
        )

    @classmethod
    def _select_transport_identity(
        cls,
        *,
        cert: dict[str, object] | None,
        cert_bin: bytes | None,
        source: str,
        allow_fingerprint_fallback: bool,
    ) -> str | None:
        source_name = cls._normalize_tls_identity_source(source)
        cn = cls._extract_cn_identity(cert)
        san = cls._extract_san_identity(cert)
        fingerprint = cls._extract_fingerprint_identity(cert_bin)

        if source_name == "auto":
            return cn or san or fingerprint
        if source_name == "cn":
            return cn or (fingerprint if allow_fingerprint_fallback else None)
        if source_name == "san":
            return san or (fingerprint if allow_fingerprint_fallback else None)
        if source_name == "fingerprint":
            return fingerprint
        return None

    @staticmethod
    def _extract_cn_identity(cert: dict[str, object] | None) -> str | None:
        if not isinstance(cert, dict):
            return None
        subject = cert.get("subject", ())
        for rdn in subject:
            for item in rdn:
                if len(item) == 2 and str(item[0]).strip().lower() == "commonname":
                    value = str(item[1]).strip()
                    if value:
                        return f"cn:{value}"
        return None

    @staticmethod
    def _extract_san_identity(cert: dict[str, object] | None) -> str | None:
        if not isinstance(cert, dict):
            return None
        sans = cert.get("subjectAltName", ())
        for row in sans:
            if isinstance(row, tuple) and len(row) == 2:
                kind = str(row[0]).strip().lower()
                value = str(row[1]).strip()
                if kind and value:
                    return f"{kind}:{value}"
        return None

    @staticmethod
    def _extract_fingerprint_identity(cert_bin: bytes | None) -> str | None:
        if cert_bin:
            return "sha256:" + hashlib.sha256(cert_bin).hexdigest()
        return None

    @staticmethod
    def _normalize_tls_identity_source(raw: str | object) -> str:
        source = str(raw).strip().lower()
        if source not in {"auto", "cn", "san", "fingerprint"}:
            raise ValueError("tls_identity_source must be one of: auto|cn|san|fingerprint")
        return source


__all__ = ["TcpFabricRelay"]
