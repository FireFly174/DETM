#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Controls-builder helpers for napari interactive controller."""

from __future__ import annotations

from typing import Any

from detm_app.config.tooltips import load_tooltips_from_config_default
from detm_app.ui.napari.interactive.flow.controls_parts.influence import add_influence_page
from detm_app.ui.napari.interactive.flow.controls_parts.recording_batch import (
    add_batch_page,
    add_recording_page,
)
from detm_app.ui.napari.interactive.flow.controls_parts.view_runtime import (
    add_runtime_page,
    add_view_page,
)


def build_interactive_controls(controller: Any) -> None:
    self = controller
    QtWidgets = self._QtWidgets
    QtCore = self._QtCore
    settings = self._settings
    cfg = settings.config
    tips = load_tooltips_from_config_default()

    self._toolbox = QtWidgets.QToolBox()
    self._layout.addWidget(self._toolbox, 1)

    add_view_page(self, QtWidgets=QtWidgets, settings=settings)
    add_runtime_page(self, QtWidgets=QtWidgets, cfg=cfg, tips=tips)
    add_influence_page(self, QtWidgets=QtWidgets, QtCore=QtCore, settings=settings, cfg=cfg)
    add_recording_page(self, QtWidgets=QtWidgets, settings=settings, tips=tips)
    add_batch_page(self, QtWidgets=QtWidgets)

    self._on_influence_mode_change(self._influence_mode.currentText())
    self._on_influence_policy_change(self._influence_policy.currentText())




__all__ = ["build_interactive_controls"]
