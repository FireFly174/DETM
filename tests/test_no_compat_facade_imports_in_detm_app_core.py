from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOTS = [
    REPO_ROOT / "detm_app" / "config",
    REPO_ROOT / "detm_app" / "runtime",
    REPO_ROOT / "detm_app" / "runner",
    REPO_ROOT / "detm_app" / "ui",
    REPO_ROOT / "detm_app" / "transport",
]
FACADE_MODULES = {
    "detm_app.app_settings",
    "detm_app.bus",
    "detm_app.cli",
    "detm_app.client",
    "detm_app.coarsening",
    "detm_app.config_hints",
    "detm_app.daemon",
    "detm_app.napari_lab",
    "detm_app.napari_subscriber",
    "detm_app.orchestrate",
    "detm_app.protocol",
    "detm_app.scheduler",
    "detm_app.session",
    "detm_app.subscriber",
    "detm_app.subscribers",
    "detm_app.tk_panel",
    "detm_app.tk_runner",
    "detm_app.tooltips",
}
FACADE_NAMES = {name.split(".")[-1] for name in FACADE_MODULES}


def _iter_python_files() -> list[Path]:
    out: list[Path] = []
    for root in CANONICAL_ROOTS:
        out.extend(path for path in root.rglob("*.py") if path.is_file())
    return sorted(out)


def _is_forbidden_module(name: str) -> bool:
    return name in FACADE_MODULES or any(name.startswith(f"{prefix}.") for prefix in FACADE_MODULES)


def _find_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=str(path))
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = str(alias.name)
                if _is_forbidden_module(name):
                    violations.append(f"{rel}:{int(node.lineno)} import {name}")
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if _is_forbidden_module(module):
                violations.append(f"{rel}:{int(node.lineno)} from {module} import ...")
                continue
            if module == "detm_app":
                imported = {str(alias.name) for alias in node.names}
                bad = sorted(name for name in imported if name in FACADE_NAMES)
                for name in bad:
                    violations.append(f"{rel}:{int(node.lineno)} from detm_app import {name}")
    return violations


def test_no_compat_facade_imports_in_detm_app_core_packages():
    violations: list[str] = []
    for path in _iter_python_files():
        violations.extend(_find_violations(path))
    assert violations == [], "Forbidden compatibility-facade imports in canonical detm_app packages:\n" + "\n".join(violations)

