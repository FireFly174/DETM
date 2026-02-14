#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Napari interactive controls (Tk feature migration path).

This module runs DETM in-process and exposes runtime manipulation controls via
napari dock widgets (run/step/reset, influence parameters, config, recording).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from detm.runtime.config import DETMConfig
from detm.runtime.symbols import list_symbols
from detm_app.config.app_settings import build_runtime_config, build_ui_overrides, load_merged_payload
from detm_app.config.ui_models import UiRunSettings
from detm_app.config.tooltips import load_tooltips_from_config_default
from detm_app.runner.batch_service import (
    BatchRunHandle,
    BatchRunRequest,
    build_batch_start_message,
    parse_batch_symbols_csv,
    start_batch_run,
)
from detm_app.runtime.ui_runtime import DetmUiRunner
from detm_app.ui.napari.interactive.helpers import (
    build_quiver_vectors as _build_quiver_vectors,
    resolve_influence_policy as _resolve_influence_policy,
    to_float as _to_float,
    to_int as _to_int,
)
from detm_app.ui.napari.subscriber import _patch_six_meta_path_importer, state_to_layers


def _sanitize_ui_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(overrides)
    if "record_dir" in out:
        value = out.get("record_dir")
        out["record_dir"] = None if value in {None, ""} else Path(str(value))
    return out


def _build_interactive_settings(*, preset: str, override_path: str | None) -> UiRunSettings:
    payload = load_merged_payload(preset=str(preset), override_path=override_path)
    config = build_runtime_config(payload)
    ui_payload = payload.get("ui", {}) if isinstance(payload.get("ui"), dict) else {}
    overrides = _sanitize_ui_overrides(build_ui_overrides(ui_payload))

    settings = UiRunSettings(config=config)
    for key, value in overrides.items():
        setattr(settings, str(key), value)

    # Interactive napari mode renders state directly and does not need viz daemon.
    settings.viz_enabled = False
    settings.viz_transport = "none"
    settings.viz_connect = False
    settings.viz_port = 0
    return settings


def _parse_symbol_csv(text: str) -> list[str]:
    return parse_batch_symbols_csv(str(text or ""), available_symbols=list_symbols())


class _InteractiveDockController:
    def __init__(self, *, viewer: Any, runner: DetmUiRunner, title: str, autoscale: bool) -> None:
        from qtpy import QtCore, QtWidgets

        self._QtCore = QtCore
        self._QtWidgets = QtWidgets
        self._viewer = viewer
        self._runner = runner
        self._settings = runner.settings
        self._running = False
        self._autoscale = bool(autoscale)
        self._field_layer_name = "field"
        self._quiver_layer_name = "quiver"
        self._colormap_map = {"gray": "gray", "heat": "inferno"}

        self._timer = QtCore.QTimer()
        self._timer.setInterval(max(1, int(self._settings.tick_interval_ms)))
        self._timer.timeout.connect(self._on_tick)
        self._batch_poll_timer = QtCore.QTimer()
        self._batch_poll_timer.setInterval(75)
        self._batch_poll_timer.timeout.connect(self._drain_batch_queue)
        self._batch_running = False
        self._batch_handle: BatchRunHandle | None = None
        self._closed = False
        self._closing = False

        self._root = QtWidgets.QWidget()
        self._layout = QtWidgets.QVBoxLayout(self._root)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(6)

        self._status = QtWidgets.QLabel("status: ready")
        self._status.setWordWrap(True)
        self._layout.addWidget(self._status)

        self._build_controls()
        self._build_buttons()
        self._install_shortcuts()
        self._on_mode_change()
        self._render(force_autoscale=True)
        self._viewer.window.add_dock_widget(self._root, name=str(title), area="right")

    def close(self) -> None:
        if self._closed:
            return
        self._closing = True
        self._timer.stop()
        self._batch_poll_timer.stop()
        if self._batch_handle is not None:
            self._batch_handle.cancel()
        self._runner.close()
        self._batch_handle = None
        self._closed = True

    def _line(
        self,
        *,
        label: str,
        value: str,
        parent_layout: Any | None = None,
        tooltip: str = "",
    ) -> tuple[Any, Any]:
        layout = self._layout if parent_layout is None else parent_layout
        row = self._QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        lbl = self._QtWidgets.QLabel(str(label))
        edit = self._QtWidgets.QLineEdit(str(value))
        if tooltip:
            lbl.setToolTip(str(tooltip))
            edit.setToolTip(str(tooltip))
        row.addWidget(lbl)
        row.addWidget(edit)
        layout.addLayout(row)
        return lbl, edit

    def _read_text(self, widget: Any, default: str = "") -> str:
        if hasattr(widget, "text"):
            try:
                return str(widget.text())
            except Exception:
                return str(default)
        if hasattr(widget, "currentText"):
            try:
                return str(widget.currentText())
            except Exception:
                return str(default)
        return str(default)

    def _read_int(self, widget: Any, default: int) -> int:
        if hasattr(widget, "value"):
            try:
                return int(widget.value())
            except Exception:
                return int(default)
        return _to_int(self._read_text(widget, str(default)), default)

    def _read_float(self, widget: Any, default: float) -> float:
        if hasattr(widget, "value"):
            try:
                return float(widget.value())
            except Exception:
                return float(default)
        return _to_float(self._read_text(widget, str(default)), default)

    def _layer_by_name(self, name: str) -> Any | None:
        try:
            if name in self._viewer.layers:
                return self._viewer.layers[name]
        except Exception:
            return None
        return None

    def _build_controls(self) -> None:
        QtWidgets = self._QtWidgets
        QtCore = self._QtCore
        from qtpy import QtGui
        settings = self._settings
        cfg = settings.config
        tips = load_tooltips_from_config_default()

        self._toolbox = QtWidgets.QToolBox()
        self._layout.addWidget(self._toolbox, 1)

        # View / Run
        page_view = QtWidgets.QWidget()
        lay_view = QtWidgets.QVBoxLayout(page_view)
        lay_view.setContentsMargins(6, 6, 6, 6)
        self._mode_combo = QtWidgets.QComboBox()
        self._mode_combo.addItems(["interactive", "batch"])
        self._mode_combo.setCurrentText("interactive")
        self._mode_combo.currentTextChanged.connect(self._on_mode_change)
        row_mode = QtWidgets.QHBoxLayout()
        row_mode.addWidget(QtWidgets.QLabel("mode"))
        row_mode.addWidget(self._mode_combo)
        lay_view.addLayout(row_mode)

        self._field_combo = QtWidgets.QComboBox()
        self._field_combo.addItems(["energy", "entropy", "internal_time"])
        self._field_combo.setCurrentText("energy")
        row_field = QtWidgets.QHBoxLayout()
        row_field.addWidget(QtWidgets.QLabel("field"))
        row_field.addWidget(self._field_combo)
        lay_view.addLayout(row_field)

        self._cmap_combo = QtWidgets.QComboBox()
        self._cmap_combo.addItems(["heat", "gray"])
        self._cmap_combo.setCurrentText("heat")
        row_cmap = QtWidgets.QHBoxLayout()
        row_cmap.addWidget(QtWidgets.QLabel("cmap"))
        row_cmap.addWidget(self._cmap_combo)
        lay_view.addLayout(row_cmap)

        self._quiver_enabled = QtWidgets.QCheckBox("quiver")
        self._quiver_enabled.setChecked(True)
        lay_view.addWidget(self._quiver_enabled)
        self._quiver_step = QtWidgets.QSpinBox()
        self._quiver_step.setRange(1, 32)
        self._quiver_step.setValue(2)
        row_qs = QtWidgets.QHBoxLayout()
        row_qs.addWidget(QtWidgets.QLabel("quiver_step"))
        row_qs.addWidget(self._quiver_step)
        lay_view.addLayout(row_qs)
        self._quiver_scale = QtWidgets.QDoubleSpinBox()
        self._quiver_scale.setRange(0.0, 2.0)
        self._quiver_scale.setSingleStep(0.05)
        self._quiver_scale.setValue(0.8)
        row_qc = QtWidgets.QHBoxLayout()
        row_qc.addWidget(QtWidgets.QLabel("quiver_scale"))
        row_qc.addWidget(self._quiver_scale)
        lay_view.addLayout(row_qc)

        self._ticks = QtWidgets.QSpinBox()
        self._ticks.setRange(1, 5000)
        self._ticks.setValue(int(settings.ticks_per_step))
        row_ticks = QtWidgets.QHBoxLayout()
        row_ticks.addWidget(QtWidgets.QLabel("ticks_per_step"))
        row_ticks.addWidget(self._ticks)
        lay_view.addLayout(row_ticks)

        self._interval = QtWidgets.QSpinBox()
        self._interval.setRange(1, 10000)
        self._interval.setValue(int(settings.tick_interval_ms))
        row_interval = QtWidgets.QHBoxLayout()
        row_interval.addWidget(QtWidgets.QLabel("tick_interval_ms"))
        row_interval.addWidget(self._interval)
        lay_view.addLayout(row_interval)

        self._seed = QtWidgets.QSpinBox()
        self._seed.setRange(0, 1_000_000_000)
        self._seed.setValue(int(settings.seed))
        row_seed = QtWidgets.QHBoxLayout()
        row_seed.addWidget(QtWidgets.QLabel("seed"))
        row_seed.addWidget(self._seed)
        lay_view.addLayout(row_seed)

        self._autoscale_check = QtWidgets.QCheckBox("autoscale")
        self._autoscale_check.setChecked(bool(self._autoscale))
        lay_view.addWidget(self._autoscale_check)
        lay_view.addStretch(1)
        self._toolbox.addItem(page_view, "View & Run")

        # Runtime
        page_runtime = QtWidgets.QWidget()
        lay_runtime = QtWidgets.QVBoxLayout(page_runtime)
        lay_runtime.setContentsMargins(6, 6, 6, 6)
        self._backend = QtWidgets.QComboBox()
        self._backend.addItems(["torch", "numpy"])
        self._backend.setCurrentText(str(cfg.backend))
        row_backend = QtWidgets.QHBoxLayout()
        row_backend.addWidget(QtWidgets.QLabel("backend"))
        row_backend.addWidget(self._backend)
        lay_runtime.addLayout(row_backend)
        _, self._device = self._line(label="device", value=str(cfg.device), parent_layout=lay_runtime, tooltip=tips.get("device", ""))
        self._width = QtWidgets.QSpinBox()
        self._width.setRange(4, 512)
        self._width.setValue(int(cfg.width))
        self._width.valueChanged.connect(self._sync_geometry_bounds)
        row_width = QtWidgets.QHBoxLayout()
        row_width.addWidget(QtWidgets.QLabel("width"))
        row_width.addWidget(self._width)
        lay_runtime.addLayout(row_width)
        self._height = QtWidgets.QSpinBox()
        self._height.setRange(4, 512)
        self._height.setValue(int(cfg.height))
        self._height.valueChanged.connect(self._sync_geometry_bounds)
        row_height = QtWidgets.QHBoxLayout()
        row_height.addWidget(QtWidgets.QLabel("height"))
        row_height.addWidget(self._height)
        lay_runtime.addLayout(row_height)
        self._boundary = QtWidgets.QComboBox()
        self._boundary.addItems(["periodic", "open"])
        self._boundary.setCurrentText(str(cfg.boundary))
        row_boundary = QtWidgets.QHBoxLayout()
        row_boundary.addWidget(QtWidgets.QLabel("boundary"))
        row_boundary.addWidget(self._boundary)
        lay_runtime.addLayout(row_boundary)
        self._alpha = QtWidgets.QDoubleSpinBox(); self._alpha.setRange(-10.0, 10.0); self._alpha.setDecimals(4); self._alpha.setValue(float(cfg.dynamics.alpha))
        self._beta = QtWidgets.QDoubleSpinBox(); self._beta.setRange(-10.0, 10.0); self._beta.setDecimals(4); self._beta.setValue(float(cfg.dynamics.beta))
        self._kappa = QtWidgets.QDoubleSpinBox(); self._kappa.setRange(-10.0, 10.0); self._kappa.setDecimals(4); self._kappa.setValue(float(cfg.dynamics.kappa))
        self._gamma = QtWidgets.QDoubleSpinBox(); self._gamma.setRange(-10.0, 10.0); self._gamma.setDecimals(4); self._gamma.setValue(float(cfg.dynamics.gamma))
        self._lambda_t = QtWidgets.QDoubleSpinBox(); self._lambda_t.setRange(-10.0, 10.0); self._lambda_t.setDecimals(4); self._lambda_t.setValue(float(cfg.dynamics.lambda_t))
        for name, widget, tip_key in [
            ("alpha", self._alpha, "dynamics.alpha"),
            ("beta", self._beta, "dynamics.beta"),
            ("kappa", self._kappa, "dynamics.kappa"),
            ("gamma", self._gamma, "dynamics.gamma"),
            ("lambda_t", self._lambda_t, "dynamics.lambda_t"),
        ]:
            row = QtWidgets.QHBoxLayout()
            lbl = QtWidgets.QLabel(name); lbl.setToolTip(tips.get(tip_key, ""))
            widget.setToolTip(tips.get(tip_key, ""))
            row.addWidget(lbl); row.addWidget(widget); lay_runtime.addLayout(row)
        lay_runtime.addStretch(1)
        self._toolbox.addItem(page_runtime, "Runtime")

        # Influence
        page_influence = QtWidgets.QWidget()
        lay_influence = QtWidgets.QVBoxLayout(page_influence)
        lay_influence.setContentsMargins(6, 6, 6, 6)
        self._influence_policy = QtWidgets.QComboBox()
        self._influence_policy.addItems(["off", "sustain", "pulse"])
        self._influence_policy.setCurrentText("off")
        self._influence_policy.currentTextChanged.connect(self._on_influence_policy_change)
        row_pol = QtWidgets.QHBoxLayout(); row_pol.addWidget(QtWidgets.QLabel("influence_policy")); row_pol.addWidget(self._influence_policy); lay_influence.addLayout(row_pol)
        self._influence_mode = QtWidgets.QComboBox()
        self._influence_mode.addItems(["symbol", "joystick_field", "joystick_patch", "source_sink", "none"])
        self._influence_mode.setCurrentText(str(settings.influence_mode or "none"))
        self._influence_mode.currentTextChanged.connect(self._on_influence_mode_change)
        row_mode_inf = QtWidgets.QHBoxLayout(); row_mode_inf.addWidget(QtWidgets.QLabel("influence_mode")); row_mode_inf.addWidget(self._influence_mode); lay_influence.addLayout(row_mode_inf)

        self._amplitude = QtWidgets.QDoubleSpinBox()
        self._amplitude.setRange(0.0, 2.0)
        self._amplitude.setSingleStep(0.01)
        self._amplitude.setValue(float(settings.amplitude))
        row_amp = QtWidgets.QHBoxLayout(); row_amp.addWidget(QtWidgets.QLabel("amplitude")); row_amp.addWidget(self._amplitude); lay_influence.addLayout(row_amp)

        self._duration = QtWidgets.QSpinBox()
        self._duration.setRange(0, 10_000)
        self._duration.setValue(int(settings.influence_duration_steps))
        row_dur = QtWidgets.QHBoxLayout(); row_dur.addWidget(QtWidgets.QLabel("influence_duration_steps")); row_dur.addWidget(self._duration); lay_influence.addLayout(row_dur)

        self._symbol_group = QtWidgets.QGroupBox("Symbol settings")
        symbol_layout = QtWidgets.QVBoxLayout(self._symbol_group)
        self._symbol = QtWidgets.QComboBox()
        self._symbol.addItems(["(none)", *list_symbols()])
        current_symbol = str(settings.symbol_id or "(none)")
        if current_symbol not in {self._symbol.itemText(i) for i in range(self._symbol.count())}:
            current_symbol = "(none)"
        self._symbol.setCurrentText(current_symbol)
        row_symbol = QtWidgets.QHBoxLayout()
        row_symbol.addWidget(QtWidgets.QLabel("symbol_id"))
        row_symbol.addWidget(self._symbol)
        symbol_layout.addLayout(row_symbol)
        lay_influence.addWidget(self._symbol_group)

        self._joystick_group = QtWidgets.QGroupBox("Joystick field")
        joystick_layout = QtWidgets.QVBoxLayout(self._joystick_group)
        self._joy_dx = QtWidgets.QSlider(self._QtCore.Qt.Horizontal)
        self._joy_dx.setRange(-100, 100)
        self._joy_dx.setValue(int(round(float(settings.joy_dx) * 100.0)))
        self._joy_dy = QtWidgets.QSlider(self._QtCore.Qt.Horizontal)
        self._joy_dy.setRange(-100, 100)
        self._joy_dy.setValue(int(round(float(settings.joy_dy) * 100.0)))
        row_dx = QtWidgets.QHBoxLayout(); row_dx.addWidget(QtWidgets.QLabel("joy_dx")); row_dx.addWidget(self._joy_dx)
        row_dy = QtWidgets.QHBoxLayout(); row_dy.addWidget(QtWidgets.QLabel("joy_dy")); row_dy.addWidget(self._joy_dy)
        joystick_layout.addLayout(row_dx)
        joystick_layout.addLayout(row_dy)

        class _JoystickPad(QtWidgets.QWidget):
            def __init__(self, *, on_change: Any, dx: int, dy: int) -> None:
                super().__init__()
                self.setMinimumSize(120, 120)
                self._on_change = on_change
                self._dx = int(max(-100, min(100, dx)))
                self._dy = int(max(-100, min(100, dy)))
                self._dragging = False

            def set_values(self, *, dx: int, dy: int, emit: bool = False) -> None:
                self._dx = int(max(-100, min(100, dx)))
                self._dy = int(max(-100, min(100, dy)))
                self.update()
                if emit:
                    self._on_change(self._dx, self._dy)

            def _update_from_pos(self, pos: Any) -> None:
                w = max(1, int(self.width()))
                h = max(1, int(self.height()))
                cx = 0.5 * float(w)
                cy = 0.5 * float(h)
                r = 0.45 * float(min(w, h))
                px = float(pos.x()) - cx
                py = float(pos.y()) - cy
                if r <= 1e-6:
                    return
                nx = px / r
                ny = -py / r
                d = float((nx * nx + ny * ny) ** 0.5)
                if d > 1.0:
                    nx /= d
                    ny /= d
                self.set_values(dx=int(round(nx * 100.0)), dy=int(round(ny * 100.0)), emit=True)

            def mousePressEvent(self, event: Any) -> None:
                if event.button() == QtCore.Qt.LeftButton:
                    self._dragging = True
                    self._update_from_pos(event.position() if hasattr(event, "position") else event.pos())
                    event.accept()
                    return
                super().mousePressEvent(event)

            def mouseMoveEvent(self, event: Any) -> None:
                if self._dragging:
                    self._update_from_pos(event.position() if hasattr(event, "position") else event.pos())
                    event.accept()
                    return
                super().mouseMoveEvent(event)

            def mouseReleaseEvent(self, event: Any) -> None:
                if event.button() == QtCore.Qt.LeftButton:
                    self._dragging = False
                    event.accept()
                    return
                super().mouseReleaseEvent(event)

            def paintEvent(self, _event: Any) -> None:
                p = QtGui.QPainter(self)
                p.setRenderHint(QtGui.QPainter.Antialiasing, True)
                w = float(self.width())
                h = float(self.height())
                cx = 0.5 * w
                cy = 0.5 * h
                r = 0.45 * min(w, h)
                p.fillRect(self.rect(), QtGui.QColor("#1b1f2a"))
                p.setPen(QtGui.QPen(QtGui.QColor("#6f7787"), 1))
                p.drawEllipse(QtCore.QPointF(cx, cy), r, r)
                p.drawLine(QtCore.QPointF(cx - r, cy), QtCore.QPointF(cx + r, cy))
                p.drawLine(QtCore.QPointF(cx, cy - r), QtCore.QPointF(cx, cy + r))
                kx = cx + (float(self._dx) / 100.0) * r
                ky = cy - (float(self._dy) / 100.0) * r
                p.setPen(QtGui.QPen(QtGui.QColor("#f3f3f3"), 1))
                p.setBrush(QtGui.QBrush(QtGui.QColor("#ffd84d")))
                p.drawEllipse(QtCore.QPointF(kx, ky), 6.0, 6.0)
                p.end()

        self._joy_sync = False

        def _on_pad_change(dx: int, dy: int) -> None:
            if self._joy_sync:
                return
            self._joy_sync = True
            self._joy_dx.setValue(int(dx))
            self._joy_dy.setValue(int(dy))
            self._joy_sync = False

        self._joystick_pad = _JoystickPad(
            on_change=_on_pad_change,
            dx=int(self._joy_dx.value()),
            dy=int(self._joy_dy.value()),
        )
        joystick_layout.addWidget(self._joystick_pad)

        def _sync_pad_from_sliders(_value: int = 0) -> None:
            if self._joy_sync:
                return
            self._joy_sync = True
            self._joystick_pad.set_values(dx=int(self._joy_dx.value()), dy=int(self._joy_dy.value()), emit=False)
            self._joy_sync = False

        self._joy_dx.valueChanged.connect(_sync_pad_from_sliders)
        self._joy_dy.valueChanged.connect(_sync_pad_from_sliders)
        joy_btn_row = QtWidgets.QHBoxLayout()
        joy_center_btn = QtWidgets.QPushButton("Center joystick")
        joy_center_btn.clicked.connect(lambda: self._joystick_pad.set_values(dx=0, dy=0, emit=True))
        joy_btn_row.addWidget(joy_center_btn)
        joystick_layout.addLayout(joy_btn_row)
        lay_influence.addWidget(self._joystick_group)

        self._patch_group = QtWidgets.QGroupBox("Joystick patch")
        patch_layout = QtWidgets.QVBoxLayout(self._patch_group)
        self._patch_cx = QtWidgets.QSpinBox(); self._patch_cx.setRange(0, max(0, int(cfg.width)-1)); self._patch_cx.setValue(int(settings.patch_cx))
        self._patch_cy = QtWidgets.QSpinBox(); self._patch_cy.setRange(0, max(0, int(cfg.height)-1)); self._patch_cy.setValue(int(settings.patch_cy))
        self._patch_radius = QtWidgets.QSpinBox(); self._patch_radius.setRange(0, max(1, max(int(cfg.width), int(cfg.height)))); self._patch_radius.setValue(int(settings.patch_radius))
        for name, widget in [("patch_cx", self._patch_cx), ("patch_cy", self._patch_cy), ("patch_radius", self._patch_radius)]:
            row = QtWidgets.QHBoxLayout(); row.addWidget(QtWidgets.QLabel(name)); row.addWidget(widget); patch_layout.addLayout(row)
        lay_influence.addWidget(self._patch_group)

        self._source_sink_group = QtWidgets.QGroupBox("Source/Sink")
        source_sink_layout = QtWidgets.QVBoxLayout(self._source_sink_group)
        self._source_x = QtWidgets.QSpinBox(); self._source_x.setRange(0, max(0, int(cfg.width)-1)); self._source_x.setValue(int(settings.source_x))
        self._source_y = QtWidgets.QSpinBox(); self._source_y.setRange(0, max(0, int(cfg.height)-1)); self._source_y.setValue(int(settings.source_y))
        self._sink_x = QtWidgets.QSpinBox(); self._sink_x.setRange(0, max(0, int(cfg.width)-1)); self._sink_x.setValue(int(settings.sink_x))
        self._sink_y = QtWidgets.QSpinBox(); self._sink_y.setRange(0, max(0, int(cfg.height)-1)); self._sink_y.setValue(int(settings.sink_y))
        for name, widget in [("source_x", self._source_x), ("source_y", self._source_y), ("sink_x", self._sink_x), ("sink_y", self._sink_y)]:
            row = QtWidgets.QHBoxLayout(); row.addWidget(QtWidgets.QLabel(name)); row.addWidget(widget); source_sink_layout.addLayout(row)
        self._source_value = QtWidgets.QDoubleSpinBox(); self._source_value.setRange(0.0, 1.0); self._source_value.setSingleStep(0.01); self._source_value.setValue(float(settings.source_value))
        self._sink_value = QtWidgets.QDoubleSpinBox(); self._sink_value.setRange(0.0, 1.0); self._sink_value.setSingleStep(0.01); self._sink_value.setValue(float(settings.sink_value))
        row_sv = QtWidgets.QHBoxLayout(); row_sv.addWidget(QtWidgets.QLabel("source_value")); row_sv.addWidget(self._source_value)
        row_tv = QtWidgets.QHBoxLayout(); row_tv.addWidget(QtWidgets.QLabel("sink_value")); row_tv.addWidget(self._sink_value)
        source_sink_layout.addLayout(row_sv)
        source_sink_layout.addLayout(row_tv)
        lay_influence.addWidget(self._source_sink_group)
        lay_influence.addStretch(1)
        self._toolbox.addItem(page_influence, "Influence")

        # Recording
        page_recording = QtWidgets.QWidget()
        lay_recording = QtWidgets.QVBoxLayout(page_recording)
        lay_recording.setContentsMargins(6, 6, 6, 6)
        self._record_enabled = QtWidgets.QCheckBox("record_trace")
        self._record_enabled.setChecked(bool(settings.record_dir is not None))
        lay_recording.addWidget(self._record_enabled)
        _, self._record_dir = self._line(
            label="record_dir",
            value=str(settings.record_dir) if settings.record_dir is not None else "runs/out/ui_run",
            parent_layout=lay_recording,
            tooltip=tips.get("ui.record_dir", ""),
        )
        self._record_fields = QtWidgets.QCheckBox("record_fields_hist_npz")
        self._record_fields.setChecked(bool(settings.record_fields))
        lay_recording.addWidget(self._record_fields)
        _, self._invariant_streams = self._line(
            label="invariant_streams",
            value=str(settings.invariant_streams or ""),
            parent_layout=lay_recording,
            tooltip=tips.get("ui.invariant_streams", ""),
        )
        lay_recording.addStretch(1)
        self._toolbox.addItem(page_recording, "Recording")

        # Batch
        page_batch = QtWidgets.QWidget()
        self._batch_layout = QtWidgets.QVBoxLayout(page_batch)
        self._batch_layout.setContentsMargins(6, 6, 6, 6)

        def _batch_line(label: str, value: str) -> Any:
            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            lbl = QtWidgets.QLabel(str(label))
            edit = QtWidgets.QLineEdit(str(value))
            row.addWidget(lbl)
            row.addWidget(edit)
            self._batch_layout.addLayout(row)
            return edit

        self._batch_n = _batch_line("batch_n", "10")
        self._batch_seed0 = _batch_line("batch_seed0", "0")
        self._batch_steps = _batch_line("batch_steps", "4")
        self._batch_symbols = _batch_line("batch_symbols_csv", "")
        self._batch_out = _batch_line("batch_out_dir", "runs/out/batch_ui")
        self._batch_fields_every = _batch_line("batch_fields_every", "1")
        self._batch_record_fields = QtWidgets.QCheckBox("batch_record_fields_npz")
        self._batch_record_fields.setChecked(False)
        self._batch_layout.addWidget(self._batch_record_fields)
        self._batch_log = QtWidgets.QTextEdit()
        self._batch_log.setReadOnly(True)
        self._batch_log.setMinimumHeight(140)
        self._batch_layout.addWidget(self._batch_log)
        self._batch_layout.addStretch(1)
        self._batch_page_index = self._toolbox.addItem(page_batch, "Batch")

        self._on_influence_mode_change(self._influence_mode.currentText())
        self._on_influence_policy_change(self._influence_policy.currentText())

    def _sync_geometry_bounds(self, *_args: object) -> None:
        width = max(1, self._read_int(self._width, int(self._settings.config.width)))
        height = max(1, self._read_int(self._height, int(self._settings.config.height)))
        self._patch_cx.setMaximum(max(0, width - 1))
        self._patch_cy.setMaximum(max(0, height - 1))
        self._source_x.setMaximum(max(0, width - 1))
        self._sink_x.setMaximum(max(0, width - 1))
        self._source_y.setMaximum(max(0, height - 1))
        self._sink_y.setMaximum(max(0, height - 1))
        self._patch_radius.setMaximum(max(1, max(width, height)))

    def _on_influence_mode_change(self, mode: str) -> None:
        mode_name = str(mode or "").strip().lower()
        symbol_mode = mode_name == "symbol"
        joystick_mode = mode_name == "joystick_field"
        patch_mode = mode_name == "joystick_patch"
        source_sink_mode = mode_name == "source_sink"
        self._symbol_group.setVisible(symbol_mode)
        self._joystick_group.setVisible(joystick_mode)
        self._patch_group.setVisible(patch_mode)
        self._source_sink_group.setVisible(source_sink_mode)

    def _on_influence_policy_change(self, policy: str) -> None:
        mode = str(policy or "").strip().lower()
        self._duration.setEnabled(mode == "pulse")

    def _build_buttons(self) -> None:
        QtWidgets = self._QtWidgets
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self._btn_reset = QtWidgets.QPushButton("Reset")
        self._btn_step = QtWidgets.QPushButton("Step")
        self._btn_run = QtWidgets.QPushButton("Run")
        self._btn_apply = QtWidgets.QPushButton("Apply")
        self._btn_batch = QtWidgets.QPushButton("Run batch")

        self._btn_reset.clicked.connect(self._on_reset)
        self._btn_step.clicked.connect(self._on_step)
        self._btn_run.clicked.connect(self._on_run_toggle)
        self._btn_apply.clicked.connect(self._on_apply)
        self._btn_batch.clicked.connect(self._on_batch_toggle)

        row.addWidget(self._btn_reset)
        row.addWidget(self._btn_step)
        row.addWidget(self._btn_run)
        row.addWidget(self._btn_apply)
        row.addWidget(self._btn_batch)
        self._layout.addLayout(row)

    def _install_shortcuts(self) -> None:
        from qtpy import QtGui, QtWidgets

        def _bind(seq: str, callback: Any) -> None:
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(seq), self._root)
            shortcut.activated.connect(callback)

        _bind("Space", self._on_run_toggle)
        _bind("N", self._on_step)
        _bind("R", self._on_reset)

    def _build_config_from_controls(self) -> DETMConfig:
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

    def _apply_settings(self, *, reset: bool) -> None:
        settings = self._settings
        settings.config = self._build_config_from_controls()
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

    def _ensure_field_layer(self, field: np.ndarray) -> Any:
        field_layer = self._layer_by_name(self._field_layer_name)
        if field_layer is None:
            field_layer = self._viewer.add_image(field, name=self._field_layer_name)
        else:
            field_layer.data = field
        cmap = self._colormap_map.get(str(self._cmap_combo.currentText()).strip().lower(), "inferno")
        try:
            field_layer.colormap = cmap
        except Exception:
            pass
        if bool(self._autoscale):
            vmin = float(np.nanmin(field)) if field.size else 0.0
            vmax = float(np.nanmax(field)) if field.size else 0.0
            if np.isfinite(vmin) and np.isfinite(vmax) and vmin < vmax:
                field_layer.contrast_limits = (vmin, vmax)
        return field_layer

    def _render(self, *, force_autoscale: bool = False) -> None:
        state = self._runner.state
        layers = state_to_layers(state)
        field_name = str(self._field_combo.currentText()).strip().lower() or "energy"
        field = np.asarray(layers.get(field_name, layers["energy"]), dtype=np.float32)
        if force_autoscale:
            self._autoscale = True
        self._ensure_field_layer(field)
        if force_autoscale:
            self._autoscale = bool(self._autoscale_check.isChecked())

        if bool(self._quiver_enabled.isChecked()):
            vectors = _build_quiver_vectors(
                field,
                step=max(1, self._read_int(self._quiver_step, 2)),
                scale=max(0.0, self._read_float(self._quiver_scale, 0.8)),
            )
            layer = self._layer_by_name(self._quiver_layer_name)
            if layer is None:
                self._viewer.add_vectors(
                    vectors,
                    name=self._quiver_layer_name,
                    edge_color="cyan",
                    edge_width=0.6,
                )
            else:
                layer.data = vectors
        else:
            if self._layer_by_name(self._quiver_layer_name) is not None:
                try:
                    self._viewer.layers.remove(self._quiver_layer_name)
                except Exception:
                    try:
                        del self._viewer.layers[self._quiver_layer_name]
                    except Exception:
                        pass

        signature = list(self._runner.last_observables or [])
        dyn = self._settings.config.dynamics
        self._status.setText(
            "tick="
            + str(int(state.step_count))
            + " sig0..3="
            + str(signature[:4])
            + " backend="
            + f"{self._settings.config.backend}/{self._settings.config.device}"
            + " boundary="
            + str(self._settings.config.boundary)
            + " a,b,k,g,t="
            + f"[{dyn.alpha:.3g},{dyn.beta:.3g},{dyn.kappa:.3g},{dyn.gamma:.3g},{dyn.lambda_t:.3g}]"
        )

    def _on_tick(self) -> None:
        if self._closing or (not bool(self._running)):
            return
        self._runner.step_once()
        self._render()

    def _mode_is_batch(self) -> bool:
        return str(self._mode_combo.currentText()).strip().lower() == "batch"

    def _on_mode_change(self, *_args: object) -> None:
        batch_mode = self._mode_is_batch()
        if batch_mode and self._running:
            self._running = False
            self._timer.stop()
            self._btn_run.setText("Run")
        self._btn_reset.setEnabled(not batch_mode)
        self._btn_step.setEnabled(not batch_mode)
        self._btn_run.setEnabled(not batch_mode)
        self._btn_run.setText("Run")
        self._btn_batch.setVisible(batch_mode)
        try:
            self._toolbox.setItemEnabled(int(self._batch_page_index), bool(batch_mode))
            if batch_mode:
                self._toolbox.setCurrentIndex(int(self._batch_page_index))
        except Exception:
            pass
        if not batch_mode:
            self._render(force_autoscale=True)

    def _log_batch(self, message: str) -> None:
        self._batch_log.append(str(message).rstrip())
        self._batch_log.ensureCursorVisible()

    def _finish_batch(self) -> None:
        self._batch_running = False
        self._batch_handle = None
        self._batch_poll_timer.stop()
        self._btn_batch.setText("Run batch")

    def _drain_batch_queue(self) -> None:
        if self._closing:
            return
        if self._batch_handle is None:
            return
        items, done = self._batch_handle.drain_messages()
        for item in items:
            self._log_batch(str(item))
        if done:
            self._finish_batch()
            return

    def _on_apply(self) -> None:
        if self._closing:
            return
        if self._mode_is_batch():
            self._apply_settings(reset=False)
            return
        self._apply_settings(reset=False)
        self._render(force_autoscale=True)

    def _on_reset(self) -> None:
        if self._closing:
            return
        if self._mode_is_batch():
            return
        self._apply_settings(reset=True)
        self._render(force_autoscale=True)

    def _on_step(self) -> None:
        if self._closing:
            return
        if self._mode_is_batch():
            return
        self._apply_settings(reset=False)
        self._runner.step_once()
        self._render()

    def _on_run_toggle(self) -> None:
        if self._closing:
            return
        if self._mode_is_batch():
            self._on_batch_toggle()
            return
        self._apply_settings(reset=False)
        self._running = not bool(self._running)
        self._btn_run.setText("Stop" if self._running else "Run")
        if self._running:
            self._timer.start()
        else:
            self._timer.stop()

    def _on_batch_toggle(self) -> None:
        if self._closing:
            return
        if not self._mode_is_batch():
            return
        if self._batch_running:
            if self._batch_handle is not None:
                self._batch_handle.cancel()
                self._log_batch("[cancel] requested")
            return

        try:
            cfg = self._build_config_from_controls()
            symbol_ids = _parse_symbol_csv(self._batch_symbols.text())
            n = max(1, _to_int(self._batch_n.text(), 10))
            seed0 = _to_int(self._batch_seed0.text(), 0)
            steps = max(1, _to_int(self._batch_steps.text(), 4))
            out_root = Path(str(self._batch_out.text()).strip() or "runs/out/batch_ui")
            fields_npz = bool(self._batch_record_fields.isChecked())
            fields_every = max(1, _to_int(self._batch_fields_every.text(), 1))
            invariant_streams = [
                chunk.strip() for chunk in str(self._invariant_streams.text() or "").split(",") if chunk.strip()
            ] or None
        except Exception as exc:
            self._log_batch(f"[error] {exc}")
            return

        request = BatchRunRequest(
            config=cfg,
            symbol_ids=symbol_ids,
            batch_n=int(n),
            seed0=int(seed0),
            tick_budget=int(steps),
            out_root=Path(out_root),
            fields_npz=bool(fields_npz),
            fields_every_steps=int(fields_every),
            invariant_streams=invariant_streams,
        )
        self._batch_running = True
        self._btn_batch.setText("Stop batch")
        self._batch_log.clear()
        self._log_batch(build_batch_start_message(request))
        self._batch_handle = start_batch_run(request)
        self._batch_poll_timer.start()


def run_napari_interactive(
    *,
    preset: str = "default",
    override_path: str | None = None,
    autoscale: bool = False,
    title: str = "DETM napari interactive (in-process)",
) -> int:
    os.environ.setdefault("QT_API", "pyside6")
    _patch_six_meta_path_importer()
    try:
        import napari
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError("napari + qtpy are required for napari interactive mode") from exc

    settings = _build_interactive_settings(preset=str(preset), override_path=override_path)
    runner = DetmUiRunner(settings)
    viewer = napari.Viewer(title=str(title))
    controller = _InteractiveDockController(
        viewer=viewer,
        runner=runner,
        title="DETM Controls",
        autoscale=bool(autoscale),
    )
    try:
        from qtpy import QtWidgets

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(controller.close)  # type: ignore[arg-type]
    except Exception:
        pass
    try:
        qt_window = getattr(getattr(viewer, "window", None), "_qt_window", None)
        if qt_window is not None and hasattr(qt_window, "destroyed"):
            qt_window.destroyed.connect(lambda *_args: controller.close())  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        napari.run()
    finally:
        controller.close()
    return 0


__all__ = [
    "_build_interactive_settings",
    "_build_quiver_vectors",
    "_parse_symbol_csv",
    "_resolve_influence_policy",
    "_sanitize_ui_overrides",
    "run_napari_interactive",
]
