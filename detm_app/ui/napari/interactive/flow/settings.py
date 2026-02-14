#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Settings/apply helpers for napari interactive controller."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detm.runtime.config import DETMConfig
from detm_app.ui.napari.interactive.helpers import resolve_influence_policy as _resolve_influence_policy


def build_config_from_controls(controller: Any) -> DETMConfig:
    self = controller
    base = dict(self._settings.config.to_dict())
    dyn = dict(base.get("dynamics", {}))
    dyn.update(
        {
            "alpha": self._read_float(self._alpha, float(self._settings.config.dynamics.alpha)),
            "beta": self._read_float(self._beta, float(self._settings.config.dynamics.beta)),
            "kappa": self._read_float(self._kappa, float(self._settings.config.dynamics.kappa)),
            "gamma": self._read_float(self._gamma, float(self._settings.config.dynamics.gamma)),
            "lambda_t": self._read_float(self._lambda_t, float(self._settings.config.dynamics.lambda_t)),
        }
    )
    payload = {
        **base,
        "backend": self._read_text(self._backend, str(self._settings.config.backend)).strip()
        or str(self._settings.config.backend),
        "device": self._read_text(self._device, str(self._settings.config.device)).strip()
        or str(self._settings.config.device),
        "width": max(1, self._read_int(self._width, int(self._settings.config.width))),
        "height": max(1, self._read_int(self._height, int(self._settings.config.height))),
        "boundary": self._read_text(self._boundary, str(self._settings.config.boundary)).strip()
        or str(self._settings.config.boundary),
        "dynamics": dyn,
    }
    return DETMConfig.from_dict(payload)


def apply_settings(controller: Any, *, reset: bool) -> None:
    self = controller
    settings = self._settings
    settings.config = build_config_from_controls(self)
    settings.seed = max(0, self._read_int(self._seed, int(settings.seed)))
    settings.ticks_per_step = max(1, self._read_int(self._ticks, int(settings.ticks_per_step)))
    settings.tick_interval_ms = max(1, self._read_int(self._interval, int(settings.tick_interval_ms)))
    selected_mode = str(self._influence_mode.currentText()).strip() or "none"
    resolved_mode, resolved_duration = _resolve_influence_policy(
        policy=self._read_text(self._influence_policy, "off"),
        selected_mode=selected_mode,
        duration_steps=self._read_int(self._duration, int(settings.influence_duration_steps)),
    )
    settings.influence_mode = resolved_mode
    symbol = str(self._symbol.currentText()).strip()
    settings.symbol_id = "none" if symbol in {"", "(none)"} else symbol
    settings.amplitude = self._read_float(self._amplitude, float(settings.amplitude))
    settings.influence_duration_steps = max(0, int(resolved_duration))
    settings.joy_dx = self._read_float(self._joy_dx, float(settings.joy_dx)) / 100.0
    settings.joy_dy = self._read_float(self._joy_dy, float(settings.joy_dy)) / 100.0
    settings.patch_cx = self._read_int(self._patch_cx, int(settings.patch_cx))
    settings.patch_cy = self._read_int(self._patch_cy, int(settings.patch_cy))
    settings.patch_radius = max(0, self._read_int(self._patch_radius, int(settings.patch_radius)))
    settings.source_x = self._read_int(self._source_x, int(settings.source_x))
    settings.source_y = self._read_int(self._source_y, int(settings.source_y))
    settings.sink_x = self._read_int(self._sink_x, int(settings.sink_x))
    settings.sink_y = self._read_int(self._sink_y, int(settings.sink_y))
    settings.source_value = self._read_float(self._source_value, float(settings.source_value))
    settings.sink_value = self._read_float(self._sink_value, float(settings.sink_value))
    settings.record_dir = (
        Path(str(self._record_dir.text()).strip() or "runs/out/ui_run")
        if bool(self._record_enabled.isChecked())
        else None
    )
    settings.record_fields = bool(self._record_fields.isChecked())
    settings.invariant_streams = str(self._invariant_streams.text()).strip()
    settings.viz_enabled = False
    settings.viz_transport = "none"
    settings.viz_connect = False
    settings.viz_port = 0

    self._runner.settings = settings
    if reset:
        self._runner.reset()
    self._runner._configure_recording()
    self._runner._configure_invariants()
    self._runner._configure_viz()
    self._timer.setInterval(max(1, int(settings.tick_interval_ms)))
    self._autoscale = bool(self._autoscale_check.isChecked())


__all__ = ["apply_settings", "build_config_from_controls"]
