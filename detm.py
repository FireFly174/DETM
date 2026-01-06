#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Compatibility wrapper for the headless CLI runner.

Use `python main.py` for UI or `python main.py ...` for headless runs.
This script remains as a convenience entrypoint.
"""

from __future__ import annotations

import sys

from detm.cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
