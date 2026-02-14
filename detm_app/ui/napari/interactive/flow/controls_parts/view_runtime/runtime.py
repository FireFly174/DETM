#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Runtime page builder for napari interactive controls."""

from __future__ import annotations

from typing import Any


def add_runtime_page(controller: Any, *, QtWidgets: Any, cfg: Any, tips: dict[str, str]) -> None:
    self = controller
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
    lay_runtime.addStretch(1)
    self._toolbox.addItem(page_runtime, "Runtime")


__all__ = ["add_runtime_page"]
