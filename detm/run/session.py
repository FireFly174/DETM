"""Backward-compatible app-layer re-export for DetmSession (deprecated)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from detm.run._compat import load_export

if TYPE_CHECKING:
    from detm_app.session import DetmSession

__all__ = ["DetmSession"]


def __getattr__(name: str):
    if str(name) != "DetmSession":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return load_export(
        shim_module=__name__,
        symbol="DetmSession",
        target_module="detm_app.session",
        target_symbol="DetmSession",
    )


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(__all__)))
