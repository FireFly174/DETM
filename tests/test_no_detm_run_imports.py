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

ALLOWED_PREFIXES = (
    "detm/run/",
)

ALLOWED_FILES = {
    "tests/test_run_compat_facade.py",
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


def _is_allowed(relative_path: str) -> bool:
    rel = str(relative_path).replace("\\", "/")
    if rel in ALLOWED_FILES:
        return True
    return any(rel.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _find_detm_run_import_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=str(path))
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = str(alias.name)
                if name == "detm.run" or name.startswith("detm.run."):
                    violations.append(f"{rel}:{int(node.lineno)} import {name}")
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if module == "detm.run" or module.startswith("detm.run."):
                violations.append(f"{rel}:{int(node.lineno)} from {module} import ...")
                continue
            if module == "detm":
                for alias in node.names:
                    if str(alias.name) == "run":
                        violations.append(f"{rel}:{int(node.lineno)} from detm import run")
    return violations


def test_no_new_detm_run_imports_outside_compat_layer():
    violations: list[str] = []
    for path in _iter_python_files():
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if _is_allowed(rel):
            continue
        violations.extend(_find_detm_run_import_violations(path))

    assert violations == [], "Forbidden `detm.run` imports found:\n" + "\n".join(violations)
