#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""View page builder for napari interactive controls."""

from __future__ import annotations

from typing import Any

from detm_app.ui.napari.interactive.flow.graph import available_graph_series_ids


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

    self._plane_combo = QtWidgets.QComboBox()
    self._plane_combo.addItem("native", None)
    self._plane_combo.currentIndexChanged.connect(lambda *_args: self._render())
    row_plane = QtWidgets.QHBoxLayout()
    row_plane.addWidget(QtWidgets.QLabel("plane"))
    row_plane.addWidget(self._plane_combo)
    lay_view.addLayout(row_plane)

    self._cmap_combo = QtWidgets.QComboBox()
    self._cmap_combo.addItems(["heat", "gray"])
    self._cmap_combo.setCurrentText("heat")
    row_cmap = QtWidgets.QHBoxLayout()
    row_cmap.addWidget(QtWidgets.QLabel("cmap"))
    row_cmap.addWidget(self._cmap_combo)
    lay_view.addLayout(row_cmap)

    self._quiver_enabled = QtWidgets.QCheckBox("quiver")
    # Default-off keeps first render less cluttered; can be enabled on demand.
    self._quiver_enabled.setChecked(False)
    lay_view.addWidget(self._quiver_enabled)
    self._quiver_step = QtWidgets.QSpinBox()
    self._quiver_step.setRange(1, 32)
    self._quiver_step.setValue(3)
    row_qs = QtWidgets.QHBoxLayout()
    row_qs.addWidget(QtWidgets.QLabel("quiver_step"))
    row_qs.addWidget(self._quiver_step)
    lay_view.addLayout(row_qs)
    self._quiver_scale = QtWidgets.QDoubleSpinBox()
    self._quiver_scale.setRange(0.0, 2.0)
    self._quiver_scale.setSingleStep(0.05)
    self._quiver_scale.setValue(0.65)
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

    self._graph_enabled = QtWidgets.QCheckBox("graphs_enabled")
    self._graph_enabled.setChecked(bool(getattr(settings, "graph_enabled", True)))
    lay_view.addWidget(self._graph_enabled)

    known_series = ",".join(available_graph_series_ids())
    graph_tooltip = (
        f"Available: {known_series}\n"
        "Preset runtime: event_count,influence_count,cpu_time_ms,energy_mean,tau_mean\n"
        "Preset refinement: refinement_count,decision_count,operator_reuse,transferability\n"
        "Preset stability: energy_var,energy_std,energy_range,oscillation_score\n"
        "Preset legacy: A_t,P_t,T_t,n_peaks\n"
        "Preset freeze+A3: freeze_mean,locked_frac,a3_plv_mean,a3_var_mean"
    )
    _, self._graph_series = self._line(
        label="graph_series(csv)",
        value=str(getattr(settings, "graph_series", "")),
        parent_layout=lay_view,
        tooltip=graph_tooltip,
    )

    self._graph_window = QtWidgets.QSpinBox()
    self._graph_window.setRange(16, 100000)
    self._graph_window.setValue(int(getattr(settings, "graph_window_steps", 256)))
    row_graph_window = QtWidgets.QHBoxLayout()
    row_graph_window.addWidget(QtWidgets.QLabel("graph_window_steps"))
    row_graph_window.addWidget(self._graph_window)
    lay_view.addLayout(row_graph_window)

    self._graph_hist_enabled = QtWidgets.QCheckBox("graph_hist_enabled")
    self._graph_hist_enabled.setChecked(bool(getattr(settings, "graph_hist_enabled", True)))
    lay_view.addWidget(self._graph_hist_enabled)

    self._graph_hist_bins = QtWidgets.QSpinBox()
    self._graph_hist_bins.setRange(4, 512)
    self._graph_hist_bins.setValue(int(getattr(settings, "graph_hist_bins", 48)))
    row_graph_bins = QtWidgets.QHBoxLayout()
    row_graph_bins.addWidget(QtWidgets.QLabel("graph_hist_bins"))
    row_graph_bins.addWidget(self._graph_hist_bins)
    lay_view.addLayout(row_graph_bins)

    self._anchor_overlay_enabled = QtWidgets.QCheckBox("anchor_overlay_enabled")
    self._anchor_overlay_enabled.setChecked(bool(getattr(settings, "anchor_overlay_enabled", True)))
    lay_view.addWidget(self._anchor_overlay_enabled)

    self._anchor_top_k = QtWidgets.QSpinBox()
    self._anchor_top_k.setRange(1, 256)
    self._anchor_top_k.setValue(int(getattr(settings, "anchor_top_k", 8)))
    row_anchor_top_k = QtWidgets.QHBoxLayout()
    row_anchor_top_k.addWidget(QtWidgets.QLabel("anchor_top_k"))
    row_anchor_top_k.addWidget(self._anchor_top_k)
    lay_view.addLayout(row_anchor_top_k)

    self._anchor_threshold = QtWidgets.QDoubleSpinBox()
    self._anchor_threshold.setRange(0.0, 10.0)
    self._anchor_threshold.setDecimals(3)
    self._anchor_threshold.setSingleStep(0.05)
    self._anchor_threshold.setValue(float(getattr(settings, "anchor_threshold", 0.8)))
    row_anchor_threshold = QtWidgets.QHBoxLayout()
    row_anchor_threshold.addWidget(QtWidgets.QLabel("anchor_threshold"))
    row_anchor_threshold.addWidget(self._anchor_threshold)
    lay_view.addLayout(row_anchor_threshold)

    self._anchor_capture_ticks = QtWidgets.QSpinBox()
    self._anchor_capture_ticks.setRange(1, 1000)
    self._anchor_capture_ticks.setValue(int(getattr(settings, "anchor_capture_ticks", 4)))
    row_anchor_capture = QtWidgets.QHBoxLayout()
    row_anchor_capture.addWidget(QtWidgets.QLabel("anchor_capture_ticks"))
    row_anchor_capture.addWidget(self._anchor_capture_ticks)
    lay_view.addLayout(row_anchor_capture)

    lay_view.addStretch(1)
    self._toolbox.addItem(page_view, "View & Run")


__all__ = ["add_view_page"]
