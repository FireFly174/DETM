from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_TARGETS = (
    REPO_ROOT / "detm",
    REPO_ROOT / "detm_app",
    REPO_ROOT / "tests",
    REPO_ROOT / "main.py",
    REPO_ROOT / "detm.py",
    REPO_ROOT / "detm_napari_viewer.py",
)

ALLOWED_FILES = {
    "detm/cli.py",
    "detm/ui/config_hints.py",
    "detm/ui/tk_runner.py",
    "detm/ui/tooltips.py",
    "detm/viz/client.py",
    "detm/viz/daemon.py",
    "detm/viz/protocol.py",
    "detm/viz/subscriber.py",
    "detm/viz/transport.py",
    "tests/test_entrypoint_facades.py",
    "tests/test_ui_helper_facades.py",
    "detm/viz/tk_panel.py",
    "detm/viz/napari_subscriber.py",
    "tests/test_viz_facades.py",
}


def _iter_python_files() -> list[Path]:
    out: list[Path] = []
    for target in SCAN_TARGETS:
        if target.is_file() and target.suffix == ".py":
            out.append(target)
            continue
        if target.is_dir():
            out.extend(path for path in target.rglob("*.py") if path.is_file())
    return sorted(set(out))


def _find_legacy_entrypoint_import_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=str(path))
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    violations: list[str] = []
    legacy_modules = (
        "detm.cli",
        "detm.ui.tk_runner",
        "detm.ui.config_hints",
        "detm.ui.tooltips",
        "detm.viz.client",
        "detm.viz.daemon",
        "detm.viz.protocol",
        "detm.viz.subscriber",
        "detm.viz.transport",
        "detm.viz.tk_panel",
        "detm.viz.napari_subscriber",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = str(alias.name)
                for legacy_module in legacy_modules:
                    if name == legacy_module or name.startswith(f"{legacy_module}."):
                        violations.append(f"{rel}:{int(node.lineno)} import {name}")
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            for legacy_module in legacy_modules:
                if module == legacy_module or module.startswith(f"{legacy_module}."):
                    violations.append(f"{rel}:{int(node.lineno)} from {module} import ...")
    return violations


def test_no_new_legacy_entrypoint_imports():
    violations: list[str] = []
    for path in _iter_python_files():
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if rel in ALLOWED_FILES:
            continue
        violations.extend(_find_legacy_entrypoint_import_violations(path))

    assert violations == [], "Forbidden legacy entrypoint imports found:\n" + "\n".join(violations)
