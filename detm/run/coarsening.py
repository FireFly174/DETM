"""Backward-compatible app-layer re-export for coarsening primitives (deprecated)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from detm.run._compat import load_export

if TYPE_CHECKING:
    from detm_app.coarsening import InvariantCoarsener, InvariantStreamSpec, parse_invariant_streams

__all__ = ["InvariantCoarsener", "InvariantStreamSpec", "parse_invariant_streams"]

_EXPORTS = {
    "InvariantCoarsener": ("detm_app.coarsening", "InvariantCoarsener"),
    "InvariantStreamSpec": ("detm_app.coarsening", "InvariantStreamSpec"),
    "parse_invariant_streams": ("detm_app.coarsening", "parse_invariant_streams"),
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
