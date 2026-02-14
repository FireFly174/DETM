from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DETM_ROOT = REPO_ROOT / "detm"


def _iter_python_files() -> list[Path]:
    return sorted(path for path in DETM_ROOT.rglob("*.py") if path.is_file())


def _find_detm_app_import_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=str(path))
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = str(alias.name)
                if name == "detm_app" or name.startswith("detm_app."):
                    violations.append(f"{rel}:{int(node.lineno)} import {name}")
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if module == "detm_app" or module.startswith("detm_app."):
                violations.append(f"{rel}:{int(node.lineno)} from {module} import ...")
    return violations


def test_detm_has_no_detm_app_imports():
    violations: list[str] = []
    for path in _iter_python_files():
        violations.extend(_find_detm_app_import_violations(path))

    assert violations == [], "Forbidden detm_app imports found in detm package:\n" + "\n".join(violations)
