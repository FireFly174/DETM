#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Interactive napari dock controller implementation."""

from __future__ import annotations

from typing import Any, Callable

from detm.runtime.config import DETMConfig
from detm_app.runtime.ui_runtime import DetmUiRunner
from detm_app.ui.napari.interactive.flow.actions import (
    mode_is_batch as _mode_is_batch_flow,
    on_apply as _on_apply_flow,
    on_mode_change as _on_mode_change_flow,
    on_reset as _on_reset_flow,
    on_run_toggle as _on_run_toggle_flow,
    on_step as _on_step_flow,
)
from detm_app.ui.napari.interactive.flow.controls import build_interactive_controls
from detm_app.ui.napari.interactive.flow.batch import BatchRunState, on_batch_toggle as _on_batch_toggle_flow
from detm_app.ui.napari.interactive.flow.influence import (
    on_influence_mode_change as _on_influence_mode_change_flow,
    on_influence_policy_change as _on_influence_policy_change_flow,
    sync_geometry_bounds as _sync_geometry_bounds_flow,
)
from detm_app.ui.napari.interactive.flow.settings import (
    apply_settings as _apply_settings_flow,
    build_config_from_controls as _build_config_from_controls_flow,
)
from detm_app.ui.napari.interactive.flow.ui_wiring import (
    build_buttons as _build_buttons_flow,
    install_shortcuts as _install_shortcuts_flow,
)
from detm_app.ui.napari.interactive.flow.widget_io import (
    line as _line_flow,
    read_float as _read_float_flow,
    read_int as _read_int_flow,
    read_text as _read_text_flow,
)
from detm_app.ui.napari.interactive.flow.render import NapariRenderFlow
from detm_app.ui.napari.interactive.flow.graph import NapariGraphDock


class _InteractiveDockController:
    def __init__(self, *, viewer: Any, runner: DetmUiRunner, title: str, autoscale: bool, parse_symbol_csv: Callable[[str], list[str]]) -> None:
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
        self._render_flow = NapariRenderFlow(
            viewer=self._viewer,
            field_layer_name=self._field_layer_name,
            quiver_layer_name=self._quiver_layer_name,
            colormap_map=self._colormap_map,
        )
        self._parse_symbol_csv = parse_symbol_csv

        self._timer = QtCore.QTimer()
        self._timer.setInterval(max(1, int(self._settings.tick_interval_ms)))
        self._timer.timeout.connect(self._on_tick)
        self._batch_poll_timer = QtCore.QTimer()
        self._batch_poll_timer.setInterval(75)
        self._batch_poll_timer.timeout.connect(self._drain_batch_queue)
        self._closed = False
        self._closing = False
        self._field_combo: Any = None
        self._cmap_combo: Any = None
        self._quiver_enabled: Any = None
        self._quiver_step: Any = None
        self._quiver_scale: Any = None
        self._autoscale_check: Any = None
        self._btn_batch: Any = None
        self._batch_log: Any = None
        self._graph_dock: Any = None
        self._last_render_meta: dict[str, Any] = {}

        self._root = QtWidgets.QWidget()
        self._layout = QtWidgets.QVBoxLayout(self._root)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(6)

        self._status = QtWidgets.QLabel("status: ready")
        self._status.setWordWrap(True)
        self._layout.addWidget(self._status)

        self._build_controls()
        self._build_buttons()
        self._batch_state = BatchRunState(
            poll_timer=self._batch_poll_timer,
            log=self._log_batch,
            clear_log=self._clear_batch_log,
            set_button_text=self._set_batch_button_text,
        )
        self._install_shortcuts()
        self._on_mode_change()
        self._render(force_autoscale=True)
        self._viewer.window.add_dock_widget(self._root, name=str(title), area="right")
        try:
            self._graph_dock = NapariGraphDock(viewer=self._viewer, title="DETM Graphs")
            self._configure_graph_dock()
            self._update_graph_dock()
        except Exception as exc:
            self._graph_dock = None
            self._status.setText(
                f"status: ready (graphs disabled: {type(exc).__name__})"
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closing = True
        self._timer.stop()
        self._batch_state.close()
        if self._graph_dock is not None and hasattr(self._graph_dock, "close"):
            self._graph_dock.close()
            self._graph_dock = None
        self._runner.close()
        self._closed = True

    def _line(
        self,
        *,
        label: str,
        value: str,
        parent_layout: Any | None = None,
        tooltip: str = "",
    ) -> tuple[Any, Any]:
        return _line_flow(self, label=label, value=value, parent_layout=parent_layout, tooltip=tooltip)

    def _read_text(self, widget: Any, default: str = "") -> str:
        return _read_text_flow(self, widget, default)

    def _read_int(self, widget: Any, default: int) -> int:
        return _read_int_flow(self, widget, default)

    def _read_float(self, widget: Any, default: float) -> float:
        return _read_float_flow(self, widget, default)

    def _build_controls(self) -> None:
        build_interactive_controls(self)

    def _sync_geometry_bounds(self, *_args: object) -> None:
        _sync_geometry_bounds_flow(self)

    def _on_influence_mode_change(self, mode: str) -> None:
        _on_influence_mode_change_flow(self, mode)

    def _on_influence_policy_change(self, policy: str) -> None:
        _on_influence_policy_change_flow(self, policy)

    def _build_buttons(self) -> None:
        _build_buttons_flow(self)

    def _install_shortcuts(self) -> None:
        _install_shortcuts_flow(self)

    def _build_config_from_controls(self) -> DETMConfig:
        return _build_config_from_controls_flow(self)

    def _apply_settings(self, *, reset: bool) -> None:
        _apply_settings_flow(self, reset=reset)

    def _render(self, *, force_autoscale: bool = False) -> None:
        if force_autoscale:
            self._autoscale = True
        render_meta = self._render_flow.render(
            runner=self._runner,
            settings=self._settings,
            status_widget=self._status,
            field_name=str(self._field_combo.currentText()),
            cmap_name=str(self._cmap_combo.currentText()),
            quiver_enabled=bool(self._quiver_enabled.isChecked()),
            quiver_step=max(1, self._read_int(self._quiver_step, 2)),
            quiver_scale=max(0.0, self._read_float(self._quiver_scale, 0.8)),
            autoscale=bool(self._autoscale),
            anchors_enabled=bool(getattr(self._settings, "anchor_overlay_enabled", True)),
            anchors_top_k=max(1, int(getattr(self._settings, "anchor_top_k", 8))),
            anchors_threshold=max(0.0, float(getattr(self._settings, "anchor_threshold", 0.8))),
            anchors_capture_ticks=max(1, int(getattr(self._settings, "anchor_capture_ticks", 4))),
        )
        self._last_render_meta = dict(render_meta) if isinstance(render_meta, dict) else {}
        self._update_graph_dock()
        if force_autoscale:
            self._autoscale = bool(self._autoscale_check.isChecked())

    def _configure_graph_dock(self) -> None:
        if self._graph_dock is None:
            return
        self._graph_dock.configure(
            enabled=bool(getattr(self._settings, "graph_enabled", True)),
            series_csv=str(getattr(self._settings, "graph_series", "")),
            window_steps=max(16, int(getattr(self._settings, "graph_window_steps", 256))),
            histogram_enabled=bool(getattr(self._settings, "graph_hist_enabled", True)),
            histogram_bins=max(4, int(getattr(self._settings, "graph_hist_bins", 48))),
        )

    def _update_graph_dock(self) -> None:
        if self._graph_dock is None:
            return
        self._configure_graph_dock()
        meta = dict(self._last_render_meta or {})
        snapshot = dict(getattr(self._runner, "learning_snapshot", {}))
        legacy_metrics = dict(meta.get("legacy_metrics", {}))
        if len(legacy_metrics) > 0:
            snapshot["legacy_metrics"] = legacy_metrics
        self._graph_dock.update(
            snapshot=snapshot,
            energy_field=meta.get("energy_field"),
            anchor_summary=dict(meta.get("anchor_summary", {})),
        )

    def _on_tick(self) -> None:
        if self._closing or (not bool(self._running)):
            return
        self._runner.step_once()
        self._render()

    def _mode_is_batch(self) -> bool:
        return _mode_is_batch_flow(self)

    def _on_mode_change(self, *_args: object) -> None:
        _on_mode_change_flow(self)

    def _set_batch_button_text(self, text: str) -> None:
        self._btn_batch.setText(str(text))

    def _clear_batch_log(self) -> None:
        self._batch_log.clear()

    def _log_batch(self, message: str) -> None:
        self._batch_log.append(str(message).rstrip())
        self._batch_log.ensureCursorVisible()

    def _drain_batch_queue(self) -> None:
        if self._closing:
            return
        self._batch_state.drain()

    def _on_apply(self) -> None:
        _on_apply_flow(self)

    def _on_reset(self) -> None:
        _on_reset_flow(self)

    def _on_step(self) -> None:
        _on_step_flow(self)

    def _on_run_toggle(self) -> None:
        _on_run_toggle_flow(self)

    def _on_batch_toggle(self) -> None:
        _on_batch_toggle_flow(self)


