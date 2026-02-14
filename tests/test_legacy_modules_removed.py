from __future__ import annotations

import importlib
from pathlib import Path

import pytest


REMOVED_PATHS = (
    "detm.py",
    "detm/cli.py",
    "detm/app_settings.py",
    "detm/_compat.py",
    "detm/run",
    "detm/ui",
    "detm/viz",
)

REMOVED_MODULES = (
    "detm.cli",
    "detm.app_settings",
    "detm.run",
    "detm.run.bus",
    "detm.ui",
    "detm.ui.tk_runner",
    "detm.viz",
    "detm.viz.transport",
)


def test_legacy_module_paths_are_removed():
    for path in REMOVED_PATHS:
        assert not Path(path).exists(), f"Legacy path should be removed: {path}"


@pytest.mark.parametrize("module_name", REMOVED_MODULES)
def test_importing_removed_legacy_modules_fails(module_name: str):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)
