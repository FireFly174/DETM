"""Small IPC protocol used by the visualization daemon.

We intentionally keep this minimal:
- transport: TCP localhost
- framing: 4-byte big-endian length prefix + msgpack payload
- payload: dict with `type` and associated fields
"""

from __future__ import annotations

import socket
import struct
from typing import Any, Dict

import msgpack


def send_msg(sock: socket.socket, payload: Dict[str, Any]) -> None:
    data = msgpack.dumps(payload, use_bin_type=True)
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise EOFError("socket closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_msg(sock: socket.socket) -> Dict[str, Any]:
    header = _recv_exact(sock, 4)
    (length,) = struct.unpack(">I", header)
    data = _recv_exact(sock, length)
    return msgpack.loads(data, raw=False)


__all__ = ["recv_msg", "send_msg"]

