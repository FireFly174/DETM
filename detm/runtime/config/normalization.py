"""Normalization helpers for DETM runtime configuration."""

from __future__ import annotations

import re
from typing import Any


def normalize_artifact_storage_policy(raw: Any) -> dict[str, dict[str, dict[str, int]]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, dict[str, int]]] = {}
    for level_key, level_rules in raw.items():
        if not isinstance(level_rules, dict):
            continue
        level_name = str(level_key).strip()
        if not level_name:
            continue
        normalized_rules: dict[str, dict[str, int]] = {}
        for artifact_key, rule in level_rules.items():
            if not isinstance(rule, dict):
                continue
            artifact_name = str(artifact_key).strip()
            if not artifact_name:
                continue
            normalized_rules[artifact_name] = {
                "retention_window": max(0, int(rule.get("retention_window", 0))),
                "compaction_budget": max(0, int(rule.get("compaction_budget", 0))),
            }
        if normalized_rules:
            out[level_name] = normalized_rules
    return out


def level_fallback_chain(level: str) -> list[str]:
    raw = str(level).strip() or "L0"
    out: list[str] = []

    def _push(value: str) -> None:
        if value not in out:
            out.append(value)

    _push(raw)
    match = re.match(r"^[Ll](\d+)$", raw)
    if not match:
        return out

    idx = max(0, int(match.group(1)))
    canonical = f"L{idx}"
    _push(canonical)
    for parent in range(idx - 1, -1, -1):
        _push(f"L{parent}")
    return out


def normalize_pattern_reuse_scope(raw: Any) -> str:
    scope = str(raw).strip().lower()
    if scope in {"global", "portable", "strict"}:
        return scope
    return "portable"


__all__ = ["level_fallback_chain", "normalize_artifact_storage_policy", "normalize_pattern_reuse_scope"]
