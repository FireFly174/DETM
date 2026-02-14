"""Control variable model for Tk runner launcher controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TkControlVars:
    backend_var: Any
    device_var: Any
    width_var: Any
    height_var: Any
    boundary_var: Any
    alpha_var: Any
    beta_var: Any
    kappa_var: Any
    gamma_var: Any
    lambda_t_var: Any
    seed_var: Any
    influence_mode_var: Any
    duration_var: Any
    symbol_var: Any
    amplitude_var: Any
    joy_dx_var: Any
    joy_dy_var: Any
    patch_cx_var: Any
    patch_cy_var: Any
    patch_radius_var: Any
    source_x_var: Any
    source_y_var: Any
    sink_x_var: Any
    sink_y_var: Any
    source_value_var: Any
    sink_value_var: Any
    ticks_var: Any
    interval_var: Any
    record_enabled_var: Any
    out_var: Any
    fields_var: Any
    invariant_streams_var: Any
    viz_enabled_var: Any
    viz_transport_var: Any
    viz_host_var: Any
    viz_port_var: Any
    viz_connect_var: Any
    viz_every_var: Any
    ui_mode_var: Any
    status_var: Any


__all__ = ["TkControlVars"]
