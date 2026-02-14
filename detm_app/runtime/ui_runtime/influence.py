"""Influence construction for UI runtime step orchestration."""

from __future__ import annotations

from typing import Any

from detm.runtime.influence import DETMInfluence
from detm.runtime.symbols import make_symbol


def resolve_influence_for_settings(
    settings: Any,
    *,
    last_key: tuple | None,
    remaining_steps: int,
) -> tuple[DETMInfluence | None, tuple | None, int]:
    mode = str(getattr(settings, "influence_mode", "symbol") or "symbol").strip().lower()
    duration_steps = int(getattr(settings, "influence_duration_steps", 0) or 0)
    amplitude = float(getattr(settings, "amplitude", 0.0))

    if mode in {"none", "(none)", ""}:
        return None, last_key, int(remaining_steps)

    influence: DETMInfluence
    key: tuple
    if mode == "symbol":
        symbol_id = (getattr(settings, "symbol_id", "") or "").strip()
        if not symbol_id or symbol_id == "(none)":
            return None, last_key, int(remaining_steps)
        key = ("symbol", symbol_id, amplitude)
        influence = make_symbol(symbol_id, amplitude=amplitude)
    elif mode == "joystick_field":
        dx = float(getattr(settings, "joy_dx", 0.0))
        dy = float(getattr(settings, "joy_dy", 0.0))
        key = ("joystick_field", amplitude, dx, dy)
        influence = DETMInfluence(
            symbol_id="joystick_field",
            amplitude=amplitude,
            external_features={"dx": dx, "dy": dy},
        )
    elif mode == "joystick_patch":
        w, h = int(settings.config.width), int(settings.config.height)
        cx = int(getattr(settings, "patch_cx", w // 2)) % max(1, w)
        cy = int(getattr(settings, "patch_cy", h // 2)) % max(1, h)
        radius = int(
            getattr(
                settings,
                "patch_radius",
                max(1, max(settings.config.width, settings.config.height) // 8),
            )
        )
        key = ("joystick_patch", amplitude, cx, cy, radius)
        influence = DETMInfluence(symbol_id="joystick_patch", amplitude=amplitude, region=(cx, cy, radius))
    elif mode == "source_sink":
        sx = int(getattr(settings, "source_x", 0))
        sy = int(getattr(settings, "source_y", 0))
        tx = int(getattr(settings, "sink_x", 0))
        ty = int(getattr(settings, "sink_y", 0))
        sv = float(getattr(settings, "source_value", 1.0))
        tv = float(getattr(settings, "sink_value", 0.0))
        key = ("source_sink", amplitude, sx, sy, tx, ty, sv, tv)
        influence = DETMInfluence(
            symbol_id="source_sink",
            amplitude=amplitude,
            external_features={
                "src_x": float(sx),
                "src_y": float(sy),
                "dst_x": float(tx),
                "dst_y": float(ty),
                "src_value": float(sv),
                "dst_value": float(tv),
            },
        )
    else:
        return None, last_key, int(remaining_steps)

    if duration_steps > 0:
        next_remaining = int(remaining_steps)
        next_key = last_key
        if last_key != key:
            next_key = key
            next_remaining = int(duration_steps)
        if int(next_remaining) <= 0:
            return None, next_key, int(next_remaining)
        return influence, next_key, int(next_remaining) - 1

    return influence, key, 0


__all__ = ["resolve_influence_for_settings"]
