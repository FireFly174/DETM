"""Helper functions for fabric runtime mode-channel mapping and bundle startup."""

from __future__ import annotations

from detm.runtime.fabric_runtime_bundle import FabricHandshakeRuntimeBundle

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (small runtime helper functions extracted from subscriber)
# - OOP_TECH_DEBT: richer channel policy registry and runtime lifecycle diagnostics


def mode_channels(split_mode_channels: bool, base_channel: str) -> dict[str, str] | None:
    """Build mode-split channel mapping for realtime/audit when enabled."""
    if not bool(split_mode_channels):
        return None
    base = str(base_channel).strip()
    if not base:
        return None
    return {
        "realtime": f"{base}.realtime",
        "audit": f"{base}.audit",
    }


def channel_for_mode(*, base_channel: str, mode: str, mapping: dict[str, str] | None) -> str:
    """Resolve effective channel for a mode with fallback to base channel."""
    if not mapping:
        return str(base_channel)
    norm_mode = str(mode).strip().lower()
    return str(mapping.get(norm_mode, str(base_channel)))


def start_runtime_bundle(
    bundle: FabricHandshakeRuntimeBundle | None,
) -> tuple[list[tuple[str, str | None]], list[tuple[str, str | None]]]:
    """Start runtime bundle and return ack/delivery subscriptions."""
    if bundle is None:
        return ([], [])
    bundle.start()
    return bundle.ack_subscriptions(), bundle.delivery_ack_subscriptions()


__all__ = ["mode_channels", "channel_for_mode", "start_runtime_bundle"]
