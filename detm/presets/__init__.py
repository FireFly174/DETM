"""Packaged presets for local runs.

Presets are kept inside the package so that running DETM does not require
creating external config files. CLI/UI entrypoints can still override values
from a user-provided JSON file.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Iterable

from detm.runtime.config import DETMConfig


def preset_names() -> Iterable[str]:
    root = resources.files(__package__)
    for entry in root.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            yield entry.name[: -len(".json")]


def load_preset_config(name: str = "default") -> DETMConfig:
    preset_path = resources.files(__package__) / f"{name}.json"
    payload = json.loads(preset_path.read_text(encoding="utf-8"))
    return DETMConfig.from_dict(payload)


__all__ = ["load_preset_config", "preset_names"]

