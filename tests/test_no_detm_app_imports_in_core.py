from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_TARGETS = (
    REPO_ROOT / "detm" / "__init__.py",
    REPO_ROOT / "detm" / "analysis",
    REPO_ROOT / "detm" / "core",
    REPO_ROOT / "detm" / "integrations",
    REPO_ROOT / "detm" / "metrics",
    REPO_ROOT / "detm" / "presets",
    REPO_ROOT / "detm" / "runtime",
)


def _iter_python_files() -> list[Path]:
    out: list[Path] = []
    for target in SCAN_TARGETS:
        if target.is_file() and target.suffix == ".py":
            out.append(target)
            continue
        if target.is_dir():
            out.extend(path for path in target.rglob("*.py") if path.is_file())
    return sorted(set(out))


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


def test_no_detm_app_imports_inside_core_layers():
    violations: list[str] = []
    for path in _iter_python_files():
        violations.extend(_find_detm_app_import_violations(path))

    assert violations == [], "Forbidden detm_app imports found in detm core layers:\n" + "\n".join(violations)
