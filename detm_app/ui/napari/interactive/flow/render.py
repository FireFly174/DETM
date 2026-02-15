#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Rendering helpers for napari interactive controller."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from detm_app.ui.napari.interactive.helpers import build_quiver_vectors as _build_quiver_vectors
from detm_app.ui.napari.subscriber import state_to_layers


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
        self._colormap_map = dict(colormap_map or {"gray": "gray", "heat": "inferno"})

    def render(
        self,
        *,
        runner: Any,
        settings: Any,
        status_widget: Any,
        field_name: str,
        cmap_name: str,
        quiver_enabled: bool,
        quiver_step: int,
        quiver_scale: float,
        autoscale: bool,
    ) -> None:
        state = runner.state
        layers = state_to_layers(state)
        field = np.asarray(
            layers.get(str(field_name).strip().lower() or "energy", layers["energy"]),
            dtype=np.float32,
        )
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

        signature = list(runner.last_observables or [])
        dyn = settings.config.dynamics
        status_widget.setText(
            "tick="
            + str(int(state.step_count))
            + " sig0..3="
            + str(signature[:4])
            + " backend="
            + f"{settings.config.backend}/{settings.config.device}"
            + " boundary="
            + str(settings.config.boundary)
            + " a,b,k,g,t="
            + f"[{dyn.alpha:.3g},{dyn.beta:.3g},{dyn.kappa:.3g},{dyn.gamma:.3g},{dyn.lambda_t:.3g}]"
        )

    def _layer_by_name(self, name: str) -> Any | None:
        try:
            if name in self._viewer.layers:
                return self._viewer.layers[name]
        except Exception:
            return None
        return None

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
