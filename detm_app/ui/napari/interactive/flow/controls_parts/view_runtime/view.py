#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""View page builder for napari interactive controls."""

from __future__ import annotations

from typing import Any


def add_view_page(controller: Any, *, QtWidgets: Any, settings: Any) -> None:
    self = controller
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


__all__ = ["add_view_page"]
