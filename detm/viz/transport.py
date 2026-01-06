"""Visualization transport abstraction.

Transports are pluggable "sinks" for visualization frames, similar to compute
backends (numpy/torch). The default transport is TCP to a local viz daemon.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from detm.viz.client import VizClient, VizDaemon, start_local_daemon


class VizTransport(Protocol):
    def send_state(self, *, state_blob: bytes, tick: int, signature: list[float] | None = None) -> None: ...

    def close(self) -> None: ...


@dataclass
class NullVizTransport:
    def send_state(self, *, state_blob: bytes, tick: int, signature: list[float] | None = None) -> None:
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

    def send_state(self, *, state_blob: bytes, tick: int, signature: list[float] | None = None) -> None:
        self._client.send_state(state_blob=state_blob, tick=int(tick), signature=signature)
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
        try:
            self._client.close()
        finally:
            if self._daemon is not None and not self._keep_open:
                self._daemon.terminate()


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
        if connect:
            if int(port) <= 0:
                raise ValueError("TCP viz connect requires a fixed --viz-port")
            return TcpVizTransport.connect(host, int(port))
        return TcpVizTransport.start_local(host=host, port=int(port), keep_open=keep_open)
    raise ValueError(f"Unknown viz transport: {transport}")


__all__ = ["NullVizTransport", "TcpVizTransport", "VizTransport", "open_viz_transport"]
