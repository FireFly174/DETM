"""Application-layer adapters for DETM orchestration.

`detm_app` is the canonical entry point for app orchestration.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "Event": ("detm_app.runtime.bus", "Event"),
    "EventBus": ("detm_app.runtime.bus", "EventBus"),
    "EventHandler": ("detm_app.runtime.bus", "EventHandler"),
    "InvariantCoarsener": ("detm_app.runtime.coarsening", "InvariantCoarsener"),
    "InvariantStreamSpec": ("detm_app.runtime.coarsening", "InvariantStreamSpec"),
    "parse_invariant_streams": ("detm_app.runtime.coarsening", "parse_invariant_streams"),
    "ScheduledItem": ("detm_app.runtime.scheduler", "ScheduledItem"),
    "TickRunner": ("detm_app.runtime.scheduler", "TickRunner"),
    "TickScheduler": ("detm_app.runtime.scheduler", "TickScheduler"),
    "DetmSession": ("detm_app.runtime.session", "DetmSession"),
    "cli_main": ("detm_app.runner.headless", "main"),
    "run_headless": ("detm_app.runner.headless", "run_headless"),
    "orchestrate_main": ("detm_app.runner.shell", "main"),
    "VizClient": ("detm_app.transport.client", "VizClient"),
    "VizDaemon": ("detm_app.transport.client", "VizDaemon"),
    "start_local_daemon": ("detm_app.transport.client", "start_local_daemon"),
    "load_tooltips_from_config_default": ("detm_app.config.tooltips", "load_tooltips_from_config_default"),
    "StatePacket": ("detm_app.transport.daemon", "StatePacket"),
    "VizHub": ("detm_app.transport.daemon", "VizHub"),
    "run_daemon": ("detm_app.transport.daemon", "run_daemon"),
    "napari_main": ("detm_app.ui.napari.subscriber", "main"),
    "run_napari_subscriber": ("detm_app.ui.napari.subscriber", "run_napari_subscriber"),
    "recv_msg": ("detm_app.transport.protocol", "recv_msg"),
    "send_msg": ("detm_app.transport.protocol", "send_msg"),
    "TcpVizSubscriber": ("detm_app.transport.subscriber", "TcpVizSubscriber"),
    "VizPacket": ("detm_app.transport.subscriber", "VizPacket"),
    "DetmTkRunner": ("detm_app.runtime.ui_runtime", "DetmTkRunner"),
    "UiRunSettings": ("detm_app.config.ui_models", "UiRunSettings"),
    "launch_tk_ui": ("detm_app.ui.tk.runner", "launch_tk_ui"),
    "DetmVizPanel": ("detm_app.ui.tk.panel", "DetmVizPanel"),
    "VizFrame": ("detm_app.ui.tk.panel", "VizFrame"),
    "NullVizTransport": ("detm_app.transport", "NullVizTransport"),
    "TcpVizTransport": ("detm_app.transport", "TcpVizTransport"),
    "VizTransport": ("detm_app.transport", "VizTransport"),
    "clear_viz_endpoint_registry": ("detm_app.transport", "clear_viz_endpoint_registry"),
    "load_viz_endpoint_registry": ("detm_app.transport", "load_viz_endpoint_registry"),
    "open_viz_transport": ("detm_app.transport", "open_viz_transport"),
    "write_viz_endpoint_registry": ("detm_app.transport", "write_viz_endpoint_registry"),
    "Tooltip": ("detm_app.ui.tk.tooltips", "Tooltip"),
    "attach_tooltip": ("detm_app.ui.tk.tooltips", "attach_tooltip"),
    "ArtifactWriter": ("detm_app.runtime.subscribers", "ArtifactWriter"),
    "CommitJsonlWriter": ("detm_app.runtime.subscribers", "CommitJsonlWriter"),
    "CommitValidationReporter": ("detm_app.runtime.subscribers", "CommitValidationReporter"),
    "FabricHandshakeRecorder": ("detm_app.runtime.subscribers", "FabricHandshakeRecorder"),
    "FieldHistoryRecorder": ("detm_app.runtime.subscribers", "FieldHistoryRecorder"),
    "InvariantTickJsonlWriter": ("detm_app.runtime.subscribers", "InvariantTickJsonlWriter"),
    "JsonlTraceWriter": ("detm_app.runtime.subscribers", "JsonlTraceWriter"),
    "OperatorDecisionWriter": ("detm_app.runtime.subscribers", "OperatorDecisionWriter"),
    "SystemTraceWriter": ("detm_app.runtime.subscribers", "SystemTraceWriter"),
    "TraceRecorder": ("detm_app.runtime.subscribers", "TraceRecorder"),
    "VizStreamer": ("detm_app.runtime.subscribers", "VizStreamer"),
    "WatchContractWriter": ("detm_app.runtime.subscribers", "WatchContractWriter"),
    "WatchTraceWriter": ("detm_app.runtime.subscribers", "WatchTraceWriter"),
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
