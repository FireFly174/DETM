"""Deprecated compatibility wrapper for viz client helpers.

Canonical implementation lives in `detm_app.client`.
"""

from __future__ import annotations

import warnings
from typing import Any

from detm_app.client import VizClient as _AppVizClient
from detm_app.client import VizDaemon
from detm_app.client import start_local_daemon as _app_start_local_daemon

_DEPRECATION_MESSAGE = (
    "`detm.viz.client` is deprecated; use `detm_app.client` instead. "
    "Compatibility wrapper will be removed in a future release."
)


class VizClient(_AppVizClient):
    def __init__(self, host: str, port: int, *, timeout_s: float = 2.0):
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        super().__init__(host, port, timeout_s=timeout_s)


def start_local_daemon(*args: Any, **kwargs: Any) -> VizDaemon:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    return _app_start_local_daemon(*args, **kwargs)


__all__ = ["VizClient", "VizDaemon", "start_local_daemon"]
