#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Backward-compatible launcher for napari read-only subscriber mode.

Canonical implementation lives in `detm_app.ui.napari.subscriber`.
"""

from __future__ import annotations

from detm_app.ui.napari.subscriber import main


if __name__ == "__main__":
    raise SystemExit(main())

