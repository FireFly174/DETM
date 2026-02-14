from __future__ import annotations

import ast
from pathlib import Path


def _imported_modules(path: str) -> set[str]:
    src = Path(path).read_text(encoding="utf-8-sig")
    tree = ast.parse(src, filename=path)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(str(alias.name))
        elif isinstance(node, ast.ImportFrom):
            imported.add(str(node.module or ""))
    return imported


def test_main_entrypoint_uses_detm_app_only():
    imported = _imported_modules("main.py")
    assert "detm_app.runner.shell" in imported
    assert "detm_app.runner.headless" in imported
    assert "detm_app.ui.napari.lab" in imported
    assert "detm_app.ui.tk.runner" not in imported
    assert "detm_app.config.app_settings" not in imported
    assert "detm.cli" not in imported
    assert "detm.ui.tk_runner" not in imported
    assert "detm.app_settings" not in imported


def test_detm_py_entrypoint_uses_detm_app_cli():
    imported = _imported_modules("detm.py")
    assert "detm_app.runner.headless" in imported
    assert "detm.cli" not in imported


def test_napari_viewer_entrypoint_uses_detm_app():
    imported = _imported_modules("detm_napari_viewer.py")
    assert "detm_app.ui.napari.subscriber" in imported
    assert "detm.viz.napari_subscriber" not in imported


def test_napari_lab_entrypoint_uses_detm_app():
    imported = _imported_modules("detm_napari_lab.py")
    assert "detm_app.ui.napari.lab" in imported

