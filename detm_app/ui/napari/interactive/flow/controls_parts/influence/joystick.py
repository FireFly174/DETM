#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Joystick controls for the influence page."""

from __future__ import annotations

from typing import Any


def add_joystick_group(
    controller: Any,
    *,
    parent_layout: Any,
    QtWidgets: Any,
    QtCore: Any,
    settings: Any,
) -> None:
    self = controller
    from qtpy import QtGui

    self._joystick_group = QtWidgets.QGroupBox("Joystick field")
    joystick_layout = QtWidgets.QVBoxLayout(self._joystick_group)
    self._joy_dx = QtWidgets.QSlider(self._QtCore.Qt.Horizontal)
    self._joy_dx.setRange(-100, 100)
    self._joy_dx.setValue(int(round(float(settings.joy_dx) * 100.0)))
    self._joy_dy = QtWidgets.QSlider(self._QtCore.Qt.Horizontal)
    self._joy_dy.setRange(-100, 100)
    self._joy_dy.setValue(int(round(float(settings.joy_dy) * 100.0)))
    row_dx = QtWidgets.QHBoxLayout()
    row_dx.addWidget(QtWidgets.QLabel("joy_dx"))
    row_dx.addWidget(self._joy_dx)
    row_dy = QtWidgets.QHBoxLayout()
    row_dy.addWidget(QtWidgets.QLabel("joy_dy"))
    row_dy.addWidget(self._joy_dy)
    joystick_layout.addLayout(row_dx)
    joystick_layout.addLayout(row_dy)

    class _JoystickPad(QtWidgets.QWidget):
        def __init__(self, *, on_change: Any, dx: int, dy: int) -> None:
            super().__init__()
            self.setMinimumSize(120, 120)
            self._on_change = on_change
            self._dx = int(max(-100, min(100, dx)))
            self._dy = int(max(-100, min(100, dy)))
            self._dragging = False

        def set_values(self, *, dx: int, dy: int, emit: bool = False) -> None:
            self._dx = int(max(-100, min(100, dx)))
            self._dy = int(max(-100, min(100, dy)))
            self.update()
            if emit:
                self._on_change(self._dx, self._dy)

        def _update_from_pos(self, pos: Any) -> None:
            w = max(1, int(self.width()))
            h = max(1, int(self.height()))
            cx = 0.5 * float(w)
            cy = 0.5 * float(h)
            r = 0.45 * float(min(w, h))
            px = float(pos.x()) - cx
            py = float(pos.y()) - cy
            if r <= 1e-6:
                return
            nx = px / r
            ny = -py / r
            d = float((nx * nx + ny * ny) ** 0.5)
            if d > 1.0:
                nx /= d
                ny /= d
            self.set_values(dx=int(round(nx * 100.0)), dy=int(round(ny * 100.0)), emit=True)

        def mousePressEvent(self, event: Any) -> None:
            if event.button() == QtCore.Qt.LeftButton:
                self._dragging = True
                self._update_from_pos(event.position() if hasattr(event, "position") else event.pos())
                event.accept()
                return
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event: Any) -> None:
            if self._dragging:
                self._update_from_pos(event.position() if hasattr(event, "position") else event.pos())
                event.accept()
                return
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event: Any) -> None:
            if event.button() == QtCore.Qt.LeftButton:
                self._dragging = False
                event.accept()
                return
            super().mouseReleaseEvent(event)

        def paintEvent(self, _event: Any) -> None:
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            w = float(self.width())
            h = float(self.height())
            cx = 0.5 * w
            cy = 0.5 * h
            r = 0.45 * min(w, h)
            p.fillRect(self.rect(), QtGui.QColor("#1b1f2a"))
            p.setPen(QtGui.QPen(QtGui.QColor("#6f7787"), 1))
            p.drawEllipse(QtCore.QPointF(cx, cy), r, r)
            p.drawLine(QtCore.QPointF(cx - r, cy), QtCore.QPointF(cx + r, cy))
            p.drawLine(QtCore.QPointF(cx, cy - r), QtCore.QPointF(cx, cy + r))
            kx = cx + (float(self._dx) / 100.0) * r
            ky = cy - (float(self._dy) / 100.0) * r
            p.setPen(QtGui.QPen(QtGui.QColor("#f3f3f3"), 1))
            p.setBrush(QtGui.QBrush(QtGui.QColor("#ffd84d")))
            p.drawEllipse(QtCore.QPointF(kx, ky), 6.0, 6.0)
            p.end()

    self._joy_sync = False

    def _on_pad_change(dx: int, dy: int) -> None:
        if self._joy_sync:
            return
        self._joy_sync = True
        self._joy_dx.setValue(int(dx))
        self._joy_dy.setValue(int(dy))
        self._joy_sync = False

    self._joystick_pad = _JoystickPad(
        on_change=_on_pad_change,
        dx=int(self._joy_dx.value()),
        dy=int(self._joy_dy.value()),
    )
    joystick_layout.addWidget(self._joystick_pad)

    def _sync_pad_from_sliders(_value: int = 0) -> None:
        if self._joy_sync:
            return
        self._joy_sync = True
        self._joystick_pad.set_values(dx=int(self._joy_dx.value()), dy=int(self._joy_dy.value()), emit=False)
        self._joy_sync = False

    self._joy_dx.valueChanged.connect(_sync_pad_from_sliders)
    self._joy_dy.valueChanged.connect(_sync_pad_from_sliders)
    joy_btn_row = QtWidgets.QHBoxLayout()
    joy_center_btn = QtWidgets.QPushButton("Center joystick")
    joy_center_btn.clicked.connect(lambda: self._joystick_pad.set_values(dx=0, dy=0, emit=True))
    joy_btn_row.addWidget(joy_center_btn)
    joystick_layout.addLayout(joy_btn_row)
    parent_layout.addWidget(self._joystick_group)


__all__ = ["add_joystick_group"]
