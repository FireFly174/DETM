#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Deprecated compatibility entrypoint for headless CLI.

Canonical CLI runtime lives in `detm_app.cli`.
"""

from __future__ import annotations

import warnings
from typing import Any

from detm_app.cli import main as _app_main
from detm_app.cli import run_headless as _app_run_headless

_DEPRECATION_MESSAGE = (
    "`detm.cli` is deprecated; use `detm_app.cli` instead. "
    "Compatibility wrapper will be removed in a future release."
)


def run_headless(*args: Any, **kwargs: Any):
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    return _app_run_headless(*args, **kwargs)


def main(argv: list[str] | None = None) -> int:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    return int(_app_main(argv))


__all__ = ["main", "run_headless"]


if __name__ == "__main__":
    raise SystemExit(main())
