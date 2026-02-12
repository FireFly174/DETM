"""Deprecated compatibility wrapper for viz daemon helpers.

Canonical implementation lives in `detm_app.daemon`.
"""

from __future__ import annotations

import warnings
from typing import Any

from detm_app.daemon import StatePacket
from detm_app.daemon import VizHub as _AppVizHub
from detm_app.daemon import run_daemon as _app_run_daemon

_DEPRECATION_MESSAGE = (
    "`detm.viz.daemon` is deprecated; use `detm_app.daemon` instead. "
    "Compatibility wrapper will be removed in a future release."
)


class VizHub(_AppVizHub):
    def __init__(self, host: str, port: int):
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        super().__init__(host, port)


def run_daemon(host: str, port: int) -> None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    _app_run_daemon(host, port)


def main(*_args: Any, **_kwargs: Any) -> None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    from detm_app.daemon import main as _app_main

    _app_main()


__all__ = ["StatePacket", "VizHub", "main", "run_daemon"]


if __name__ == "__main__":
    main()
