#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""DETM interactive launcher.

`python main.py` opens a lightweight settings + visualization UI.

`python main.py ...` (any non-`ui` args) runs the headless CLI runner
with the same preset/config mechanism.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from importlib import resources


def _ensure_repo_on_path() -> None:
    repo_root = Path(__file__).resolve().parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _ensure_local_config(repo_root: Path) -> Path:
    """Ensure a local untracked config exists and return its path.

    Priority:
    - `config.example.py` (preferred for no-args UX)
    - `config.py`

    If neither exists, copy `detm/presets/config.default.py` to `config.example.py`.
    """

    example_path = repo_root / "config.example.py"
    config_path = repo_root / "config.py"

    if example_path.exists():
        return example_path
    if config_path.exists():
        return config_path

    template = resources.files("detm.presets") / "config.default.py"
    content = template.read_text(encoding="utf-8")
    example_path.write_text(content, encoding="utf-8")
    return example_path


def _ui_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="main.py ui", description="DETM UI launcher")
    ap.add_argument("--preset", default="default", help="Preset name from detm/presets")
    ap.add_argument("--config", default=None, help="Path to override config (.json or .py; may include `ui` defaults)")
    args = ap.parse_args(argv)

    from detm.app_settings import build_runtime_config, build_ui_overrides, load_merged_payload
    from detm_app.tk_runner import UiRunSettings, launch_tk_ui

    payload = load_merged_payload(preset=str(args.preset), override_path=args.config)
    config = build_runtime_config(payload)
    ui_payload = payload.get("ui", {}) if isinstance(payload.get("ui", {}), dict) else {}
    overrides = build_ui_overrides(ui_payload)

    # Provide safe defaults if preset doesn't include UI section.
    settings = UiRunSettings(config=config, seed=1, record_dir=Path("runs/out/ui_run"))
    for key, value in overrides.items():
        if key == "record_dir":
            setattr(settings, key, Path(value) if value else None)
        else:
            setattr(settings, key, value)

    launch_tk_ui(settings)
    return 0


def main() -> int:
    _ensure_repo_on_path()

    # Default: UI. Anything else: forward to headless CLI.
    argv = sys.argv[1:]
    if not argv or argv[0] == "ui":
        if not argv:
            repo_root = Path(__file__).resolve().parent
            local_cfg = _ensure_local_config(repo_root)
            return _ui_main(["--config", str(local_cfg)])
        return _ui_main(argv[1:] if argv and argv[0] == "ui" else argv)

    from detm_app.cli import main as cli_mainou


    return int(cli_mainou(argv))


if __name__ == "__main__":
    raise SystemExit(main())
