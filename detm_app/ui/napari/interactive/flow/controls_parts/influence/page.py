#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Influence page builder for napari interactive controls."""

from __future__ import annotations

from typing import Any

from detm.runtime.symbols import list_symbols
from detm_app.ui.napari.interactive.flow.controls_parts.influence.joystick import add_joystick_group


def add_influence_page(
    controller: Any,
    *,
    QtWidgets: Any,
    QtCore: Any,
    settings: Any,
    cfg: Any,
) -> None:
    self = controller

    page_influence = QtWidgets.QWidget()
    lay_influence = QtWidgets.QVBoxLayout(page_influence)
    lay_influence.setContentsMargins(6, 6, 6, 6)
    self._influence_policy = QtWidgets.QComboBox()
    self._influence_policy.addItems(["off", "sustain", "pulse"])
    self._influence_policy.setCurrentText("off")
    self._influence_policy.currentTextChanged.connect(self._on_influence_policy_change)
    row_pol = QtWidgets.QHBoxLayout()
    row_pol.addWidget(QtWidgets.QLabel("influence_policy"))
    row_pol.addWidget(self._influence_policy)
    lay_influence.addLayout(row_pol)
    self._influence_mode = QtWidgets.QComboBox()
    self._influence_mode.addItems(["symbol", "joystick_field", "joystick_patch", "source_sink", "none"])
    self._influence_mode.setCurrentText(str(settings.influence_mode or "none"))
    self._influence_mode.currentTextChanged.connect(self._on_influence_mode_change)
    row_mode_inf = QtWidgets.QHBoxLayout()
    row_mode_inf.addWidget(QtWidgets.QLabel("influence_mode"))
    row_mode_inf.addWidget(self._influence_mode)
    lay_influence.addLayout(row_mode_inf)

    self._amplitude = QtWidgets.QDoubleSpinBox()
    self._amplitude.setRange(0.0, 2.0)
    self._amplitude.setSingleStep(0.01)
    self._amplitude.setValue(float(settings.amplitude))
    row_amp = QtWidgets.QHBoxLayout()
    row_amp.addWidget(QtWidgets.QLabel("amplitude"))
    row_amp.addWidget(self._amplitude)
    lay_influence.addLayout(row_amp)

    self._duration = QtWidgets.QSpinBox()
    self._duration.setRange(0, 10_000)
    self._duration.setValue(int(settings.influence_duration_steps))
    row_dur = QtWidgets.QHBoxLayout()
    row_dur.addWidget(QtWidgets.QLabel("influence_duration_steps"))
    row_dur.addWidget(self._duration)
    lay_influence.addLayout(row_dur)

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

    add_joystick_group(
        self,
        parent_layout=lay_influence,
        QtWidgets=QtWidgets,
        QtCore=QtCore,
        settings=settings,
    )

    self._patch_group = QtWidgets.QGroupBox("Joystick patch")
    patch_layout = QtWidgets.QVBoxLayout(self._patch_group)
    self._patch_cx = QtWidgets.QSpinBox()
    self._patch_cx.setRange(0, max(0, int(cfg.width) - 1))
    self._patch_cx.setValue(int(settings.patch_cx))
    self._patch_cy = QtWidgets.QSpinBox()
    self._patch_cy.setRange(0, max(0, int(cfg.height) - 1))
    self._patch_cy.setValue(int(settings.patch_cy))
    self._patch_radius = QtWidgets.QSpinBox()
    self._patch_radius.setRange(0, max(1, max(int(cfg.width), int(cfg.height))))
    self._patch_radius.setValue(int(settings.patch_radius))
    for name, widget in [("patch_cx", self._patch_cx), ("patch_cy", self._patch_cy), ("patch_radius", self._patch_radius)]:
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(name))
        row.addWidget(widget)
        patch_layout.addLayout(row)
    lay_influence.addWidget(self._patch_group)

    self._source_sink_group = QtWidgets.QGroupBox("Source/Sink")
    source_sink_layout = QtWidgets.QVBoxLayout(self._source_sink_group)
    self._source_x = QtWidgets.QSpinBox()
    self._source_x.setRange(0, max(0, int(cfg.width) - 1))
    self._source_x.setValue(int(settings.source_x))
    self._source_y = QtWidgets.QSpinBox()
    self._source_y.setRange(0, max(0, int(cfg.height) - 1))
    self._source_y.setValue(int(settings.source_y))
    self._sink_x = QtWidgets.QSpinBox()
    self._sink_x.setRange(0, max(0, int(cfg.width) - 1))
    self._sink_x.setValue(int(settings.sink_x))
    self._sink_y = QtWidgets.QSpinBox()
    self._sink_y.setRange(0, max(0, int(cfg.height) - 1))
    self._sink_y.setValue(int(settings.sink_y))
    for name, widget in [("source_x", self._source_x), ("source_y", self._source_y), ("sink_x", self._sink_x), ("sink_y", self._sink_y)]:
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(name))
        row.addWidget(widget)
        source_sink_layout.addLayout(row)
    self._source_value = QtWidgets.QDoubleSpinBox()
    self._source_value.setRange(0.0, 1.0)
    self._source_value.setSingleStep(0.01)
    self._source_value.setValue(float(settings.source_value))
    self._sink_value = QtWidgets.QDoubleSpinBox()
    self._sink_value.setRange(0.0, 1.0)
    self._sink_value.setSingleStep(0.01)
    self._sink_value.setValue(float(settings.sink_value))
    row_sv = QtWidgets.QHBoxLayout()
    row_sv.addWidget(QtWidgets.QLabel("source_value"))
    row_sv.addWidget(self._source_value)
    row_tv = QtWidgets.QHBoxLayout()
    row_tv.addWidget(QtWidgets.QLabel("sink_value"))
    row_tv.addWidget(self._sink_value)
    source_sink_layout.addLayout(row_sv)
    source_sink_layout.addLayout(row_tv)
    lay_influence.addWidget(self._source_sink_group)
    lay_influence.addStretch(1)
    self._toolbox.addItem(page_influence, "Influence")


__all__ = ["add_influence_page"]
