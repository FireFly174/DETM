"""Backward-compatible app-layer re-export for EventBus subscribers (deprecated)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from detm.run._compat import load_export

if TYPE_CHECKING:
    from detm_app.subscribers import (
        ArtifactWriter,
        CommitJsonlWriter,
        CommitValidationReporter,
        FabricHandshakeRecorder,
        FieldHistoryRecorder,
        InvariantTickJsonlWriter,
        JsonlTraceWriter,
        SystemTraceWriter,
        TraceRecorder,
        VizStreamer,
        WatchContractWriter,
        WatchTraceWriter,
    )

__all__ = [
    "ArtifactWriter",
    "CommitJsonlWriter",
    "CommitValidationReporter",
    "FabricHandshakeRecorder",
    "FieldHistoryRecorder",
    "InvariantTickJsonlWriter",
    "JsonlTraceWriter",
    "SystemTraceWriter",
    "TraceRecorder",
    "VizStreamer",
    "WatchContractWriter",
    "WatchTraceWriter",
]

_EXPORTS = {
    "ArtifactWriter": ("detm_app.subscribers", "ArtifactWriter"),
    "CommitJsonlWriter": ("detm_app.subscribers", "CommitJsonlWriter"),
    "CommitValidationReporter": ("detm_app.subscribers", "CommitValidationReporter"),
    "FabricHandshakeRecorder": ("detm_app.subscribers", "FabricHandshakeRecorder"),
    "FieldHistoryRecorder": ("detm_app.subscribers", "FieldHistoryRecorder"),
    "InvariantTickJsonlWriter": ("detm_app.subscribers", "InvariantTickJsonlWriter"),
    "JsonlTraceWriter": ("detm_app.subscribers", "JsonlTraceWriter"),
    "SystemTraceWriter": ("detm_app.subscribers", "SystemTraceWriter"),
    "TraceRecorder": ("detm_app.subscribers", "TraceRecorder"),
    "VizStreamer": ("detm_app.subscribers", "VizStreamer"),
    "WatchContractWriter": ("detm_app.subscribers", "WatchContractWriter"),
    "WatchTraceWriter": ("detm_app.subscribers", "WatchTraceWriter"),
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
