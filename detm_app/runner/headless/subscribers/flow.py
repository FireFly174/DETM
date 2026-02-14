"""Headless subscriber wiring orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from detm.runtime.config import DETMConfig
from detm_app.runner.headless.subscribers.core import attach_core_subscribers
from detm_app.runner.headless.subscribers.fabric import attach_fabric_handshake_subscriber
from detm_app.runner.headless.subscribers.streaming import attach_streaming_subscribers
from detm_app.runtime.session import DetmSession


def attach_headless_subscribers(
    *,
    session: DetmSession,
    config: DETMConfig,
    seed: int,
    out_dir: Path,
    level_name: str,
    invariant_streams: list[str] | None,
    viz_transport: Any,
    viz_every_steps: int,
    fields_npz: bool,
    fields_every_steps: int,
    fabric_kwargs: Mapping[str, Any],
) -> None:
    attach_core_subscribers(
        session=session,
        config=config,
        seed=seed,
        out_dir=out_dir,
        level_name=level_name,
        invariant_streams=invariant_streams,
    )
    attach_fabric_handshake_subscriber(
        session=session,
        config=config,
        seed=seed,
        out_dir=out_dir,
        level_name=level_name,
        fabric_kwargs=fabric_kwargs,
    )
    attach_streaming_subscribers(
        session=session,
        out_dir=out_dir,
        viz_transport=viz_transport,
        viz_every_steps=viz_every_steps,
        fields_npz=fields_npz,
        fields_every_steps=fields_every_steps,
    )


__all__ = ["attach_headless_subscribers"]
