"""Backward-compatible app-layer re-export for tick scheduler primitives (deprecated)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from detm.run._compat import load_export

if TYPE_CHECKING:
    from detm_app.scheduler import ScheduledItem, TickRunner, TickScheduler

__all__ = ["ScheduledItem", "TickRunner", "TickScheduler"]

_EXPORTS = {
    "ScheduledItem": ("detm_app.scheduler", "ScheduledItem"),
    "TickRunner": ("detm_app.scheduler", "TickRunner"),
    "TickScheduler": ("detm_app.scheduler", "TickScheduler"),
}


def __getattr__(name: str):
    target = _EXPORTS.get(str(name))
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    target_module, target_symbol = target
    return load_export(
        shim_module=__name__,
        symbol=str(name),
        target_module=str(target_module),
        target_symbol=str(target_symbol),
    )


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(__all__)))
