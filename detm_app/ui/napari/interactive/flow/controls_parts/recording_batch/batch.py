#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Batch page builder for napari interactive controls."""

from __future__ import annotations

from typing import Any


def add_batch_page(controller: Any, *, QtWidgets: Any) -> None:
    self = controller
    page_batch = QtWidgets.QWidget()
    self._batch_layout = QtWidgets.QVBoxLayout(page_batch)
    self._batch_layout.setContentsMargins(6, 6, 6, 6)

    def _batch_line(label: str, value: str) -> Any:
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        lbl = QtWidgets.QLabel(str(label))
        edit = QtWidgets.QLineEdit(str(value))
        row.addWidget(lbl)
        row.addWidget(edit)
        self._batch_layout.addLayout(row)
        return edit

    self._batch_n = _batch_line("batch_n", "10")
    self._batch_seed0 = _batch_line("batch_seed0", "0")
    self._batch_steps = _batch_line("batch_steps", "4")
    self._batch_symbols = _batch_line("batch_symbols_csv", "")
    self._batch_out = _batch_line("batch_out_dir", "runs/out/batch_ui")
    self._batch_fields_every = _batch_line("batch_fields_every", "1")
    self._batch_record_fields = QtWidgets.QCheckBox("batch_record_fields_npz")
    self._batch_record_fields.setChecked(False)
    self._batch_layout.addWidget(self._batch_record_fields)
    self._batch_log = QtWidgets.QTextEdit()
    self._batch_log.setReadOnly(True)
    self._batch_log.setMinimumHeight(140)
    self._batch_layout.addWidget(self._batch_log)
    self._batch_layout.addStretch(1)
    self._batch_page_index = self._toolbox.addItem(page_batch, "Batch")


__all__ = ["add_batch_page"]
