"""TCP relay transport adapter for fabric envelopes."""

from __future__ import annotations

import json
import socket
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_transport import FabricHandler, FabricTransportAdapter

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (network adapter class exists)
# - OOP_TECH_DEBT: auth, encryption, backpressure, durable message queue


class TcpFabricRelay:
    """Lightweight broadcast relay used by TCP fabric transports."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = str(host)
        self._port = int(port)
        self._server: socket.socket | None = None
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
            conn.settimeout(0.2)
            with self._lock:
                self._clients.add(conn)
            threading.Thread(
                target=self._client_loop,
                args=(conn,),
                name="fabric-relay-client",
                daemon=True,
            ).start()

    def _client_loop(self, conn: socket.socket) -> None:
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
                    self._broadcast(raw + b"\n")
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


@dataclass
class TcpFabricTransport:
    """TCP client transport with local subscriptions and channel dispatch."""

    _sock: socket.socket
    _relay: TcpFabricRelay | None = None
    _keep_open: bool = False
    _running: bool = True
    _reader: threading.Thread | None = None
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _handlers: Dict[tuple[str, str | None], List[FabricHandler]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._handlers = defaultdict(list)
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
    ) -> "TcpFabricTransport":
        sock = socket.create_connection((str(host), int(port)), timeout=float(timeout_s))
        return cls(sock)

    @classmethod
    def start_local(
        cls,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        keep_open: bool = False,
        timeout_s: float = 2.0,
    ) -> "TcpFabricTransport":
        relay = TcpFabricRelay(host=host, port=int(port))
        relay.start()
        r_host, r_port = relay.address
        sock = socket.create_connection((r_host, int(r_port)), timeout=float(timeout_s))
        return cls(sock, _relay=relay, _keep_open=bool(keep_open))

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
        payload = json.dumps(envelope.to_dict(), ensure_ascii=False) + "\n"
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
                try:
                    envelope = FabricEnvelope.from_dict(payload)
                except Exception:
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


def open_fabric_transport(
    *,
    transport: str = "memory",
    host: str = "127.0.0.1",
    port: int = 0,
    connect: bool = False,
    keep_open: bool = False,
) -> FabricTransportAdapter:
    name = str(transport).strip().lower()
    if name in {"memory", "inmemory", "local"}:
        from detm.runtime.fabric_transport import InMemoryFabricBus

        return InMemoryFabricBus()
    if name == "tcp":
        if connect:
            if int(port) <= 0:
                raise ValueError("TCP fabric connect requires fixed port > 0")
            return TcpFabricTransport.connect(host=host, port=int(port))
        return TcpFabricTransport.start_local(host=host, port=int(port), keep_open=keep_open)
    raise ValueError(f"Unknown fabric transport: {transport}")


__all__ = ["TcpFabricRelay", "TcpFabricTransport", "open_fabric_transport"]
