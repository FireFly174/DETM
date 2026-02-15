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

from detm.runtime.symbols import list_symbols
from detm_app.config.app_settings import build_runtime_config, build_ui_overrides, load_merged_payload
from detm_app.config.ui_models import UiRunSettings
from detm_app.runner.batch_service import parse_batch_symbols_csv
from detm_app.runtime.ui_runtime import DetmUiRunner
from detm_app.ui.napari.interactive.controller import _InteractiveDockController
from detm_app.ui.napari.interactive.helpers import (
    build_quiver_vectors as _build_quiver_vectors,
    resolve_influence_policy as _resolve_influence_policy,
)
from detm_app.ui.napari.subscriber import _patch_six_meta_path_importer


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


def run_napari_interactive(
    *,
    preset: str = "default",
    override_path: str | None = None,
    autoscale: bool = True,
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
        parse_symbol_csv=_parse_symbol_csv,
    )
    try:
        from qtpy import QtWidgets

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(controller.close)
    except Exception:
        pass
    try:
        qt_window = getattr(getattr(viewer, "window", None), "_qt_window", None)
        if qt_window is not None and hasattr(qt_window, "destroyed"):
            qt_window.destroyed.connect(lambda *_args: controller.close())
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
