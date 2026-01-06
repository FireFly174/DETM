"""Visualization helpers (optional runtime sidecar).

`detm` core/runtime should not depend on any UI framework. This package
provides a "viz daemon" that can run in a separate process and receive
serialized state blobs from a runner (CLI/UI/orchestrator).
"""

from __future__ import annotations

