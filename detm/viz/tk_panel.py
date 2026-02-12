"""Deprecated compatibility wrapper for viz Tk panel.

Canonical implementation lives in `detm_app.tk_panel`.
"""

from __future__ import annotations

import warnings

from detm_app.tk_panel import DetmVizPanel as _AppDetmVizPanel
from detm_app.tk_panel import VizFrame

_DEPRECATION_MESSAGE = (
    "`detm.viz.tk_panel` is deprecated; use `detm_app.tk_panel` instead. "
    "Compatibility wrapper will be removed in a future release."
)


class DetmVizPanel(_AppDetmVizPanel):  # pragma: no cover - UI wrapper
    def __init__(self, parent) -> None:
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        super().__init__(parent)


__all__ = ["DetmVizPanel", "VizFrame"]
