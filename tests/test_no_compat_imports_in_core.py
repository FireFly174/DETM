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

FORBIDDEN_DIRECT_PREFIXES = (
    "detm_legacy",
    "detm.app_settings",
    "detm.cli",
    "detm.run",
    "detm.ui",
    "detm.viz",
)

FORBIDDEN_DETM_FROM_IMPORTS = {
    "app_settings",
    "cli",
    "run",
    "ui",
    "viz",
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


def _is_forbidden_import(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_DIRECT_PREFIXES
    )


def _find_compat_import_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=str(path))
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = str(alias.name)
                if _is_forbidden_import(name):
                    violations.append(f"{rel}:{int(node.lineno)} import {name}")
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if _is_forbidden_import(module):
                violations.append(f"{rel}:{int(node.lineno)} from {module} import ...")
                continue
            if module == "detm":
                for alias in node.names:
                    if str(alias.name) in FORBIDDEN_DETM_FROM_IMPORTS:
                        violations.append(f"{rel}:{int(node.lineno)} from detm import {alias.name}")
    return violations


def test_core_layers_do_not_import_compatibility_entrypoints():
    violations: list[str] = []
    for path in _iter_python_files():
        violations.extend(_find_compat_import_violations(path))

    assert violations == [], (
        "Forbidden compatibility imports found in detm core layers:\n" + "\n".join(violations)
    )
