"""Attach orchestration for FabricHandshakeRecorder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detm.runtime.fabric import compose_fabric_handshake_runtime

from detm_app.runtime.subscribers.fabric.attach import build_attach_kwargs
from detm_app.runtime.subscribers.fabric.lifecycle import (
    bind_runtime_composition,
    initialize_recorder_runtime_state,
)


def attach_recorder(
    *,
    cls: Any,
    bus: Any,
    out_dir: Path,
    **kwargs: Any,
):
    rec = cls(
        out_dir=out_dir,
        **build_attach_kwargs(**kwargs),
    )
    initialize_recorder_runtime_state(rec, bus=bus)
    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=rec._mode_channels,
    )
    bind_runtime_composition(rec, composition)
    rec._unsub_commit = bus.add_event_listener_unsub("commit_packet", rec.on_commit_packet)
    rec._unsub_close = bus.add_event_listener_unsub("close", rec.on_close)
    return rec


__all__ = ["attach_recorder"]
