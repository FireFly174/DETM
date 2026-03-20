#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Rendering helpers for napari interactive controller."""

from __future__ import annotations

from collections import deque
from typing import Any, Mapping

import numpy as np

from detm.runtime.diagnostics.attractors import detect_attractors
from detm_app.ui.napari.interactive.helpers import (
    build_quiver_vectors as _build_quiver_vectors,
    format_projection_plane_label as _format_projection_plane_label,
)
from detm_app.ui.napari.subscriber import state_to_layers

try:
    from legacy.utils.signal import phase_from_peaks as _phase_from_peaks
    from legacy.utils.signal import local_phase_via_quadrature as _local_phase_via_quadrature
except Exception:  # pragma: no cover - optional legacy helper
    _phase_from_peaks = None
    _local_phase_via_quadrature = None


class NapariRenderFlow:
    def __init__(
        self,
        *,
        viewer: Any,
        field_layer_name: str = "field",
        quiver_layer_name: str = "quiver",
        colormap_map: Mapping[str, str] | None = None,
    ) -> None:
        self._viewer = viewer
        self._field_layer_name = str(field_layer_name)
        self._quiver_layer_name = str(quiver_layer_name)
        self._anchor_layer_name = "anchors"
        self._anchor_capture_layer_name = "anchor_captures"
        self._colormap_map = dict(colormap_map or {"gray": "gray", "heat": "inferno"})
        self._anchor_tracks: dict[int, dict[str, Any]] = {}
        self._next_anchor_id = 1
        self._last_anchor_tick = -1
        self._legacy_t: deque[float] = deque(maxlen=512)
        self._legacy_a: deque[float] = deque(maxlen=512)
        self._legacy_p: deque[float] = deque(maxlen=512)
        self._legacy_phi: deque[float] = deque(maxlen=512)
        self._legacy_t_period: deque[float] = deque(maxlen=512)
        self._probe_points: list[tuple[int, int]] | None = None
        self._probe_buffers: list[deque[float]] | None = None
        self._probe_anchor_x: int = -1
        self._probe_shape: tuple[int, int] | None = None

    def render(
        self,
        *,
        runner: Any,
        settings: Any,
        status_widget: Any,
        field_name: str,
        plane_index: tuple[int, ...] | None,
        cmap_name: str,
        quiver_enabled: bool,
        quiver_step: int,
        quiver_scale: float,
        autoscale: bool,
        anchors_enabled: bool,
        anchors_top_k: int,
        anchors_threshold: float,
        anchors_capture_ticks: int,
    ) -> dict[str, Any]:
        state = runner.state
        layers = state_to_layers(state, plane_index=plane_index)
        field = np.asarray(
            layers.get(str(field_name).strip().lower() or "energy", layers["energy"]),
            dtype=np.float32,
        )
        energy_field = np.asarray(layers.get("energy", field), dtype=np.float32)
        self._ensure_field_layer(field=field, cmap_name=str(cmap_name), autoscale=bool(autoscale))

        if bool(quiver_enabled):
            vectors = _build_quiver_vectors(field, step=max(1, int(quiver_step)), scale=max(0.0, float(quiver_scale)))
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

        anchor_summary = self._update_anchor_layers(
            energy_field=energy_field,
            tick=int(state.step_count),
            enabled=bool(anchors_enabled),
            top_k=max(1, int(anchors_top_k)),
            threshold=max(0.0, float(anchors_threshold)),
            capture_ticks=max(1, int(anchors_capture_ticks)),
        )
        legacy_metrics = self._update_legacy_metrics(
            energy_field=energy_field,
            tick=int(state.step_count),
            anchor_summary=anchor_summary,
        )

        signature = list(runner.last_observables or [])
        dyn = settings.config.dynamics
        learning = ""
        if hasattr(runner, "learning_status_compact"):
            learning = str(runner.learning_status_compact(max_len=96))
        invariant_status = ""
        if hasattr(runner, "invariant_status_compact"):
            invariant_status = str(runner.invariant_status_compact() or "")
        requested_backend = f"{settings.config.backend}/{settings.config.device}"
        runtime_backend = (
            str(runner.runtime_backend_label())
            if hasattr(runner, "runtime_backend_label")
            else str(requested_backend)
        )
        view_text = _format_projection_plane_label(plane_index)
        backend_text = runtime_backend
        if runtime_backend != requested_backend:
            backend_text = f"{runtime_backend} (requested={requested_backend})"
        anchors_text = f" anchors={int(anchor_summary.get('captured', 0))}/{int(anchor_summary.get('detected', 0))}"
        A_t = float(legacy_metrics.get("A_t", np.nan))
        P_t = float(legacy_metrics.get("P_t", np.nan))
        T_t = float(legacy_metrics.get("T_t", np.nan))
        legacy_text = (
            f" A={A_t:.3g} P={P_t:.3g} T={T_t:.3g}"
            if np.isfinite(A_t) and np.isfinite(P_t)
            else ""
        )
        status_widget.setText(
            "tick="
            + str(int(state.step_count))
            + " sig0..3="
            + str(signature[:4])
            + " backend="
            + backend_text
            + " view="
            + view_text
            + " boundary="
            + str(settings.config.boundary)
            + " a,b,k,g,t="
            + f"[{dyn.alpha:.3g},{dyn.beta:.3g},{dyn.kappa:.3g},{dyn.gamma:.3g},{dyn.lambda_t:.3g}]"
            + anchors_text
            + legacy_text
            + (" " + invariant_status if invariant_status else "")
            + (" " + learning if learning else "")
        )
        return {
            "energy_field": energy_field,
            "anchor_summary": anchor_summary,
            "legacy_metrics": legacy_metrics,
        }

    def _layer_by_name(self, name: str) -> Any | None:
        try:
            if name in self._viewer.layers:
                return self._viewer.layers[name]
        except Exception:
            return None
        return None

    def _clear_anchor_layers(self) -> None:
        self._anchor_tracks = {}
        self._next_anchor_id = 1
        for layer_name in [self._anchor_layer_name, self._anchor_capture_layer_name]:
            if self._layer_by_name(layer_name) is None:
                continue
            try:
                self._viewer.layers.remove(layer_name)
            except Exception:
                try:
                    del self._viewer.layers[layer_name]
                except Exception:
                    pass

    def _set_points_layer(
        self,
        *,
        layer_name: str,
        points: np.ndarray,
        size: float,
        face_color: str,
        edge_color: str,
        opacity: float = 0.9,
        symbol: str = "disc",
    ) -> None:
        layer = self._layer_by_name(layer_name)
        if points.size <= 0:
            if layer is not None:
                try:
                    self._viewer.layers.remove(layer_name)
                except Exception:
                    try:
                        del self._viewer.layers[layer_name]
                    except Exception:
                        pass
            return
        if layer is None:
            base_kwargs = {
                "name": layer_name,
                "size": float(size),
                "face_color": str(face_color),
                "opacity": float(opacity),
                "symbol": str(symbol),
            }
            try:
                self._viewer.add_points(points, edge_color=str(edge_color), **base_kwargs)
            except Exception:
                # napari API compatibility: older/newer versions may expose
                # border_color instead of edge_color for Points.
                try:
                    self._viewer.add_points(points, border_color=str(edge_color), **base_kwargs)
                except Exception:
                    fallback = dict(base_kwargs)
                    fallback.pop("symbol", None)
                    self._viewer.add_points(points, **fallback)
        else:
            layer.data = points
            try:
                layer.size = float(size)
                layer.face_color = str(face_color)
                layer.opacity = float(opacity)
                if hasattr(layer, "symbol"):
                    layer.symbol = str(symbol)
                if hasattr(layer, "edge_color"):
                    layer.edge_color = str(edge_color)
                elif hasattr(layer, "border_color"):
                    layer.border_color = str(edge_color)
            except Exception:
                pass

    def _update_anchor_layers(
        self,
        *,
        energy_field: np.ndarray,
        tick: int,
        enabled: bool,
        top_k: int,
        threshold: float,
        capture_ticks: int,
    ) -> dict[str, Any]:
        if not bool(enabled):
            self._clear_anchor_layers()
            self._last_anchor_tick = int(tick)
            return {"detected": 0, "captured": 0, "max_streak": 0}

        if int(tick) < int(self._last_anchor_tick):
            self._anchor_tracks = {}
            self._next_anchor_id = 1
        self._last_anchor_tick = int(tick)

        anchors = detect_attractors(energy_field, threshold=float(threshold), top_k=max(1, int(top_k)))
        previous_tracks = {
            int(track_id): dict(payload)
            for track_id, payload in dict(self._anchor_tracks).items()
            if int(payload.get("last_tick", -10_000)) >= int(tick) - max(1, int(capture_ticks) * 2)
        }

        used_prev: set[int] = set()
        updated_tracks: dict[int, dict[str, Any]] = {}
        all_points: list[list[float]] = []
        captured_points: list[list[float]] = []
        max_streak = 0
        for anchor in anchors:
            x, y = anchor.position
            best_id = -1
            best_dist = 1e9
            for track_id, payload in previous_tracks.items():
                if track_id in used_prev:
                    continue
                px = float(payload.get("x", -1.0))
                py = float(payload.get("y", -1.0))
                dist = float(((float(x) - px) ** 2 + (float(y) - py) ** 2) ** 0.5)
                if dist <= 1.75 and dist < best_dist:
                    best_dist = dist
                    best_id = int(track_id)
            if best_id >= 0:
                used_prev.add(best_id)
                streak = int(previous_tracks[best_id].get("streak", 0)) + 1
                track_id = int(best_id)
            else:
                streak = 1
                track_id = int(self._next_anchor_id)
                self._next_anchor_id += 1
            max_streak = max(max_streak, int(streak))
            payload = {
                "x": float(x),
                "y": float(y),
                "streak": int(streak),
                "last_tick": int(tick),
                "strength": float(getattr(anchor, "strength", 0.0)),
            }
            updated_tracks[track_id] = payload
            all_points.append([float(y), float(x)])
            if int(streak) >= int(capture_ticks):
                captured_points.append([float(y), float(x)])

        self._anchor_tracks = updated_tracks
        grid_scale = float(max(1.0, min(float(energy_field.shape[0]), float(energy_field.shape[1]))))
        base_size = float(np.clip(grid_scale / 12.0, 2.0, 6.0))
        capture_size = float(np.clip(base_size * 1.35, 2.75, 8.0))
        all_data = np.asarray(all_points, dtype=np.float32).reshape((-1, 2)) if all_points else np.empty((0, 2), dtype=np.float32)
        captured_data = (
            np.asarray(captured_points, dtype=np.float32).reshape((-1, 2))
            if captured_points
            else np.empty((0, 2), dtype=np.float32)
        )
        self._set_points_layer(
            layer_name=self._anchor_layer_name,
            points=all_data,
            size=base_size,
            face_color="transparent",
            edge_color="cyan",
            opacity=0.95,
            symbol="ring",
        )
        self._set_points_layer(
            layer_name=self._anchor_capture_layer_name,
            points=captured_data,
            size=capture_size,
            face_color="magenta",
            edge_color="white",
            opacity=0.7,
            symbol="disc",
        )
        return {
            "detected": int(len(all_points)),
            "captured": int(len(captured_points)),
            "max_streak": int(max_streak),
            "best_anchor_y": int(all_points[0][0]) if len(all_points) > 0 else -1,
            "best_anchor_x": int(all_points[0][1]) if len(all_points) > 0 else -1,
        }

    def _reset_probe_state(self) -> None:
        self._probe_points = None
        self._probe_buffers = None
        self._probe_anchor_x = -1
        self._probe_shape = None

    def _ensure_probe_state(self, *, anchor_y: int, anchor_x: int, shape: tuple[int, int]) -> None:
        h, w = int(shape[0]), int(shape[1])
        if h <= 0 or w <= 0:
            self._reset_probe_state()
            return
        ax = int(anchor_x) % w
        reuse = (
            self._probe_points is not None
            and self._probe_buffers is not None
            and self._probe_shape == (h, w)
            and abs(int(self._probe_anchor_x) - int(ax)) <= 1
        )
        if reuse:
            return
        step = max(1, int(round(h / 12.0)))
        probe_points = [(int(y), int(ax)) for y in range(0, h, step)]
        if len(probe_points) <= 0:
            probe_points = [(int(h // 2), int(ax))]
        self._probe_points = list(probe_points)
        self._probe_buffers = [deque(maxlen=512) for _ in probe_points]
        self._probe_anchor_x = int(ax)
        self._probe_shape = (h, w)

    def _append_probe_samples(self, *, energy_field: np.ndarray) -> None:
        if self._probe_points is None or self._probe_buffers is None:
            return
        h, w = int(energy_field.shape[0]), int(energy_field.shape[1])
        for idx, (yy, xx) in enumerate(self._probe_points):
            y = int(yy) % h
            x = int(xx) % w
            self._probe_buffers[idx].append(float(energy_field[y, x]))

    def _update_legacy_metrics(
        self,
        *,
        energy_field: np.ndarray,
        tick: int,
        anchor_summary: Mapping[str, Any],
    ) -> dict[str, float]:
        gy, gx = np.gradient(np.asarray(energy_field, dtype=np.float32))
        A_t = float(np.sqrt(np.mean(gx**2 + gy**2)))
        h, w = energy_field.shape
        ay = int(anchor_summary.get("best_anchor_y", -1))
        ax = int(anchor_summary.get("best_anchor_x", -1))
        if ay < 0 or ax < 0:
            ay = int(h // 2)
            ax = int(w // 2)

        vals: list[float] = []
        r_in = 2
        r_out = 5
        for dy in range(-r_out, r_out + 1):
            for dx in range(-r_out, r_out + 1):
                rr = abs(dy) + abs(dx)
                if rr < r_in or rr >= r_out:
                    continue
                yy = (ay + dy) % h
                xx = (ax + dx) % w
                vals.append(float(energy_field[yy, xx]))
        if len(vals) >= 6:
            P_t = float(np.std(np.asarray(vals, dtype=np.float32)))
        else:
            P_t = float(energy_field[ay, ax])

        self._legacy_t.append(float(tick))
        self._legacy_a.append(float(A_t))
        self._legacy_p.append(float(P_t))

        T_t = float("nan")
        phi_last = float("nan")
        n_peaks = 0
        if _phase_from_peaks is not None and len(self._legacy_p) >= 12:
            p_arr = np.asarray(list(self._legacy_p), dtype=float)
            t_arr = np.asarray(list(self._legacy_t), dtype=float)
            phi_arr, t_inst, peaks = _phase_from_peaks(
                p_arr,
                t_arr,
                min_period=4,
                max_period=max(16, int(len(p_arr))),
                smooth_win=5,
                prominence=0.0,
            )
            n_peaks = int(len(peaks or []))
            if t_inst is not None and len(t_inst) > 0 and np.isfinite(float(t_inst[-1])):
                T_t = float(t_inst[-1])
            if phi_arr is not None and len(phi_arr) > 0 and np.isfinite(float(phi_arr[-1])):
                phi_last = float(phi_arr[-1])
        self._legacy_t_period.append(float(T_t))
        self._legacy_phi.append(float(phi_last))

        self._ensure_probe_state(anchor_y=int(ay), anchor_x=int(ax), shape=(int(h), int(w)))
        self._append_probe_samples(energy_field=np.asarray(energy_field, dtype=np.float32))

        freeze_mean = float("nan")
        freeze_min = float("nan")
        locked_frac = float("nan")
        a3_plv_mean = float("nan")
        a3_var_mean = float("nan")

        if _local_phase_via_quadrature is not None and self._probe_buffers is not None and self._probe_points is not None:
            win = min(
                64,
                int(len(self._legacy_phi)),
                min((int(len(buf)) for buf in self._probe_buffers), default=0),
            )
            if win >= 8:
                phi_window = np.asarray(list(self._legacy_phi)[-win:], dtype=float)
                if np.all(np.isfinite(phi_window)):
                    probe_vars: list[float] = []
                    probe_plvs: list[float] = []
                    probe_radii: list[int] = []
                    for idx, buf in enumerate(self._probe_buffers):
                        sig = np.asarray(list(buf)[-win:], dtype=float)
                        if sig.size < win:
                            continue
                        _theta_last, plv, var = _local_phase_via_quadrature(sig, phi_window, win=win)
                        if not (np.isfinite(float(plv)) and np.isfinite(float(var))):
                            continue
                        probe_plvs.append(float(plv))
                        probe_vars.append(float(var))
                        yy, xx = self._probe_points[idx]
                        radius = int(abs(int(yy) - int(ay)) + abs(int(xx) - int(ax)))
                        probe_radii.append(max(0, radius))
                    if len(probe_vars) > 0:
                        var_arr = np.asarray(probe_vars, dtype=float)
                        freeze_mean = float(np.mean(var_arr))
                        freeze_min = float(np.min(var_arr))
                        locked_frac = float(np.mean(var_arr <= 0.05))

                    if len(probe_radii) > 0 and len(probe_plvs) == len(probe_radii):
                        per_r_plv: dict[int, list[float]] = {}
                        per_r_var: dict[int, list[float]] = {}
                        for r, plv, var in zip(probe_radii, probe_plvs, probe_vars):
                            per_r_plv.setdefault(int(r), []).append(float(plv))
                            per_r_var.setdefault(int(r), []).append(float(var))
                        radial_rs = sorted(per_r_plv.keys())
                        radial_plv = np.asarray([float(np.mean(per_r_plv[r])) for r in radial_rs], dtype=float)
                        radial_var = np.asarray([float(np.mean(per_r_var[r])) for r in radial_rs], dtype=float)
                        if radial_plv.size > 0:
                            a3_plv_mean = float(np.mean(radial_plv))
                        if radial_var.size > 0:
                            a3_var_mean = float(np.mean(radial_var))

        return {
            "A_t": float(A_t),
            "P_t": float(P_t),
            "T_t": float(T_t),
            "n_peaks": float(n_peaks),
            "freeze_mean": float(freeze_mean),
            "freeze_min": float(freeze_min),
            "locked_frac": float(locked_frac),
            "a3_plv_mean": float(a3_plv_mean),
            "a3_var_mean": float(a3_var_mean),
        }

    def _ensure_field_layer(self, *, field: np.ndarray, cmap_name: str, autoscale: bool) -> None:
        field_layer = self._layer_by_name(self._field_layer_name)
        if field_layer is None:
            field_layer = self._viewer.add_image(field, name=self._field_layer_name)
        else:
            field_layer.data = field
        # Preserve lattice-cell readability on startup (avoid blurred interpolation).
        try:
            field_layer.interpolation2d = "nearest"
        except Exception:
            pass
        cmap = self._colormap_map.get(str(cmap_name).strip().lower(), "inferno")
        try:
            field_layer.colormap = cmap
        except Exception:
            pass
        if bool(autoscale):
            finite = np.asarray(field[np.isfinite(field)], dtype=np.float32)
            if finite.size <= 0:
                return
            # Robust autoscale stabilizes first-look contrast under occasional outliers.
            vmin = float(np.nanpercentile(finite, 1.0))
            vmax = float(np.nanpercentile(finite, 99.0))
            if not (np.isfinite(vmin) and np.isfinite(vmax) and vmin < vmax):
                vmin = float(np.nanmin(finite))
                vmax = float(np.nanmax(finite))
            if np.isfinite(vmin) and np.isfinite(vmax) and vmin < vmax:
                field_layer.contrast_limits = (vmin, vmax)


__all__ = ["NapariRenderFlow"]
