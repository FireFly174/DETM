"""Deprecated compatibility entrypoint for Tk UI runner.

Canonical UI runtime lives in `detm_app.tk_runner`.
"""

from __future__ import annotations

import warnings

from detm_app.tk_runner import DetmTkRunner as _AppDetmTkRunner
from detm_app.tk_runner import UiRunSettings as _AppUiRunSettings
from detm_app.tk_runner import launch_tk_ui as _app_launch_tk_ui

_DEPRECATION_MESSAGE = (
    "`detm.ui.tk_runner` is deprecated; use `detm_app.tk_runner` instead. "
    "Compatibility wrapper will be removed in a future release."
)


UiRunSettings = _AppUiRunSettings
DetmTkRunner = _AppDetmTkRunner


def launch_tk_ui(settings: UiRunSettings) -> None:  # pragma: no cover
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    _app_launch_tk_ui(settings)


__all__ = ["DetmTkRunner", "UiRunSettings", "launch_tk_ui"]
