from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_import_detm_does_not_eagerly_import_app_or_legacy_layers():
    # Run in a clean Python process to avoid mutating test runner module cache.
    script = """
import importlib
import sys
importlib.import_module("detm")
forbidden = [
    name
    for name in sys.modules
    if name == "detm_app"
    or name.startswith("detm_app.")
    or name == "detm_legacy"
    or name.startswith("detm_legacy.")
]
raise SystemExit(1 if forbidden else 0)
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Expected `import detm` to stay core-only, but app/legacy layers were imported.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
