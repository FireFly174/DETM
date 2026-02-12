"""Deprecated compatibility wrapper for UI config hints.

Canonical module lives in `detm_app.config_hints`.
"""

from __future__ import annotations

import warnings

from detm_app.config_hints import load_tooltips_from_config_default as _app_load_tooltips

_DEPRECATION_MESSAGE = (
    "`detm.ui.config_hints` is deprecated; use `detm_app.config_hints` instead. "
    "Compatibility wrapper will be removed in a future release."
)


def load_tooltips_from_config_default():
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    return _app_load_tooltips()


__all__ = ["load_tooltips_from_config_default"]
