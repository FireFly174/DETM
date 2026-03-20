#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Pluggable time-series graphs for napari interactive mode."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import sys
from typing import Any, Callable, Dict, Iterable, Mapping

import numpy as np


@dataclass(frozen=True)
class GraphSeriesSpec:
    id: str
    label: str
    extractor: Callable[[Mapping[str, Any]], float]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_flag(value: Any) -> float:
    return 1.0 if bool(value) else 0.0


def _event_count(snapshot: Mapping[str, Any]) -> float:
    return _to_float(snapshot.get("event_count", 0))


def _refinement_count(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("refinement_count", 0))


def _decision_count(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("operator_decision_count", 0))


def _operator_reuse(snapshot: Mapping[str, Any]) -> float:
    panel = dict(snapshot.get("portability_panel", {}))
    return _to_float(panel.get("operator_reuse", 0.0))


def _transferability(snapshot: Mapping[str, Any]) -> float:
    panel = dict(snapshot.get("portability_panel", {}))
    return _to_float(panel.get("transferability", 0.0))


def _hold_rate(snapshot: Mapping[str, Any]) -> float:
    panel = dict(snapshot.get("portability_panel", {}))
    return _to_float(panel.get("hold_rate", 0.0))


def _torsion_health(snapshot: Mapping[str, Any]) -> float:
    panel = dict(snapshot.get("portability_panel", {}))
    return _to_float(panel.get("torsion_health", 1.0))


def _runtime_active(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_flag(watchpoints.get("runtime_adaptive_window_active", False))


def _anti_goodhart_flag(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_flag(watchpoints.get("anti_goodhart_flag", False))


def _exploration_horizon_ticks(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("exploration_horizon_ticks", 0.0))


def _horizon_recovery_cost_ticks(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("horizon_recovery_cost_ticks", 0.0))


def _cpu_time_ms(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("cpu_time_ms", 0.0))


def _oscillation_score(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("oscillation_score", 0.0))


def _influence_count(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("influence_count", 0.0))


def _attractor_count(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("attractor_count", 0.0))


def _operator_reuse_rate(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("operator_reuse_rate", 0.0))


def _step_ops_estimate(snapshot: Mapping[str, Any]) -> float:
    watchpoints = dict(snapshot.get("watchpoints", {}))
    return _to_float(watchpoints.get("step_ops_estimate", 0.0))


def _energy_mean(snapshot: Mapping[str, Any]) -> float:
    summary = dict(snapshot.get("signature_summary", {}))
    return _to_float(summary.get("energy_mean", 0.0))


def _energy_var(snapshot: Mapping[str, Any]) -> float:
    summary = dict(snapshot.get("signature_summary", {}))
    return _to_float(summary.get("energy_var", 0.0))


def _energy_min(snapshot: Mapping[str, Any]) -> float:
    energy = dict(dict(snapshot.get("field_summaries", {})).get("energy", {}))
    return _to_float(energy.get("minimum", 0.0))


def _energy_max(snapshot: Mapping[str, Any]) -> float:
    energy = dict(dict(snapshot.get("field_summaries", {})).get("energy", {}))
    return _to_float(energy.get("maximum", 0.0))


def _energy_std(snapshot: Mapping[str, Any]) -> float:
    energy = dict(dict(snapshot.get("field_summaries", {})).get("energy", {}))
    return _to_float(energy.get("std", 0.0))


def _energy_range(snapshot: Mapping[str, Any]) -> float:
    energy = dict(dict(snapshot.get("field_summaries", {})).get("energy", {}))
    return _to_float(energy.get("range", 0.0))


def _entropy_mean(snapshot: Mapping[str, Any]) -> float:
    summary = dict(snapshot.get("signature_summary", {}))
    return _to_float(summary.get("entropy_mean", 0.0))


def _tau_mean(snapshot: Mapping[str, Any]) -> float:
    summary = dict(snapshot.get("signature_summary", {}))
    return _to_float(summary.get("internal_time_mean", 0.0))


def _center_x(snapshot: Mapping[str, Any]) -> float:
    summary = dict(snapshot.get("signature_summary", {}))
    return _to_float(summary.get("center_of_mass_x", 0.0))


def _center_y(snapshot: Mapping[str, Any]) -> float:
    summary = dict(snapshot.get("signature_summary", {}))
    return _to_float(summary.get("center_of_mass_y", 0.0))


def _influence_last_amplitude(snapshot: Mapping[str, Any]) -> float:
    influence = dict(snapshot.get("influence", {}))
    return _to_float(influence.get("last_amplitude", 0.0))


def _influence_last_affected_fraction(snapshot: Mapping[str, Any]) -> float:
    influence = dict(snapshot.get("influence", {}))
    return _to_float(influence.get("last_affected_fraction", 0.0))


def _A_t(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("A_t", 0.0))


def _P_t(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("P_t", 0.0))


def _T_t(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("T_t", 0.0))


def _n_peaks(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("n_peaks", 0.0))


def _freeze_mean(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("freeze_mean", 0.0))


def _freeze_min(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("freeze_min", 0.0))


def _locked_frac(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("locked_frac", 0.0))


def _a3_plv_mean(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("a3_plv_mean", 0.0))


def _a3_var_mean(snapshot: Mapping[str, Any]) -> float:
    legacy = dict(snapshot.get("legacy_metrics", {}))
    return _to_float(legacy.get("a3_var_mean", 0.0))


GRAPH_SERIES_REGISTRY: Dict[str, GraphSeriesSpec] = {}


def register_graph_series(spec: GraphSeriesSpec) -> None:
    key = str(spec.id).strip()
    if not key:
        raise ValueError("GraphSeriesSpec.id must not be empty")
    GRAPH_SERIES_REGISTRY[key] = spec


def _register_builtin_series() -> None:
    if GRAPH_SERIES_REGISTRY:
        return
    for spec in (
        GraphSeriesSpec("event_count", "event_count", _event_count),
        GraphSeriesSpec("refinement_count", "refinement_count", _refinement_count),
        GraphSeriesSpec("decision_count", "decision_count", _decision_count),
        GraphSeriesSpec("operator_reuse", "operator_reuse", _operator_reuse),
        GraphSeriesSpec("transferability", "transferability", _transferability),
        GraphSeriesSpec("hold_rate", "hold_rate", _hold_rate),
        GraphSeriesSpec("torsion_health", "torsion_health", _torsion_health),
        GraphSeriesSpec("runtime_active", "runtime_active", _runtime_active),
        GraphSeriesSpec("anti_goodhart_flag", "anti_goodhart_flag", _anti_goodhart_flag),
        GraphSeriesSpec("exploration_horizon_ticks", "exploration_horizon_ticks", _exploration_horizon_ticks),
        GraphSeriesSpec(
            "horizon_recovery_cost_ticks",
            "horizon_recovery_cost_ticks",
            _horizon_recovery_cost_ticks,
        ),
        GraphSeriesSpec("cpu_time_ms", "cpu_time_ms", _cpu_time_ms),
        GraphSeriesSpec("oscillation_score", "oscillation_score", _oscillation_score),
        GraphSeriesSpec("influence_count", "influence_count", _influence_count),
        GraphSeriesSpec("attractor_count", "attractor_count", _attractor_count),
        GraphSeriesSpec("operator_reuse_rate", "operator_reuse_rate", _operator_reuse_rate),
        GraphSeriesSpec("step_ops_estimate", "step_ops_estimate", _step_ops_estimate),
        GraphSeriesSpec("energy_mean", "energy_mean", _energy_mean),
        GraphSeriesSpec("energy_var", "energy_var", _energy_var),
        GraphSeriesSpec("energy_min", "energy_min", _energy_min),
        GraphSeriesSpec("energy_max", "energy_max", _energy_max),
        GraphSeriesSpec("energy_std", "energy_std", _energy_std),
        GraphSeriesSpec("energy_range", "energy_range", _energy_range),
        GraphSeriesSpec("entropy_mean", "entropy_mean", _entropy_mean),
        GraphSeriesSpec("tau_mean", "tau_mean", _tau_mean),
        GraphSeriesSpec("center_x", "center_x", _center_x),
        GraphSeriesSpec("center_y", "center_y", _center_y),
        GraphSeriesSpec("influence_last_amplitude", "influence_last_amplitude", _influence_last_amplitude),
        GraphSeriesSpec(
            "influence_last_affected_fraction",
            "influence_last_affected_fraction",
            _influence_last_affected_fraction,
        ),
        GraphSeriesSpec("A_t", "A_t", _A_t),
        GraphSeriesSpec("P_t", "P_t", _P_t),
        GraphSeriesSpec("T_t", "T_t", _T_t),
        GraphSeriesSpec("n_peaks", "n_peaks", _n_peaks),
        GraphSeriesSpec("freeze_mean", "freeze_mean", _freeze_mean),
        GraphSeriesSpec("freeze_min", "freeze_min", _freeze_min),
        GraphSeriesSpec("locked_frac", "locked_frac", _locked_frac),
        GraphSeriesSpec("a3_plv_mean", "a3_plv_mean", _a3_plv_mean),
        GraphSeriesSpec("a3_var_mean", "a3_var_mean", _a3_var_mean),
    ):
        register_graph_series(spec)


_register_builtin_series()

DEFAULT_GRAPH_SERIES = (
    "event_count",
    "refinement_count",
    "influence_count",
    "cpu_time_ms",
    "energy_mean",
    "tau_mean",
)


def available_graph_series_ids() -> list[str]:
    return sorted(GRAPH_SERIES_REGISTRY.keys())


def parse_graph_series_csv(raw: str | None) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return list(DEFAULT_GRAPH_SERIES)
    out: list[str] = []
    known = set(available_graph_series_ids())
    for chunk in text.split(","):
        series_id = str(chunk).strip()
        if not series_id:
            continue
        if series_id in known:
            out.append(series_id)
    if not out:
        return list(DEFAULT_GRAPH_SERIES)
    # Keep order but remove duplicates.
    seen: set[str] = set()
    dedup: list[str] = []
    for series_id in out:
        if series_id in seen:
            continue
        seen.add(series_id)
        dedup.append(series_id)
    return dedup


def extract_graph_series_values(
    *,
    snapshot: Mapping[str, Any],
    series_ids: Iterable[str],
) -> dict[str, float]:
    out: dict[str, float] = {}
    for series_id in list(series_ids):
        spec = GRAPH_SERIES_REGISTRY.get(str(series_id))
        if spec is None:
            continue
        try:
            out[str(series_id)] = float(spec.extractor(snapshot))
        except Exception:
            out[str(series_id)] = 0.0
    return out


def _build_histogram_bins(values: np.ndarray, requested_bins: int) -> int | np.ndarray:
    """Build stable histogram bins for narrow/degenerate numeric ranges."""
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    arr = arr[np.isfinite(arr)]
    if arr.size <= 0:
        return max(4, int(requested_bins))

    lo = float(np.min(arr))
    hi = float(np.max(arr))
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return max(4, int(requested_bins))

    bins = max(4, int(requested_bins))
    span = float(hi - lo)
    scale = max(1.0, abs(lo), abs(hi))
    tiny = np.finfo(np.float64).eps * scale * 64.0
    if span <= tiny:
        pad = max(tiny, 1e-12)
        return np.linspace(lo - pad, hi + pad, bins + 1, dtype=np.float64)
    return bins


def _patch_six_meta_path_importer() -> None:
    """Mitigate PySide/shiboken interactions with six importer in some envs."""
    # Ensure six importer is materialized before matplotlib/PySide import chain.
    try:
        import six  # type: ignore
    except Exception:
        six = None

    candidates: list[Any] = []
    if six is not None:
        importer = getattr(six, "_importer", None)
        if importer is not None:
            candidates.append(importer)
    candidates.extend(list(sys.meta_path))

    seen: set[int] = set()
    for importer in candidates:
        obj_id = id(importer)
        if obj_id in seen:
            continue
        seen.add(obj_id)
        if type(importer).__name__ == "_SixMetaPathImporter" and not hasattr(importer, "_path"):
            try:
                setattr(importer, "_path", [])
            except Exception:
                continue


class NapariGraphDock:
    """Dock widget with pluggable graph series for DETM interactive mode."""

    def __init__(self, *, viewer: Any, title: str = "DETM Graphs") -> None:
        from qtpy import QtWidgets

        self._viewer = viewer
        self._title = str(title)
        self._enabled = True
        self._window_steps = 256
        self._series_ids = list(DEFAULT_GRAPH_SERIES)
        self._samples: deque[dict[str, Any]] = deque(maxlen=int(self._window_steps))
        self._last_tick = -1
        self._hist_enabled = True
        self._hist_bins = 48
        self._latest_energy_field: np.ndarray | None = None
        self._anchor_summary: dict[str, Any] = {}
        self._plot_available = False
        self._plot_error = ""
        self._figure: Any = None
        self._canvas: Any = None
        self._axis_series: Any = None
        self._axis_hist: Any = None

        self._widget = QtWidgets.QWidget()
        self._layout = QtWidgets.QVBoxLayout(self._widget)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(4)

        self._status = QtWidgets.QLabel("graphs: waiting for data")
        self._status.setWordWrap(True)
        self._layout.addWidget(self._status)

        _patch_six_meta_path_importer()
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure

            self._figure = Figure(figsize=(6.0, 2.5), tight_layout=True)
            self._canvas = FigureCanvas(self._figure)
            self._axis_series = self._figure.add_subplot(1, 2, 1)
            self._axis_hist = self._figure.add_subplot(1, 2, 2)
            self._layout.addWidget(self._canvas, 1)
            self._plot_available = True
        except Exception as exc:
            error_text = type(exc).__name__
            try:
                message = str(exc).strip()
            except Exception:
                message = ""
            if message:
                error_text = f"{error_text}: {message}"
            self._plot_error = error_text
            hint = QtWidgets.QLabel(
                "graphs: plotting backend is unavailable; launch continues without chart canvas."
            )
            hint.setWordWrap(True)
            self._layout.addWidget(hint)

        self._dock = self._viewer.window.add_dock_widget(self._widget, name=self._title, area="bottom")

    def close(self) -> None:
        try:
            if hasattr(self._dock, "close"):
                self._dock.close()
        except Exception:
            pass

    def configure(
        self,
        *,
        enabled: bool,
        series_csv: str,
        window_steps: int,
        histogram_enabled: bool = True,
        histogram_bins: int = 48,
    ) -> None:
        self._enabled = bool(enabled)
        desired_window = max(16, int(window_steps))
        if desired_window != int(self._window_steps):
            self._window_steps = desired_window
            self._samples = deque(list(self._samples)[-desired_window:], maxlen=desired_window)
        self._hist_enabled = bool(histogram_enabled)
        self._hist_bins = max(4, int(histogram_bins))
        series_ids = parse_graph_series_csv(series_csv)
        self._series_ids = list(series_ids)
        if not self._enabled:
            self._status.setText("graphs: disabled")
        elif not self._plot_available:
            self._status.setText(
                "graphs: no canvas (matplotlib backend unavailable)"
                + (f" [{self._plot_error}]" if self._plot_error else "")
            )
        else:
            self._status.setText(
                f"graphs: {len(self._series_ids)} series, window={int(self._window_steps)}, ids={','.join(self._series_ids)}"
            )

    def update(
        self,
        *,
        snapshot: Mapping[str, Any],
        energy_field: Any | None = None,
        anchor_summary: Mapping[str, Any] | None = None,
    ) -> None:
        payload = dict(snapshot)
        if not self._enabled or not payload:
            return
        tick = int(payload.get("tick", len(self._samples)))
        if int(tick) == int(self._last_tick):
            return
        self._last_tick = int(tick)
        if energy_field is not None:
            arr = np.asarray(energy_field, dtype=np.float32)
            if arr.size > 0:
                self._latest_energy_field = arr.reshape(-1)
        if anchor_summary is not None:
            self._anchor_summary = {str(k): v for k, v in dict(anchor_summary).items()}
        values = extract_graph_series_values(snapshot=payload, series_ids=self._series_ids)
        self._samples.append({"tick": int(tick), "values": values})
        preview = ", ".join(f"{sid}={float(values.get(sid, 0.0)):.3g}" for sid in self._series_ids)
        detected = int(self._anchor_summary.get("detected", 0))
        captured = int(self._anchor_summary.get("captured", 0))
        self._status.setText(f"graphs: tick={int(tick)} [{preview}] anchors={captured}/{detected}")
        self._render()

    def _render(self) -> None:
        if (
            (not self._plot_available)
            or self._axis_series is None
            or self._axis_hist is None
            or self._canvas is None
        ):
            return
        self._axis_series.clear()
        self._axis_hist.clear()
        rows = list(self._samples)
        if not rows:
            self._axis_series.set_title("DETM Graphs")
            self._axis_series.set_xlabel("tick")
            self._axis_series.set_ylabel("value")
            self._axis_hist.set_title("E histogram")
            self._axis_hist.set_xlabel("energy")
            self._axis_hist.set_ylabel("count")
            self._canvas.draw_idle()
            return

        ticks = [int(row.get("tick", 0)) for row in rows]
        for series_id in self._series_ids:
            ys = [float(dict(row.get("values", {})).get(series_id, 0.0)) for row in rows]
            self._axis_series.plot(ticks, ys, label=series_id, linewidth=1.5)
        self._axis_series.set_title("Time Series")
        self._axis_series.set_xlabel("tick")
        self._axis_series.grid(True, alpha=0.25)
        self._axis_series.legend(loc="upper left", ncol=2, fontsize=8)

        self._axis_hist.set_title("E histogram")
        self._axis_hist.set_xlabel("energy")
        self._axis_hist.set_ylabel("count")
        if self._hist_enabled and self._latest_energy_field is not None:
            finite = np.asarray(self._latest_energy_field, dtype=np.float64)
            finite = finite[np.isfinite(finite)]
            if finite.size > 0:
                bins = _build_histogram_bins(finite, int(self._hist_bins))
                self._axis_hist.hist(finite, bins=bins, color="#4C78A8", alpha=0.8)
                self._axis_hist.grid(True, alpha=0.2)
            else:
                self._axis_hist.text(0.5, 0.5, "no finite values", ha="center", va="center")
        else:
            self._axis_hist.text(0.5, 0.5, "hist off", ha="center", va="center")
        self._canvas.draw_idle()


__all__ = [
    "DEFAULT_GRAPH_SERIES",
    "GRAPH_SERIES_REGISTRY",
    "GraphSeriesSpec",
    "NapariGraphDock",
    "available_graph_series_ids",
    "extract_graph_series_values",
    "parse_graph_series_csv",
    "register_graph_series",
]
