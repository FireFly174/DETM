from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DETM_ROOT = REPO_ROOT / "detm"


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


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


def _find_forbidden_imports(*, root: Path, forbidden_prefixes: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []
    for path in _iter_python_files(root):
        modules = _imported_modules(path)
        if any(
            module == prefix or module.startswith(f"{prefix}.")
            for module in modules
            for prefix in forbidden_prefixes
        ):
            offenders.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
    return offenders


def test_detm_core_does_not_import_higher_layers() -> None:
    offenders = _find_forbidden_imports(
        root=DETM_ROOT / "core",
        forbidden_prefixes=(
            "detm.runtime",
            "detm.integrations",
            "detm.analysis",
            "detm.presets",
            "detm_app",
        ),
    )
    assert offenders == []


def test_detm_runtime_does_not_import_upper_app_layers() -> None:
    offenders = _find_forbidden_imports(
        root=DETM_ROOT / "runtime",
        forbidden_prefixes=(
            "detm.integrations",
            "detm.analysis",
            "detm.presets",
            "detm_app",
        ),
    )
    assert offenders == []


def test_detm_metrics_does_not_import_upper_app_layers() -> None:
    offenders = _find_forbidden_imports(
        root=DETM_ROOT / "metrics",
        forbidden_prefixes=(
            "detm.integrations",
            "detm.analysis",
            "detm.presets",
            "detm_app",
        ),
    )
    assert offenders == []
