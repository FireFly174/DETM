"""Shared configuration helpers for experiment scripts.

The helpers are intentionally lightweight: configuration files can be JSON or
YAML (when the optional dependency is available) and are merged with CLI
overrides by the calling script.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def load_structured_config(path: str | Path | None) -> dict[str, Any]:
    """Return a mapping loaded from ``path`` or an empty dict if ``None``."""

    if path is None:
        return {}

    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")

    if config_path.suffix.lower() in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise SystemExit("PyYAML is required for YAML configuration files") from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)

    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ValueError(f"Configuration at {config_path} must be a mapping")
    return dict(data)


def pick(config: Mapping[str, Any], cli_value: Any, key: str, default: Any) -> Any:
    """Resolve a single value with CLI override > config file > default."""

    if cli_value is not None:
        return cli_value
    return config.get(key, default)


__all__ = ["load_structured_config", "pick"]
