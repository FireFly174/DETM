"""TCP subscriber client for the headless viz daemon."""

from __future__ import annotations

import queue
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from detm_app.protocol import recv_msg, send_msg


@dataclass
class VizPacket:
    tick: int
    state_blob: bytes
    signature: Optional[list[float]] = None
    meta: Optional[Dict[str, Any]] = None


class TcpVizSubscriber:
    def __init__(self, host: str, port: int, *, timeout_s: float = 2.0) -> None:
        self.host = str(host)
        self.port = int(port)
        self._sock = socket.create_connection((self.host, self.port), timeout=timeout_s)
        self._sock.settimeout(1.0)
        self._queue: "queue.Queue[VizPacket]" = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

        self.recv_frames: int = 0
        self._recv_window_start: float = 0.0
        self._recv_window_count: int = 0
        self.recv_fps_ema: float = 0.0

        send_msg(self._sock, {"type": "subscribe"})
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass

    def poll_latest(self) -> Optional[VizPacket]:
        latest = None
        try:
            while True:
                latest = self._queue.get_nowait()
        except queue.Empty:
            return latest

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                msg = recv_msg(self._sock)
            except Exception:
                return
            if msg.get("type") != "state":
                continue
            pkt = VizPacket(
                tick=int(msg.get("tick", 0)),
                state_blob=msg.get("state_blob", b""),
                signature=msg.get("signature"),
                meta=msg.get("meta"),
            )
            try:
                self._queue.put_nowait(pkt)
            except Exception:
                pass

            self.recv_frames += 1
            now = time.perf_counter()
            if self._recv_window_start <= 0.0:
                self._recv_window_start = now
                self._recv_window_count = 0
            self._recv_window_count += 1
            dt = now - self._recv_window_start
            if dt >= 0.5:
                fps = float(self._recv_window_count) / max(1e-9, dt)
                self.recv_fps_ema = 0.85 * float(self.recv_fps_ema) + 0.15 * fps
                self._recv_window_start = now
                self._recv_window_count = 0


__all__ = ["TcpVizSubscriber", "VizPacket"]

