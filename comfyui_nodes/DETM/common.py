from __future__ import annotations

import sys
from pathlib import Path


def ensure_detm_on_path() -> None:
    """Ensure `import detm` works when this pack is vendored inside the DETM repo.

    Expected layout:
      <repo>/comfyui_nodes/DETM/nodes.py  (and sibling modules)
    Then repo root is parents[2].
    """
    try:
        import detm  # noqa: F401
        return
    except Exception:
        pass

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


# Run on import
ensure_detm_on_path()
