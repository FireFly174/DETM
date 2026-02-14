#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""DETM interactive launcher.

`python main.py` opens napari interactive mode by default
(in-process controls + direct runtime manipulation).

`python main.py napari ...` starts explicit napari lab flow
(producer + subscriber) or interactive mode via `--interactive`.

`python main.py ...` (other args) runs the headless CLI runner.

`python main.py shell ...` composes explicit shell roles
(`controller`/`runner`/`viewer`) for future external orchestration (LLM-ready).
"""

from __future__ import annotations

import sys
from pathlib import Path
from importlib import resources
from textwrap import dedent


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


def _napari_main(argv: list[str]) -> int:
    from detm_app.ui.napari.lab import main as napari_main

    return int(napari_main(argv))


def _print_launcher_help() -> None:
    text = dedent(
        """
        DETM launcher (`main.py`)

        Usage:
          python main.py
          python main.py napari [NAPARI_ARGS]
          python main.py shell [SHELL_ARGS]
          python main.py headless [HEADLESS_ARGS]
          python main.py [HEADLESS_ARGS]

        Modes:
          (no args)     Start napari interactive mode with local config bootstrap
          napari        Start napari lab/interactive flow
          shell         Start orchestration shell role-router
          headless      Explicit headless CLI mode
          other args    Passed through to headless CLI for backward compatibility

        Help:
          python main.py --help
            Show this launcher-level help (only run modes/start options).
          python main.py headless --help
            Show full headless CLI options (including advanced/internal knobs).
          python main.py napari --help
            Show napari mode options.
          python main.py shell --help
            Show shell mode options.
        """
    ).strip()
    print(text)


def main() -> int:
    _ensure_repo_on_path()

    # Default: napari interactive UI flow. Otherwise: headless CLI.
    argv = sys.argv[1:]
    if argv and argv[0] in {"-h", "--help", "help"}:
        _print_launcher_help()
        return 0

    if argv and argv[0] == "shell":
        from detm_app.runner.shell import main as shell_main

        return int(shell_main(argv[1:]))

    if argv and argv[0] in {"napari", "ui"}:
        return _napari_main(argv[1:])

    if argv and argv[0] == "headless":
        from detm_app.runner.headless import main as cli_main

        return int(cli_main(argv[1:]))

    if not argv:
        repo_root = Path(__file__).resolve().parent
        local_cfg = _ensure_local_config(repo_root)
        return _napari_main(["--interactive", "--config", str(local_cfg)])

    from detm_app.runner.headless import main as cli_main

    return int(cli_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())

