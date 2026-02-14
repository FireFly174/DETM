"""Settings application helpers for Tk settings flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detm_app.ui.tk.runner.flow.controls.model import TkControlVars
from detm_app.ui.tk.runner.flow.settings.runtime_config import build_runtime_config


def read_invariant_streams(*, controls: TkControlVars) -> str:
    return str(controls.invariant_streams_var.get() or "")


def apply_runtime_settings(*, settings: Any, runner: Any, controls: TkControlVars, reset: bool) -> None:
    settings.config = build_runtime_config(settings=settings, controls=controls)
    settings.seed = int(controls.seed_var.get())
    settings.influence_mode = str(controls.influence_mode_var.get()).strip() or "symbol"
    settings.symbol_id = controls.symbol_var.get()
    settings.amplitude = float(controls.amplitude_var.get())
    settings.influence_duration_steps = int(controls.duration_var.get())
    settings.joy_dx = float(controls.joy_dx_var.get())
    settings.joy_dy = float(controls.joy_dy_var.get())
    settings.patch_cx = int(controls.patch_cx_var.get())
    settings.patch_cy = int(controls.patch_cy_var.get())
    settings.patch_radius = int(controls.patch_radius_var.get())
    settings.source_x = int(controls.source_x_var.get())
    settings.source_y = int(controls.source_y_var.get())
    settings.sink_x = int(controls.sink_x_var.get())
    settings.sink_y = int(controls.sink_y_var.get())
    settings.source_value = float(controls.source_value_var.get())
    settings.sink_value = float(controls.sink_value_var.get())
    settings.ticks_per_step = int(controls.ticks_var.get())
    settings.tick_interval_ms = int(controls.interval_var.get())
    settings.record_dir = Path(controls.out_var.get()) if controls.record_enabled_var.get() else None
    settings.record_fields = bool(controls.fields_var.get())
    settings.invariant_streams = str(controls.invariant_streams_var.get()).strip()
    settings.viz_enabled = bool(controls.viz_enabled_var.get())
    settings.viz_transport = str(controls.viz_transport_var.get()).strip() or "embedded"
    settings.viz_host = str(controls.viz_host_var.get()).strip() or "127.0.0.1"
    settings.viz_port = int(controls.viz_port_var.get())
    settings.viz_connect = bool(controls.viz_connect_var.get()) and settings.viz_port > 0
    settings.viz_every_steps = int(controls.viz_every_var.get())
    runner.settings = settings
    if reset:
        runner.reset()
    runner._configure_recording()
    runner._configure_invariants()
    runner._configure_viz()


__all__ = ["apply_runtime_settings", "read_invariant_streams"]
