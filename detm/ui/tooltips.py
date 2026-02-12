"""Deprecated compatibility wrapper for UI tooltips.

Canonical module lives in `detm_app.tooltips`.
"""

from __future__ import annotations

import warnings

from detm_app.tooltips import Tooltip as _AppTooltip
from detm_app.tooltips import attach_tooltip as _app_attach_tooltip

_DEPRECATION_MESSAGE = (
    "`detm.ui.tooltips` is deprecated; use `detm_app.tooltips` instead. "
    "Compatibility wrapper will be removed in a future release."
)


Tooltip = _AppTooltip


def attach_tooltip(widget: object, text: str) -> None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    _app_attach_tooltip(widget, text)


__all__ = ["Tooltip", "attach_tooltip"]
