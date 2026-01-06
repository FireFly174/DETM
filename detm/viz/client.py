"""Client for sending state updates to the viz daemon."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from detm.viz.protocol import send_msg


class VizClient:
    def __init__(self, host: str, port: int, *, timeout_s: float = 2.0):
        self.host = str(host)
        self.port = int(port)
        self._sock = socket.create_connection((self.host, self.port), timeout=timeout_s)

    def send_state(
        self,
        *,
        state_blob: bytes,
        tick: int,
        signature: Optional[list[float]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "type": "state",
            "tick": int(tick),
            "state_blob": state_blob,
        }
        if signature is not None:
            payload["signature"] = [float(x) for x in signature]
        if meta is not None:
            payload["meta"] = meta
        send_msg(self._sock, payload)

    def close(self) -> None:
        try:
            send_msg(self._sock, {"type": "close"})
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass


@dataclass(frozen=True)
class VizDaemon:
    process: subprocess.Popen[str]
    host: str
    port: int

    def connect(self) -> VizClient:
        return VizClient(self.host, self.port)

    def terminate(self) -> None:
        try:
            self.process.terminate()
        except Exception:
            return


def start_local_daemon(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    cwd: str | None = None,
) -> VizDaemon:
    """Start a local viz daemon subprocess and return its connection info."""

    args = [
        sys.executable,
        "-m",
        "detm.viz.daemon",
        "--host",
        str(host),
        "--port",
        str(int(port)),
    ]
    proc = subprocess.Popen(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    line = proc.stdout.readline().strip()
    if not line:
        raise RuntimeError("Viz daemon did not report readiness")
    try:
        info = json.loads(line)
        ready_host = str(info["host"])
        ready_port = int(info["port"])
    except Exception as exc:
        raise RuntimeError(f"Unexpected viz daemon output: {line}") from exc
    return VizDaemon(process=proc, host=ready_host, port=ready_port)


__all__ = ["VizClient", "VizDaemon", "start_local_daemon"]

