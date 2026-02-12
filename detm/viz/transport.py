"""Deprecated compatibility wrapper for viz transport helpers.

Canonical implementation lives in `detm_app.transport`.
"""

from __future__ import annotations

import warnings
from typing import Any

from detm_app.transport import NullVizTransport
from detm_app.transport import TcpVizTransport as _AppTcpVizTransport
from detm_app.transport import VizTransport
from detm_app.transport import clear_viz_endpoint_registry as _app_clear_registry
from detm_app.transport import load_viz_endpoint_registry as _app_load_registry
from detm_app.transport import open_viz_transport as _app_open_transport
from detm_app.transport import write_viz_endpoint_registry as _app_write_registry

_DEPRECATION_MESSAGE = (
    "`detm.viz.transport` is deprecated; use `detm_app.transport` instead. "
    "Compatibility wrapper will be removed in a future release."
)


class TcpVizTransport(_AppTcpVizTransport):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        super().__init__(*args, **kwargs)


def write_viz_endpoint_registry(*, host: str, port: int) -> None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    _app_write_registry(host=host, port=port)


def load_viz_endpoint_registry() -> tuple[str, int] | None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    return _app_load_registry()


def clear_viz_endpoint_registry(*, host: str, port: int) -> None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    _app_clear_registry(host=host, port=port)


def open_viz_transport(
    *,
    enabled: bool,
    transport: str = "tcp",
    host: str = "127.0.0.1",
    port: int = 0,
    connect: bool = False,
    keep_open: bool = False,
) -> VizTransport:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    return _app_open_transport(
        enabled=enabled,
        transport=transport,
        host=host,
        port=port,
        connect=connect,
        keep_open=keep_open,
    )


__all__ = [
    "clear_viz_endpoint_registry",
    "NullVizTransport",
    "TcpVizTransport",
    "VizTransport",
    "load_viz_endpoint_registry",
    "open_viz_transport",
    "write_viz_endpoint_registry",
]
