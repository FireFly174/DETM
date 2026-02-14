"""Compatibility aggregation for runtime subscribers API."""

from __future__ import annotations

from detm_app.runtime.subscribers.trace import (
    ArtifactWriter,
    FieldHistoryRecorder,
    JsonlTraceWriter,
    SystemTraceWriter,
    TraceRecorder,
)
from detm_app.runtime.subscribers.watch import WatchContractWriter, WatchTraceWriter
from detm_app.runtime.subscribers.commit import (
    CommitJsonlWriter,
    CommitValidationReporter,
    InvariantTickJsonlWriter,
)
from detm_app.runtime.subscribers.fabric import FabricHandshakeRecorder
from detm_app.runtime.subscribers.viz import VizStreamer

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
