#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Batch request builders for napari interactive controller."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from detm.runtime.config import DETMConfig
from detm_app.runner.batch_service import BatchRunRequest
from detm_app.ui.napari.interactive.flow.batch.input import BatchUiInput
from detm_app.ui.napari.interactive.helpers import to_int as _to_int


def build_batch_request(
    *,
    config: DETMConfig,
    parse_symbol_csv: Callable[[str], list[str]],
    ui: BatchUiInput,
) -> BatchRunRequest:
    symbol_ids = parse_symbol_csv(str(ui.batch_symbols_csv))
    n = max(1, _to_int(str(ui.batch_n), 10))
    seed0 = _to_int(str(ui.batch_seed0), 0)
    steps = max(1, _to_int(str(ui.batch_steps), 4))
    out_root = Path(str(ui.batch_out_dir).strip() or "runs/out/batch_ui")
    fields_npz = bool(ui.batch_record_fields_npz)
    fields_every = max(1, _to_int(str(ui.batch_fields_every), 1))
    invariant_streams = [
        chunk.strip() for chunk in str(ui.invariant_streams or "").split(",") if chunk.strip()
    ] or None
    return BatchRunRequest(
        config=config,
        symbol_ids=symbol_ids,
        batch_n=int(n),
        seed0=int(seed0),
        tick_budget=int(steps),
        out_root=Path(out_root),
        fields_npz=bool(fields_npz),
        fields_every_steps=int(fields_every),
        invariant_streams=invariant_streams,
    )


__all__ = ["build_batch_request"]
