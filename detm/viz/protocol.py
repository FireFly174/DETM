"""Deprecated compatibility wrapper for viz protocol helpers.

Canonical implementation lives in `detm_app.protocol`.
"""

from __future__ import annotations

import socket
import warnings
from typing import Any, Dict

from detm_app.protocol import recv_msg as _app_recv_msg
from detm_app.protocol import send_msg as _app_send_msg

_DEPRECATION_MESSAGE = (
    "`detm.viz.protocol` is deprecated; use `detm_app.protocol` instead. "
    "Compatibility wrapper will be removed in a future release."
)


def send_msg(sock: socket.socket, payload: Dict[str, Any]) -> None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    _app_send_msg(sock, payload)


def recv_msg(sock: socket.socket) -> Dict[str, Any]:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    return _app_recv_msg(sock)


__all__ = ["recv_msg", "send_msg"]
