"""Load UI tooltips from config templates.

User-facing hints live in `detm/presets/config.default.py` as `///` comments.
This module extracts those hints for any UI frontend (Tk, napari, etc.).
"""

from __future__ import annotations

import re
from importlib import resources
from typing import Dict


_LINE_RE = re.compile(
    r"""
    ^\s*
    (?P<q>["'])
    (?P<key>[^"']+)
    (?P=q)
    \s*:\s*
    .*?
    \#\s*
    (?P<opts>[^/]*?)
    \s*///\s*
    (?P<desc>.+?)
    \s*$
    """,
    re.VERBOSE,
)

_SECTION_RE = re.compile(r'^\s*["\'](?P<section>ui|runner|dynamics)["\']\s*:\s*\{\s*(?:#.*)?$')


def load_tooltips_from_config_default() -> Dict[str, str]:
    path = resources.files("detm.presets") / "config.default.py"
    text = path.read_text(encoding="utf-8")
    tips: Dict[str, str] = {}
    stack: list[tuple[str, int]] = []
    for line in text.splitlines():
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        # Pop sections when we leave their indentation level.
        if stripped.startswith("}"):
            while stack and indent <= stack[-1][1]:
                stack.pop()

        sec = _SECTION_RE.match(line)
        if sec:
            stack.append((sec.group("section"), indent))
            continue

        m = _LINE_RE.match(line)
        if not m:
            continue
        key = m.group("key").strip()
        desc = " ".join(m.group("desc").split())
        prefix = ".".join(s for (s, _i) in stack)
        full_key = f"{prefix}.{key}" if prefix else key
        tips[full_key] = desc
    return tips


__all__ = ["load_tooltips_from_config_default"]
