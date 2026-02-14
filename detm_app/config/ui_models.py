"""UI settings models shared across app-layer frontends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from detm.runtime.config import DETMConfig


@dataclass
class UiRunSettings:
    config: DETMConfig
    seed: int = 1
    ticks_per_step: int = 4
    tick_interval_ms: int = 60
    influence_mode: str = "none"
    symbol_id: str = "none"
    amplitude: float = 0.005
    influence_duration_steps: int = 0
    joy_dx: float = 0.0
    joy_dy: float = 0.0
    patch_cx: int = 12
    patch_cy: int = 12
    patch_radius: int = 6
    source_x: int = 6
    source_y: int = 12
    sink_x: int = 18
    sink_y: int = 12
    source_value: float = 1.0
    sink_value: float = 0.0
    record_dir: Path | None = None
    record_fields: bool = False
    invariant_streams: str = ""
    viz_enabled: bool = True
    viz_transport: str = "embedded"
    viz_host: str = "127.0.0.1"
    viz_port: int = 0
    viz_connect: bool = False
    viz_keep_open: bool = False
    viz_every_steps: int = 1


__all__ = ["UiRunSettings"]
