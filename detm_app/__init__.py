"""Application-layer adapters for DETM orchestration.

This package is a migration shim for roadmap stage A: `detm_app` becomes the
entry point for app orchestration while preserving compatibility with `detm.run`.
"""

from __future__ import annotations

from detm_app.bus import Event, EventBus, EventHandler
from detm_app.coarsening import InvariantCoarsener, InvariantStreamSpec, parse_invariant_streams
from detm_app.scheduler import ScheduledItem, TickRunner, TickScheduler
from detm_app.session import DetmSession
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
    "DetmSession",
    "Event",
    "EventBus",
    "EventHandler",
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
    "InvariantCoarsener",
    "InvariantStreamSpec",
    "parse_invariant_streams",
    "ScheduledItem",
    "TickRunner",
    "TickScheduler",
]
