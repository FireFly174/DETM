#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Recording/batch controls package for napari interactive flow."""

from detm_app.ui.napari.interactive.flow.controls_parts.recording_batch.batch import add_batch_page
from detm_app.ui.napari.interactive.flow.controls_parts.recording_batch.recording import add_recording_page

__all__ = ["add_recording_page", "add_batch_page"]
