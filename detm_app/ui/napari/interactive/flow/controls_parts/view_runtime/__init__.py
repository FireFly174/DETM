#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""View/runtime controls package for napari interactive flow."""

from detm_app.ui.napari.interactive.flow.controls_parts.view_runtime.runtime import add_runtime_page
from detm_app.ui.napari.interactive.flow.controls_parts.view_runtime.view import add_view_page

__all__ = ["add_view_page", "add_runtime_page"]
