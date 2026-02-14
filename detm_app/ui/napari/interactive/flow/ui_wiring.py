#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UI wiring helpers (buttons/shortcuts) for napari interactive controller."""

from __future__ import annotations

from typing import Any


def build_buttons(controller: Any) -> None:
    self = controller
    QtWidgets = self._QtWidgets
    row = QtWidgets.QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)

    self._btn_reset = QtWidgets.QPushButton("Reset")
    self._btn_step = QtWidgets.QPushButton("Step")
    self._btn_run = QtWidgets.QPushButton("Run")
    self._btn_apply = QtWidgets.QPushButton("Apply")
    self._btn_batch = QtWidgets.QPushButton("Run batch")

    self._btn_reset.clicked.connect(self._on_reset)
    self._btn_step.clicked.connect(self._on_step)
    self._btn_run.clicked.connect(self._on_run_toggle)
    self._btn_apply.clicked.connect(self._on_apply)
    self._btn_batch.clicked.connect(self._on_batch_toggle)

    row.addWidget(self._btn_reset)
    row.addWidget(self._btn_step)
    row.addWidget(self._btn_run)
    row.addWidget(self._btn_apply)
    row.addWidget(self._btn_batch)
    self._layout.addLayout(row)


def install_shortcuts(controller: Any) -> None:
    self = controller
    from qtpy import QtGui, QtWidgets

    def _bind(seq: str, callback: Any) -> None:
        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(seq), self._root)
        shortcut.activated.connect(callback)

    _bind("Space", self._on_run_toggle)
    _bind("N", self._on_step)
    _bind("R", self._on_reset)


__all__ = ["build_buttons", "install_shortcuts"]
