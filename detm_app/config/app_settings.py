"""Shared settings loader for DETM app-layer entrypoints.

Goals:
- Keep a single JSON config source of truth that can drive both UI and headless runs.
- Allow merging a packaged preset with a user-provided override JSON file.
"""

from __future__ import annotations

import json
from dataclasses import fields
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Mapping

from detm.presets import preset_names
from detm.runtime.config import DETMConfig


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = _deep_merge(out[key], value)  # type: ignore[arg-type]
        else:
            out[key] = value
    return out


def load_preset_payload(name: str = "default") -> Dict[str, Any]:
    if name not in set(preset_names()):
        raise ValueError(f"Unknown preset: {name}")
    preset_path = resources.files("detm.presets") / f"{name}.json"
    return json.loads(preset_path.read_text(encoding="utf-8"))


def load_override_payload(path: str | None) -> Dict[str, Any]:
    if path is None:
        return {}
    p = Path(path)
    if p.suffix.lower() == ".py":
        return load_override_payload_py(p)
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Override config must be a JSON object")
    return payload


def load_override_payload_py(path: Path) -> Dict[str, Any]:
    """Load an override config from a Python file.

    Supported conventions inside the module:
    - `CONFIG: dict`
    - `get_config() -> dict`
    - `load_config() -> dict`
    """

    import importlib.util

    spec = importlib.util.spec_from_file_location("detm_user_config", str(path))
    if spec is None or spec.loader is None:
        raise ValueError(f"Failed to import config module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]

    if hasattr(module, "get_config") and callable(getattr(module, "get_config")):
        payload = module.get_config()
    elif hasattr(module, "load_config") and callable(getattr(module, "load_config")):
        payload = module.load_config()
    elif hasattr(module, "CONFIG"):
        payload = getattr(module, "CONFIG")
    else:
        raise ValueError("Python config must define CONFIG dict or get_config()/load_config()")

    if isinstance(payload, DETMConfig):
        payload = payload.to_dict()
    if not isinstance(payload, dict):
        raise ValueError("Python config must return/contain a dict")
    return payload


def load_merged_payload(*, preset: str = "default", override_path: str | None = None) -> Dict[str, Any]:
    base = load_preset_payload(preset)
    override = load_override_payload(override_path)
    return _deep_merge(base, override)


def build_runtime_config(payload: Mapping[str, Any]) -> DETMConfig:
    # DETMConfig.from_dict ignores unknown keys, so we can pass the whole payload.
    return DETMConfig.from_dict(dict(payload))


def build_ui_overrides(ui_payload: Mapping[str, Any]) -> Dict[str, Any]:
    # Keep only keys that exist on UiRunSettings to avoid accidental typos.
    from detm_app.config.ui_models import UiRunSettings

    allowed = {f.name for f in fields(UiRunSettings)} - {"config"}
    clean: Dict[str, Any] = {}
    for key, value in ui_payload.items():
        if key in allowed:
            clean[key] = value
    return clean


__all__ = [
    "build_runtime_config",
    "build_ui_overrides",
    "load_merged_payload",
    "load_override_payload",
    "load_override_payload_py",
    "load_preset_payload",
]
