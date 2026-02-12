"""Backward-compatible app-layer re-export package.

`detm.run` is a deprecated compatibility facade; canonical orchestration
primitives are provided via `detm_app`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from detm.run._compat import load_export

if TYPE_CHECKING:
    from detm_app.bus import EventBus
    from detm_app.coarsening import InvariantCoarsener, InvariantStreamSpec
    from detm_app.scheduler import TickRunner, TickScheduler
    from detm_app.session import DetmSession

_EXPORTS = {
    "DetmSession": ("detm_app.session", "DetmSession"),
    "EventBus": ("detm_app.bus", "EventBus"),
    "InvariantCoarsener": ("detm_app.coarsening", "InvariantCoarsener"),
    "InvariantStreamSpec": ("detm_app.coarsening", "InvariantStreamSpec"),
    "TickRunner": ("detm_app.scheduler", "TickRunner"),
    "TickScheduler": ("detm_app.scheduler", "TickScheduler"),
}

__all__ = [
    "DetmSession",
    "EventBus",
    "InvariantCoarsener",
    "InvariantStreamSpec",
    "TickRunner",
    "TickScheduler",
]


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
