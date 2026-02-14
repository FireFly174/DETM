#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Influence/geometry handlers for napari interactive controller."""

from __future__ import annotations

from typing import Any


def sync_geometry_bounds(controller: Any) -> None:
    self = controller
    width = max(1, self._read_int(self._width, int(self._settings.config.width)))
    height = max(1, self._read_int(self._height, int(self._settings.config.height)))
    self._patch_cx.setMaximum(max(0, width - 1))
    self._patch_cy.setMaximum(max(0, height - 1))
    self._source_x.setMaximum(max(0, width - 1))
    self._sink_x.setMaximum(max(0, width - 1))
    self._source_y.setMaximum(max(0, height - 1))
    self._sink_y.setMaximum(max(0, height - 1))
    self._patch_radius.setMaximum(max(1, max(width, height)))


def on_influence_mode_change(controller: Any, mode: str) -> None:
    self = controller
    mode_name = str(mode or "").strip().lower()
    symbol_mode = mode_name == "symbol"
    joystick_mode = mode_name == "joystick_field"
    patch_mode = mode_name == "joystick_patch"
    source_sink_mode = mode_name == "source_sink"
    self._symbol_group.setVisible(symbol_mode)
    self._joystick_group.setVisible(joystick_mode)
    self._patch_group.setVisible(patch_mode)
    self._source_sink_group.setVisible(source_sink_mode)


def on_influence_policy_change(controller: Any, policy: str) -> None:
    self = controller
    mode = str(policy or "").strip().lower()
    self._duration.setEnabled(mode == "pulse")


__all__ = [
    "sync_geometry_bounds",
    "on_influence_mode_change",
    "on_influence_policy_change",
]
