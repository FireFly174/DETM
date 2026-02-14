from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imported_modules(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
    return out


def _imported_modules_first_existing(*paths: Path) -> set[str]:
    for path in paths:
        if path.exists():
            return _imported_modules(path)
    raise FileNotFoundError(f"No expected file found: {[str(p) for p in paths]}")


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _find_forbidden_imports(*, roots: list[Path], forbidden_prefixes: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []
    for sub_root in roots:
        for path in _python_files(sub_root):
            modules = _imported_modules(path)
            if any(
                module == prefix or module.startswith(f"{prefix}.")
                for module in modules
                for prefix in forbidden_prefixes
            ):
                offenders.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return offenders


def test_napari_and_config_do_not_import_tk_modules() -> None:
    offenders = _find_forbidden_imports(
        roots=[
            ROOT / "detm_app" / "ui" / "napari",
            ROOT / "detm_app" / "config",
        ],
        forbidden_prefixes=("detm_app.ui.tk",),
    )
    assert offenders == []


def test_config_layer_does_not_import_runner_modules() -> None:
    offenders = _find_forbidden_imports(
        roots=[ROOT / "detm_app" / "config"],
        forbidden_prefixes=("detm_app.runner",),
    )
    assert offenders == []


def test_ui_runtime_does_not_import_frontend_layers() -> None:
    modules = _imported_modules_first_existing(
        ROOT / "detm_app" / "runtime" / "ui_runtime" / "core.py",
        ROOT / "detm_app" / "runtime" / "ui_runtime.py",
    )
    assert not any(module == "detm_app.ui" or module.startswith("detm_app.ui.") for module in modules)


def test_runner_shell_uses_viewer_registry_not_direct_ui_imports() -> None:
    path = ROOT / "detm_app" / "runner" / "shell.py"
    modules = _imported_modules(path)
    assert "detm_app.runner.viewer_registry" in modules
    assert not any(module == "detm_app.ui" or module.startswith("detm_app.ui.") for module in modules)


def test_tk_launcher_stays_orchestration_layer() -> None:
    path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "launcher.py"
    modules = _imported_modules(path)
    assert "detm_app.runtime.ui_runtime" in modules
    assert "detm_app.ui.tk.runner.flow" in modules
    assert not any(module == "detm_app.ui.napari" or module.startswith("detm_app.ui.napari.") for module in modules)


def test_napari_interactive_controller_uses_flow_modules() -> None:
    path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "controller.py"
    modules = _imported_modules(path)
    expected = {
        "detm_app.ui.napari.interactive.flow.actions",
        "detm_app.ui.napari.interactive.flow.batch",
        "detm_app.ui.napari.interactive.flow.controls",
        "detm_app.ui.napari.interactive.flow.influence",
        "detm_app.ui.napari.interactive.flow.render",
        "detm_app.ui.napari.interactive.flow.settings",
        "detm_app.ui.napari.interactive.flow.ui_wiring",
        "detm_app.ui.napari.interactive.flow.widget_io",
    }
    assert expected.issubset(modules)
    assert not any(module == "detm_app.ui.tk" or module.startswith("detm_app.ui.tk.") for module in modules)


def test_napari_flow_package_does_not_import_tk() -> None:
    offenders = _find_forbidden_imports(
        roots=[ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow"],
        forbidden_prefixes=("detm_app.ui.tk",),
    )
    assert offenders == []
