from __future__ import annotations

import ast
from pathlib import Path
import warnings

from detm.runtime.config import DETMConfig


def test_detm_cli_facade_warns_and_delegates(monkeypatch):
    import detm.cli as legacy_cli

    monkeypatch.setattr(legacy_cli, "_app_main", lambda _argv: 0)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        rc = legacy_cli.main(["--dummy"])

    assert int(rc) == 0
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_detm_ui_tk_runner_facade_warns_and_delegates(monkeypatch):
    import detm.ui.tk_runner as legacy_tk
    from detm_app.tk_runner import UiRunSettings as app_ui_settings

    called = {"ok": False}

    def _fake_launch(_settings):
        called["ok"] = True

    monkeypatch.setattr(legacy_tk, "_app_launch_tk_ui", _fake_launch)

    settings = legacy_tk.UiRunSettings(config=DETMConfig())
    assert legacy_tk.UiRunSettings is app_ui_settings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        legacy_tk.launch_tk_ui(settings)

    assert called["ok"] is True
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_main_imports_detm_app_entrypoints():
    src = Path("main.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(src, filename="main.py")

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(str(alias.name))
        elif isinstance(node, ast.ImportFrom):
            imported_modules.add(str(node.module or ""))

    assert "detm_app.cli" in imported_modules
    assert "detm_app.tk_runner" in imported_modules
    assert "detm.cli" not in imported_modules
    assert "detm.ui.tk_runner" not in imported_modules
