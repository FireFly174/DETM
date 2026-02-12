"""Helpers for deprecated `detm.run` compatibility exports."""

from __future__ import annotations

import warnings
from importlib import import_module
from typing import Any

_WARNED_EXPORTS: set[tuple[str, str]] = set()
DETM_RUN_DEPRECATED_SINCE = "0.0.0"
DETM_RUN_REMOVAL_TARGET_VERSION = "0.3.0"
DETM_RUN_REMOVAL_TARGET_DATE = "2026-06-30"
DETM_RUN_MIGRATION_DOC = "docs/rus/30_architecture/detm_run_migration.md"


def load_export(
    *,
    shim_module: str,
    symbol: str,
    target_module: str,
    target_symbol: str | None = None,
) -> Any:
    resolved_symbol = str(target_symbol or symbol)
    warn_key = (str(shim_module), str(symbol))
    if warn_key not in _WARNED_EXPORTS:
        warnings.warn(
            (
                f"`{shim_module}.{symbol}` is deprecated; "
                f"use `{target_module}.{resolved_symbol}`. "
                f"Scheduled removal: {DETM_RUN_REMOVAL_TARGET_VERSION} "
                f"(target date: {DETM_RUN_REMOVAL_TARGET_DATE}). "
                f"Migration guide: `{DETM_RUN_MIGRATION_DOC}`."
            ),
            DeprecationWarning,
            stacklevel=3,
        )
        _WARNED_EXPORTS.add(warn_key)
    module = import_module(str(target_module))
    return getattr(module, resolved_symbol)


__all__ = [
    "DETM_RUN_DEPRECATED_SINCE",
    "DETM_RUN_REMOVAL_TARGET_VERSION",
    "DETM_RUN_REMOVAL_TARGET_DATE",
    "DETM_RUN_MIGRATION_DOC",
    "load_export",
]
