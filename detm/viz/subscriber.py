"""Deprecated compatibility wrapper for viz TCP subscriber.

Canonical implementation lives in `detm_app.subscriber`.
"""

from __future__ import annotations

import warnings

from detm_app.subscriber import TcpVizSubscriber as _AppTcpVizSubscriber
from detm_app.subscriber import VizPacket

_DEPRECATION_MESSAGE = (
    "`detm.viz.subscriber` is deprecated; use `detm_app.subscriber` instead. "
    "Compatibility wrapper will be removed in a future release."
)


class TcpVizSubscriber(_AppTcpVizSubscriber):
    def __init__(self, host: str, port: int, *, timeout_s: float = 2.0) -> None:
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        super().__init__(host, port, timeout_s=timeout_s)


__all__ = ["TcpVizSubscriber", "VizPacket"]
