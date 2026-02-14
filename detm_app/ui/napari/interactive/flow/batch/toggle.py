#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Batch toggle action for napari interactive controller."""

from __future__ import annotations

from typing import Any

from detm_app.ui.napari.interactive.flow.batch.input import BatchUiInput
from detm_app.ui.napari.interactive.flow.batch.request import build_batch_request


def on_batch_toggle(controller: Any) -> None:
    self = controller
    if self._closing:
        return
    if not self._mode_is_batch():
        return
    if self._batch_state.is_running():
        self._batch_state.cancel()
        return

    try:
        request = build_batch_request(
            config=self._build_config_from_controls(),
            parse_symbol_csv=self._parse_symbol_csv,
            ui=BatchUiInput(
                batch_n=str(self._batch_n.text()),
                batch_seed0=str(self._batch_seed0.text()),
                batch_steps=str(self._batch_steps.text()),
                batch_symbols_csv=str(self._batch_symbols.text()),
                batch_out_dir=str(self._batch_out.text()),
                batch_fields_every=str(self._batch_fields_every.text()),
                batch_record_fields_npz=bool(self._batch_record_fields.isChecked()),
                invariant_streams=str(self._invariant_streams.text() or ""),
            ),
        )
    except Exception as exc:
        self._log_batch(f"[error] {exc}")
        return

    self._batch_state.start(request)


__all__ = ["on_batch_toggle"]
