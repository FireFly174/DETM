"""Application-layer adapters for DETM orchestration.

This package is a migration shim for roadmap stage A: `detm_app` becomes the
entry point for app orchestration while preserving compatibility with `detm.run`.
"""

from __future__ import annotations

from detm_app.bus import Event, EventBus, EventHandler
from detm_app.coarsening import InvariantCoarsener, InvariantStreamSpec, parse_invariant_streams
from detm_app.scheduler import ScheduledItem, TickRunner, TickScheduler
from detm_app.session import DetmSession
from detm_app.cli import main as cli_main, run_headless
from detm_app.client import VizClient, VizDaemon, start_local_daemon
from detm_app.config_hints import load_tooltips_from_config_default
from detm_app.daemon import StatePacket, VizHub, run_daemon
from detm_app.napari_subscriber import main as napari_main, run_napari_subscriber
from detm_app.protocol import recv_msg, send_msg
from detm_app.subscriber import TcpVizSubscriber, VizPacket
from detm_app.tk_runner import DetmTkRunner, UiRunSettings, launch_tk_ui
from detm_app.tk_panel import DetmVizPanel, VizFrame
from detm_app.transport import (
    NullVizTransport,
    TcpVizTransport,
    VizTransport,
    clear_viz_endpoint_registry,
    load_viz_endpoint_registry,
    open_viz_transport,
    write_viz_endpoint_registry,
)
from detm_app.tooltips import Tooltip, attach_tooltip
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
    "DetmTkRunner",
    "UiRunSettings",
    "launch_tk_ui",
    "DetmVizPanel",
    "VizFrame",
    "load_tooltips_from_config_default",
    "Tooltip",
    "attach_tooltip",
    "cli_main",
    "run_headless",
    "VizClient",
    "VizDaemon",
    "start_local_daemon",
    "StatePacket",
    "VizHub",
    "run_daemon",
    "send_msg",
    "recv_msg",
    "TcpVizSubscriber",
    "VizPacket",
    "NullVizTransport",
    "TcpVizTransport",
    "VizTransport",
    "open_viz_transport",
    "load_viz_endpoint_registry",
    "write_viz_endpoint_registry",
    "clear_viz_endpoint_registry",
    "napari_main",
    "run_napari_subscriber",
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
