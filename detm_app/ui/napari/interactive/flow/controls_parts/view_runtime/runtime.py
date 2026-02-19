#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Runtime page builder for napari interactive controls."""

from __future__ import annotations

from typing import Any


def add_runtime_page(controller: Any, *, QtWidgets: Any, cfg: Any, tips: dict[str, str]) -> None:
    self = controller
    level_policy = cfg.level_policy
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
    self._alpha = QtWidgets.QDoubleSpinBox()
    self._alpha.setRange(-10.0, 10.0)
    self._alpha.setDecimals(4)
    self._alpha.setValue(float(cfg.dynamics.alpha))
    self._beta = QtWidgets.QDoubleSpinBox()
    self._beta.setRange(-10.0, 10.0)
    self._beta.setDecimals(4)
    self._beta.setValue(float(cfg.dynamics.beta))
    self._kappa = QtWidgets.QDoubleSpinBox()
    self._kappa.setRange(-10.0, 10.0)
    self._kappa.setDecimals(4)
    self._kappa.setValue(float(cfg.dynamics.kappa))
    self._gamma = QtWidgets.QDoubleSpinBox()
    self._gamma.setRange(-10.0, 10.0)
    self._gamma.setDecimals(4)
    self._gamma.setValue(float(cfg.dynamics.gamma))
    self._lambda_t = QtWidgets.QDoubleSpinBox()
    self._lambda_t.setRange(-10.0, 10.0)
    self._lambda_t.setDecimals(4)
    self._lambda_t.setValue(float(cfg.dynamics.lambda_t))
    for name, widget, tip_key in [
        ("alpha", self._alpha, "dynamics.alpha"),
        ("beta", self._beta, "dynamics.beta"),
        ("kappa", self._kappa, "dynamics.kappa"),
        ("gamma", self._gamma, "dynamics.gamma"),
        ("lambda_t", self._lambda_t, "dynamics.lambda_t"),
    ]:
        row = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(name)
        lbl.setToolTip(tips.get(tip_key, ""))
        widget.setToolTip(tips.get(tip_key, ""))
        row.addWidget(lbl)
        row.addWidget(widget)
        lay_runtime.addLayout(row)

    self._learn_refinement = QtWidgets.QCheckBox("allow_refinement")
    self._learn_refinement.setChecked(bool(level_policy.allow_refinement))
    lay_runtime.addWidget(self._learn_refinement)

    self._learn_refine_ratio = QtWidgets.QDoubleSpinBox()
    self._learn_refine_ratio.setRange(0.0, 10.0)
    self._learn_refine_ratio.setDecimals(4)
    self._learn_refine_ratio.setSingleStep(0.01)
    self._learn_refine_ratio.setValue(float(level_policy.refinement_capacity_overflow_ratio_threshold))
    row_refine_ratio = QtWidgets.QHBoxLayout()
    row_refine_ratio.addWidget(QtWidgets.QLabel("refine_ratio_threshold"))
    row_refine_ratio.addWidget(self._learn_refine_ratio)
    lay_runtime.addLayout(row_refine_ratio)

    self._learn_refine_mean = QtWidgets.QDoubleSpinBox()
    self._learn_refine_mean.setRange(0.0, 10.0)
    self._learn_refine_mean.setDecimals(4)
    self._learn_refine_mean.setSingleStep(0.01)
    self._learn_refine_mean.setValue(float(level_policy.refinement_capacity_overflow_mean_threshold))
    row_refine_mean = QtWidgets.QHBoxLayout()
    row_refine_mean.addWidget(QtWidgets.QLabel("refine_mean_threshold"))
    row_refine_mean.addWidget(self._learn_refine_mean)
    lay_runtime.addLayout(row_refine_mean)

    self._learn_refine_saturation = QtWidgets.QDoubleSpinBox()
    self._learn_refine_saturation.setRange(0.0, 1.0)
    self._learn_refine_saturation.setDecimals(4)
    self._learn_refine_saturation.setSingleStep(0.005)
    saturation_band = float(getattr(level_policy, "refinement_capacity_saturation_band", 0.0))
    if saturation_band <= 0.0:
        saturation_band = 0.05
    self._learn_refine_saturation.setValue(float(saturation_band))
    row_refine_sat = QtWidgets.QHBoxLayout()
    row_refine_sat.addWidget(QtWidgets.QLabel("refine_saturation_band"))
    row_refine_sat.addWidget(self._learn_refine_saturation)
    lay_runtime.addLayout(row_refine_sat)

    self._learn_refine_min_signals = QtWidgets.QSpinBox()
    self._learn_refine_min_signals.setRange(1, 32)
    self._learn_refine_min_signals.setValue(int(level_policy.refinement_capacity_min_signals))
    row_refine_min = QtWidgets.QHBoxLayout()
    row_refine_min.addWidget(QtWidgets.QLabel("refine_min_signals"))
    row_refine_min.addWidget(self._learn_refine_min_signals)
    lay_runtime.addLayout(row_refine_min)

    self._learn_refine_autoclamp = QtWidgets.QCheckBox("refine_autoclamp")
    self._learn_refine_autoclamp.setChecked(
        bool(getattr(level_policy, "refinement_capacity_autoclamp_enabled", False))
    )
    lay_runtime.addWidget(self._learn_refine_autoclamp)

    _, self._learn_runtime_events = self._line(
        label="runtime_adaptive_events",
        value=",".join(level_policy.runtime_adaptive_signal_event_types),
        parent_layout=lay_runtime,
        tooltip="Comma-separated event types for runtime-adaptive trigger.",
    )

    self._learn_adaptive_hold = QtWidgets.QSpinBox()
    self._learn_adaptive_hold.setRange(0, 100000)
    self._learn_adaptive_hold.setValue(int(level_policy.runtime_adaptive_hold_ticks))
    row_hold = QtWidgets.QHBoxLayout()
    row_hold.addWidget(QtWidgets.QLabel("runtime_adaptive_hold_ticks"))
    row_hold.addWidget(self._learn_adaptive_hold)
    lay_runtime.addLayout(row_hold)

    self._learn_anti_goodhart = QtWidgets.QCheckBox("anti_goodhart_enabled")
    self._learn_anti_goodhart.setChecked(bool(level_policy.anti_goodhart_enabled))
    lay_runtime.addWidget(self._learn_anti_goodhart)

    self._learning_view = QtWidgets.QCheckBox("learning_view_enabled")
    self._learning_view.setChecked(bool(getattr(self._settings, "learning_view_enabled", True)))
    lay_runtime.addWidget(self._learning_view)

    self._learning_window = QtWidgets.QSpinBox()
    self._learning_window.setRange(1, 100000)
    self._learning_window.setValue(int(getattr(self._settings, "learning_window_steps", 64)))
    row_window = QtWidgets.QHBoxLayout()
    row_window.addWidget(QtWidgets.QLabel("learning_window_steps"))
    row_window.addWidget(self._learning_window)
    lay_runtime.addLayout(row_window)

    lay_runtime.addStretch(1)
    self._toolbox.addItem(page_runtime, "Runtime")


__all__ = ["add_runtime_page"]
