from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imported_modules(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.append(node.module)
    return out


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def test_napari_and_config_do_not_import_tk_modules() -> None:
    roots = [
        ROOT / "detm_app" / "ui" / "napari",
        ROOT / "detm_app" / "config",
    ]
    offenders: list[str] = []
    for sub_root in roots:
        for path in _python_files(sub_root):
            modules = _imported_modules(path)
            if any(module.startswith("detm_app.ui.tk") for module in modules):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_config_layer_does_not_import_runner_modules() -> None:
    offenders: list[str] = []
    for path in _python_files(ROOT / "detm_app" / "config"):
        modules = _imported_modules(path)
        if any(module.startswith("detm_app.runner") for module in modules):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_ui_runtime_does_not_import_frontend_layers() -> None:
    offenders: list[str] = []
    path = ROOT / "detm_app" / "runtime" / "ui_runtime.py"
    modules = _imported_modules(path)
    if any(module.startswith("detm_app.ui.tk") for module in modules):
        offenders.append(str(path.relative_to(ROOT)))
    if any(module.startswith("detm_app.ui.napari") for module in modules):
        offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_runner_shell_uses_viewer_registry_not_direct_ui_imports() -> None:
    path = ROOT / "detm_app" / "runner" / "shell.py"
    modules = _imported_modules(path)
    assert not any(module.startswith("detm_app.ui.") for module in modules)
    assert "detm_app.runner.viewer_registry" in modules


def test_tk_runner_wrapper_points_to_launcher() -> None:
    runner_path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "__init__.py"
    source = runner_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.tk.runner.launcher import DetmTkRunner, UiRunSettings, launch_tk_ui" in source


def test_tk_launcher_reuses_runtime_and_batch_services() -> None:
    launcher_path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "launcher.py"
    source = launcher_path.read_text(encoding="utf-8")
    assert "from detm_app.runtime.ui_runtime import DetmUiRunner" in source
    assert "from detm_app.config.ui_models import UiRunSettings" in source
    assert "from detm_app.runner.batch_service import (" in source
    assert "DetmTkRunner = DetmUiRunner" in source


def test_napari_interactive_uses_shared_batch_service() -> None:
    path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "__init__.py"
    source = path.read_text(encoding="utf-8")
    assert "from detm_app.runner.batch_service import (" in source
