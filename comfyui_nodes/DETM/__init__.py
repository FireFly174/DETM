"""ComfyUI node pack for DETM.

Install by symlinking (or copying) `comfyui_nodes/DETM` into ComfyUI's
`custom_nodes/DETM` folder, while keeping the DETM repo importable.
See `comfyui_nodes/DETM/README.md`.
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

