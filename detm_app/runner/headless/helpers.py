"""Utility helpers for headless runner CLI/runtime wiring."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from detm.runtime.symbols import list_symbols


def default_out_dir(out: str | None) -> Path:
    if out is not None:
        return Path(out)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("runs/out") / f"run_{stamp}"


def resolve_symbols(symbols: list[str] | None) -> list[str]:
    if symbols is None:
        return list_symbols()
    out: list[str] = []
    known = set(list_symbols())
    for sid in symbols:
        if sid in known:
            out.append(sid)
        else:
            raise SystemExit(f"Unknown symbol_id: {sid}. Known: {sorted(known)}")
    return out


def normalize_steps_mode(value: Any, *, default: str) -> str:
    raw = str(value if value is not None else default).strip().lower()
    aliases = {
        "total": "total",
        "global": "total",
        "overall": "total",
        "per_symbol": "per_symbol",
        "per-symbol": "per_symbol",
        "legacy": "per_symbol",
    }
    mode = aliases.get(raw, raw)
    if mode not in {"total", "per_symbol"}:
        raise SystemExit(f"Unsupported steps mode: {value!r}. Expected: total|per_symbol")
    return mode


def runner_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("runner", {})
    return raw if isinstance(raw, dict) else {}


def as_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        chunks = [c.strip() for c in value.split(",") if c.strip()]
        return chunks
    return None


def flatten_list_args(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    out: list[str] = []
    for raw in list(values):
        chunks = as_list(raw)
        if chunks:
            out.extend(chunks)
    return out


__all__ = [
    "as_list",
    "default_out_dir",
    "flatten_list_args",
    "normalize_steps_mode",
    "resolve_symbols",
    "runner_defaults",
]
