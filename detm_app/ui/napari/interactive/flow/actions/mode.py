#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Mode-related action handlers for napari interactive controller."""

from __future__ import annotations

from typing import Any


def mode_is_batch(controller: Any) -> bool:
    self = controller
    return str(self._mode_combo.currentText()).strip().lower() == "batch"


def on_mode_change(controller: Any) -> None:
    self = controller
    batch_mode = mode_is_batch(self)
    if batch_mode and self._running:
        self._running = False
        self._timer.stop()
        self._btn_run.setText("Run")
    self._btn_reset.setEnabled(not batch_mode)
    self._btn_step.setEnabled(not batch_mode)
    self._btn_run.setEnabled(not batch_mode)
    self._btn_run.setText("Run")
    self._btn_batch.setVisible(batch_mode)
    try:
        self._toolbox.setItemEnabled(int(self._batch_page_index), bool(batch_mode))
        if batch_mode:
            self._toolbox.setCurrentIndex(int(self._batch_page_index))
    except Exception:
        pass
    if not batch_mode:
        self._render(force_autoscale=True)


__all__ = ["mode_is_batch", "on_mode_change"]
