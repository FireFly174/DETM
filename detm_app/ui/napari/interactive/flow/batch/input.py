#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Batch UI input models for napari interactive controller."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BatchUiInput:
    batch_n: str
    batch_seed0: str
    batch_steps: str
    batch_symbols_csv: str
    batch_out_dir: str
    batch_fields_every: str
    batch_record_fields_npz: bool
    invariant_streams: str


__all__ = ["BatchUiInput"]
