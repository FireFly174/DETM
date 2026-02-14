#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Widget I/O helpers for napari interactive controller."""

from __future__ import annotations

from typing import Any

from detm_app.ui.napari.interactive.helpers import to_float as _to_float, to_int as _to_int


def line(
    controller: Any,
    *,
    label: str,
    value: str,
    parent_layout: Any | None = None,
    tooltip: str = "",
) -> tuple[Any, Any]:
    self = controller
    layout = self._layout if parent_layout is None else parent_layout
    row = self._QtWidgets.QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)
    lbl = self._QtWidgets.QLabel(str(label))
    edit = self._QtWidgets.QLineEdit(str(value))
    if tooltip:
        lbl.setToolTip(str(tooltip))
        edit.setToolTip(str(tooltip))
    row.addWidget(lbl)
    row.addWidget(edit)
    layout.addLayout(row)
    return lbl, edit


def read_text(controller: Any, widget: Any, default: str = "") -> str:
    _ = controller
    if hasattr(widget, "text"):
        try:
            return str(widget.text())
        except Exception:
            return str(default)
    if hasattr(widget, "currentText"):
        try:
            return str(widget.currentText())
        except Exception:
            return str(default)
    return str(default)


def read_int(controller: Any, widget: Any, default: int) -> int:
    self = controller
    if hasattr(widget, "value"):
        try:
            return int(widget.value())
        except Exception:
            return int(default)
    return _to_int(read_text(self, widget, str(default)), default)


def read_float(controller: Any, widget: Any, default: float) -> float:
    self = controller
    if hasattr(widget, "value"):
        try:
            return float(widget.value())
        except Exception:
            return float(default)
    return _to_float(read_text(self, widget, str(default)), default)


__all__ = ["line", "read_text", "read_int", "read_float"]
