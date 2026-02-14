"""Execution loop helpers for headless runner."""

from __future__ import annotations

from detm.runtime.symbols import make_symbol
from detm_app.runner.headless.helpers import normalize_steps_mode


def execute_headless_steps(
    *,
    session,
    symbol_ids: list[str],
    steps: int,
    steps_mode: str,
) -> None:
    mode = normalize_steps_mode(steps_mode, default="per_symbol")
    if mode == "per_symbol":
        for sid in symbol_ids:
            session.step(make_symbol(sid), steps)
        return

    total_steps = max(0, int(steps))
    if len(symbol_ids) == 0:
        if total_steps > 0:
            session.step(None, total_steps)
        return

    for index in range(total_steps):
        sid = symbol_ids[index % len(symbol_ids)]
        session.step(make_symbol(sid), 1)


__all__ = ["execute_headless_steps"]
