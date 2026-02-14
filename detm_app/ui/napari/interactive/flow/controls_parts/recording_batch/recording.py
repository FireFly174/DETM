#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Recording page builder for napari interactive controls."""

from __future__ import annotations

from typing import Any


def add_recording_page(controller: Any, *, QtWidgets: Any, settings: Any, tips: dict[str, str]) -> None:
    self = controller
    page_recording = QtWidgets.QWidget()
    lay_recording = QtWidgets.QVBoxLayout(page_recording)
    lay_recording.setContentsMargins(6, 6, 6, 6)
    self._record_enabled = QtWidgets.QCheckBox("record_trace")
    self._record_enabled.setChecked(bool(settings.record_dir is not None))
    lay_recording.addWidget(self._record_enabled)
    _, self._record_dir = self._line(
        label="record_dir",
        value=str(settings.record_dir) if settings.record_dir is not None else "runs/out/ui_run",
        parent_layout=lay_recording,
        tooltip=tips.get("ui.record_dir", ""),
    )
    self._record_fields = QtWidgets.QCheckBox("record_fields_hist_npz")
    self._record_fields.setChecked(bool(settings.record_fields))
    lay_recording.addWidget(self._record_fields)
    _, self._invariant_streams = self._line(
        label="invariant_streams",
        value=str(settings.invariant_streams or ""),
        parent_layout=lay_recording,
        tooltip=tips.get("ui.invariant_streams", ""),
    )
    lay_recording.addStretch(1)
    self._toolbox.addItem(page_recording, "Recording")


__all__ = ["add_recording_page"]
