#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Interaction action handlers for napari interactive controller."""

from __future__ import annotations

from typing import Any

from detm_app.ui.napari.interactive.flow.actions.mode import mode_is_batch


def on_apply(controller: Any) -> None:
    self = controller
    if self._closing:
        return
    if mode_is_batch(self):
        self._apply_settings(reset=False)
        return
    self._apply_settings(reset=False)
    self._render(force_autoscale=True)


def on_reset(controller: Any) -> None:
    self = controller
    if self._closing:
        return
    if mode_is_batch(self):
        return
    self._apply_settings(reset=True)
    self._render(force_autoscale=True)


def on_step(controller: Any) -> None:
    self = controller
    if self._closing:
        return
    if mode_is_batch(self):
        return
    self._apply_settings(reset=False)
    self._runner.step_once()
    self._render()


def on_run_toggle(controller: Any) -> None:
    self = controller
    if self._closing:
        return
    if mode_is_batch(self):
        self._on_batch_toggle()
        return
    self._apply_settings(reset=False)
    self._running = not bool(self._running)
    self._btn_run.setText("Stop" if self._running else "Run")
    if self._running:
        self._timer.start()
    else:
        self._timer.stop()


__all__ = ["on_apply", "on_reset", "on_step", "on_run_toggle"]
