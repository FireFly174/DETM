#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""DETM interactive launcher.

`python main.py` opens a lightweight settings + visualization UI.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_on_path() -> None:
    repo_root = Path(__file__).resolve().parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main() -> int:
    _ensure_repo_on_path()

    from detm.presets import load_preset_config
    from detm.ui.tk_runner import UiRunSettings, launch_tk_ui

    settings = UiRunSettings(config=load_preset_config("default"), seed=1, record_dir=Path("runs/out/ui_run"))
    launch_tk_ui(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

