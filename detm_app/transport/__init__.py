"""Visualization transport abstraction.

Transports are pluggable "sinks" for visualization frames, similar to compute
backends (numpy/torch). The default transport is TCP to a local viz daemon.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from detm_app.transport.client import VizClient, VizDaemon, start_local_daemon


class VizTransport(Protocol):
    def send_state(
        self,
        *,
        state_blob: bytes,
        tick: int,
        signature: list[float] | None = None,
        meta: dict[str, object] | None = None,
    ) -> None: ...

    def close(self) -> None: ...


@dataclass
class NullVizTransport:
    def send_state(
        self,
        *,
        state_blob: bytes,
        tick: int,
        signature: list[float] | None = None,
        meta: dict[str, object] | None = None,
    ) -> None:
        return

    def close(self) -> None:
        return


class TcpVizTransport:
    def __init__(
        self,
        client: VizClient,
        *,
        daemon: VizDaemon | None = None,
        keep_open: bool = False,
    ) -> None:
        self._client = client
        self._daemon = daemon
        self._keep_open = bool(keep_open)
        self.sent_frames: int = 0
        self._sent_window_start: float = 0.0
        self._sent_window_count: int = 0
        self.sent_fps_ema: float = 0.0

    @classmethod
    def connect(cls, host: str, port: int, *, timeout_s: float = 2.0) -> "TcpVizTransport":
        return cls(VizClient(host, int(port), timeout_s=timeout_s))

    @classmethod
    def start_local(
        cls,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        keep_open: bool = False,
    ) -> "TcpVizTransport":
        daemon = start_local_daemon(host=host, port=int(port))
        client = daemon.connect()
        return cls(client, daemon=daemon, keep_open=keep_open)

    def send_state(
        self,
        *,
        state_blob: bytes,
        tick: int,
        signature: list[float] | None = None,
        meta: dict[str, object] | None = None,
    ) -> None:
        self._client.send_state(state_blob=state_blob, tick=int(tick), signature=signature, meta=meta)
        self.sent_frames += 1
        now = __import__("time").perf_counter()
        if self._sent_window_start <= 0.0:
            self._sent_window_start = now
            self._sent_window_count = 0
        self._sent_window_count += 1
        dt = now - self._sent_window_start
        if dt >= 0.5:
            fps = float(self._sent_window_count) / max(1e-9, dt)
            self.sent_fps_ema = 0.85 * float(self.sent_fps_ema) + 0.15 * fps
            self._sent_window_start = now
            self._sent_window_count = 0

    @property
    def address(self) -> tuple[str, int]:
        return str(self._client.host), int(self._client.port)

    def close(self) -> None:
        endpoint_host = ""
        endpoint_port = 0
        try:
            endpoint_host, endpoint_port = self.address
        except Exception:
            endpoint_host, endpoint_port = "", 0
        try:
            self._client.close()
        finally:
            if self._daemon is not None and not self._keep_open:
                try:
                    self._daemon.terminate()
                finally:
                    clear_viz_endpoint_registry(host=endpoint_host, port=endpoint_port)
        self._daemon = None


def _endpoint_registry_path() -> Path:
    raw = str(os.environ.get("DETM_VIZ_ENDPOINT_PATH", "")).strip()
    if raw:
        return Path(raw)
    return Path("runs") / "viz_endpoint.json"


def write_viz_endpoint_registry(*, host: str, port: int) -> None:
    """Best-effort write of current viz endpoint for external read-only subscribers."""
    if int(port) <= 0:
        return
    payload = {
        "host": str(host),
        "port": int(port),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    path = _endpoint_registry_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Endpoint registry is advisory metadata; producer must continue even if write fails.
        return


def load_viz_endpoint_registry() -> tuple[str, int] | None:
    path = _endpoint_registry_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    host = str(payload.get("host", "")).strip()
    try:
        port = int(payload.get("port", 0))
    except Exception:
        return None
    if not host or port <= 0:
        return None
    return host, port


def clear_viz_endpoint_registry(*, host: str, port: int) -> None:
    """Best-effort clear of endpoint registry when it still points to host/port."""
    path = _endpoint_registry_path()
    if not path.exists():
        return
    if not host or int(port) <= 0:
        return
    current = load_viz_endpoint_registry()
    if current is None:
        return
    if current != (str(host), int(port)):
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        return


def open_viz_transport(
    *,
    enabled: bool,
    transport: str = "tcp",
    host: str = "127.0.0.1",
    port: int = 0,
    connect: bool = False,
    keep_open: bool = False,
) -> VizTransport:
    if not enabled:
        return NullVizTransport()
    name = str(transport).strip().lower()
    if name in {"none", "null", "off"}:
        return NullVizTransport()
    if name == "tcp":
        transport_obj: TcpVizTransport
        if connect:
            if int(port) <= 0:
                raise ValueError("TCP viz connect requires a fixed --viz-port")
            transport_obj = TcpVizTransport.connect(host, int(port))
        else:
            transport_obj = TcpVizTransport.start_local(host=host, port=int(port), keep_open=keep_open)
        endpoint_host, endpoint_port = transport_obj.address
        write_viz_endpoint_registry(host=endpoint_host, port=endpoint_port)
        return transport_obj
    raise ValueError(f"Unknown viz transport: {transport}")


__all__ = [
    "clear_viz_endpoint_registry",
    "NullVizTransport",
    "TcpVizTransport",
    "VizTransport",
    "load_viz_endpoint_registry",
    "open_viz_transport",
    "write_viz_endpoint_registry",
]
