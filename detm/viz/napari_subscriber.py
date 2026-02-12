"""Deprecated compatibility wrapper for napari read-only subscriber.

Canonical implementation lives in `detm_app.napari_subscriber`.
"""

from __future__ import annotations

import warnings

from detm_app.napari_subscriber import (
    NapariFrame,
    _LayerPresenter,
    packet_to_layer_frame,
    resolve_napari_endpoint,
    run_napari_subscriber,
    state_to_layers,
    wait_latest_packet,
)

_DEPRECATION_MESSAGE = (
    "`detm.viz.napari_subscriber` is deprecated; use `detm_app.napari_subscriber` instead. "
    "Compatibility wrapper will be removed in a future release."
)


def main(argv: list[str] | None = None) -> int:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    from detm_app.napari_subscriber import main as _app_main

    return int(_app_main(argv))


__all__ = [
    "NapariFrame",
    "_LayerPresenter",
    "packet_to_layer_frame",
    "resolve_napari_endpoint",
    "run_napari_subscriber",
    "state_to_layers",
    "wait_latest_packet",
    "main",
]
