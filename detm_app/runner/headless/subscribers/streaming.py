"""Streaming/viz subscriber wiring for headless runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import FieldHistoryRecorder, VizStreamer


def attach_streaming_subscribers(
    *,
    session: DetmSession,
    out_dir: Path,
    viz_transport: Any,
    viz_every_steps: int,
    fields_npz: bool,
    fields_every_steps: int,
) -> None:
    if viz_transport is not None:
        VizStreamer.attach(session.bus, viz_transport, every_steps=viz_every_steps)
    if fields_npz:
        FieldHistoryRecorder.attach(
            session.bus,
            out_dir / "fields_hist.npz",
            every_steps=int(fields_every_steps),
            dtype="float32",
        )


__all__ = ["attach_streaming_subscribers"]
