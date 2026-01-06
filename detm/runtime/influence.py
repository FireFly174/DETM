"""Influence structures and helpers for DETM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

from detm.core.fields import Lattice
from detm.runtime.state import DETMFieldState


@dataclass(frozen=True)
class DETMInfluence:
    """External influence applied during a step."""

    symbol_id: str
    amplitude: float = 1.0
    phase: float | None = None
    seed: int | None = None
    region: tuple[int, int, int] | None = None  # (cx, cy, radius)
    mask: np.ndarray | None = None
    duration: int | None = None
    external_features: np.ndarray | Dict[str, float] | None = None
    dynamics_overrides: Dict[str, float] | None = None


@dataclass(frozen=True)
class InfluenceApplication:
    """Description of how an influence was applied."""

    symbol_id: str
    affected_fraction: float
    amplitude: float
    region: tuple[int, int, int] | None = None
    external_features: Dict[str, float] | None = None


def _resolve_mask(lattice: Lattice, influence: DETMInfluence) -> np.ndarray:
    if influence.mask is not None:
        mask = np.asarray(influence.mask, dtype=bool)
        if mask.shape != (lattice.height, lattice.width):
            raise ValueError("Influence mask shape does not match lattice")
        return mask

    sid = str(influence.symbol_id or "")
    h, w = lattice.height, lattice.width
    y, x = np.ogrid[:h, :w]

    if sid == "noise_burst" and influence.region is None:
        return np.ones((h, w), dtype=bool)

    cx, cy, radius = influence.region if influence.region is not None else (w // 2, h // 2, max(w, h) // 4)
    cx = int(cx)
    cy = int(cy)
    radius = max(0, int(radius))
    dist2 = (x - cx) ** 2 + (y - cy) ** 2

    if sid == "ring":
        r_out = max(1, radius)
        r_in = max(0, int(round(r_out * 0.6)))
        return (dist2 <= r_out**2) & (dist2 >= r_in**2)

    if sid == "stripe":
        # A deterministic stripe mask. `phase` selects orientation when provided:
        # phase < 0.5 => vertical, else horizontal.
        orientation = "vertical"
        if influence.phase is not None:
            try:
                orientation = "vertical" if float(influence.phase) < 0.5 else "horizontal"
            except Exception:
                orientation = "vertical"
        stripe_half = max(1, int(round(radius if influence.region is not None else max(1, w // 10))))
        if orientation == "horizontal":
            mask = np.abs(y - cy) <= stripe_half
            return np.broadcast_to(mask, (h, w))
        mask = np.abs(x - cx) <= stripe_half
        return np.broadcast_to(mask, (h, w))

    if sid == "focus":
        # Smaller, tighter spot than a default pulse.
        r = max(1, int(round(radius * 0.5))) if influence.region is not None else max(1, max(w, h) // 8)
        return dist2 <= r**2

    if sid == "disturb":
        # Checker-like pattern to differ visually from `pulse`.
        base = dist2 <= max(1, radius) ** 2
        return base & (((x + y) % 2) == 0)

    return dist2 <= max(1, radius) ** 2


def _is_torch_tensor(value: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(value, torch.Tensor)


def apply_influence(state: DETMFieldState, influence: DETMInfluence, rng: np.random.Generator) -> InfluenceApplication:
    """Apply influence to energy field in-place.

    The implementation is intentionally simple: it perturbs energy in a masked
    region. More sophisticated behaviour can be added without changing the
    public signature.
    """

    lattice = state.lattice
    amplitude = float(influence.amplitude)

    # Symbol-specific variants that don't use a boolean mask.
    sid = str(influence.symbol_id or "")

    influence_rng = rng
    if influence.seed is not None:
        influence_rng = np.random.Generator(np.random.PCG64(int(influence.seed)))

    external_features = None
    if isinstance(influence.external_features, dict):
        external_features = {str(k): float(v) for k, v in influence.external_features.items()}

    if _is_torch_tensor(state.energy):
        import torch  # type: ignore

        energy_t = state.energy
        device = energy_t.device
        dtype = energy_t.dtype

        if sid == "joystick_field":
            dx = float(external_features.get("dx", 0.0)) if external_features else 0.0
            dy = float(external_features.get("dy", 0.0)) if external_features else 0.0
            h, w = lattice.height, lattice.width
            xs = torch.linspace(-1.0, 1.0, steps=w, device=device, dtype=dtype).reshape(1, w).expand(h, w)
            ys = torch.linspace(-1.0, 1.0, steps=h, device=device, dtype=dtype).reshape(h, 1).expand(h, w)
            plane = dx * xs + dy * ys
            updated = torch.clamp(energy_t + amplitude * plane, min=0.0, max=1.0)
            state.energy = updated
            affected_fraction = 1.0
            return InfluenceApplication(
                symbol_id=influence.symbol_id,
                affected_fraction=float(affected_fraction),
                amplitude=float(amplitude),
                region=influence.region,
                external_features=external_features,
            )

        if sid == "source_sink":
            h, w = lattice.height, lattice.width
            src_x = int(external_features.get("src_x", w // 4)) if external_features else w // 4
            src_y = int(external_features.get("src_y", h // 2)) if external_features else h // 2
            dst_x = int(external_features.get("dst_x", (3 * w) // 4)) if external_features else (3 * w) // 4
            dst_y = int(external_features.get("dst_y", h // 2)) if external_features else h // 2
            src_value = float(external_features.get("src_value", 1.0)) if external_features else 1.0
            dst_value = float(external_features.get("dst_value", 0.0)) if external_features else 0.0
            strength = float(min(1.0, max(0.0, abs(amplitude))))

            energy = energy_t.reshape(h, w)
            energy[src_y % h, src_x % w] = (1.0 - strength) * energy[src_y % h, src_x % w] + strength * src_value
            energy[dst_y % h, dst_x % w] = (1.0 - strength) * energy[dst_y % h, dst_x % w] + strength * dst_value
            state.energy = torch.clamp(energy, min=0.0, max=1.0)
            affected_fraction = float(2.0 / float(max(1, h * w)))
            return InfluenceApplication(
                symbol_id=influence.symbol_id,
                affected_fraction=float(affected_fraction),
                amplitude=float(amplitude),
                region=influence.region,
                external_features=external_features,
            )

        mask = _resolve_mask(lattice, influence)
        mask_t = torch.from_numpy(mask).to(device=device)
        noise_np = influence_rng.normal(loc=0.0, scale=0.05, size=mask.shape).astype(np.float64)
        noise_t = torch.from_numpy(noise_np).to(device=device, dtype=dtype)

        updated = energy_t + amplitude * (1.0 + noise_t)
        updated = torch.clamp(updated, min=0.0, max=1.0)
        state.energy = torch.where(mask_t, updated, energy_t)
    else:
        energy = np.asarray(state.energy, dtype=float)

        if sid == "joystick_field":
            dx = float(external_features.get("dx", 0.0)) if external_features else 0.0
            dy = float(external_features.get("dy", 0.0)) if external_features else 0.0
            h, w = lattice.height, lattice.width
            xs = np.linspace(-1.0, 1.0, num=w, dtype=float).reshape(1, w).repeat(h, axis=0)
            ys = np.linspace(-1.0, 1.0, num=h, dtype=float).reshape(h, 1).repeat(w, axis=1)
            plane = dx * xs + dy * ys
            state.energy = np.clip(energy + amplitude * plane, 0.0, 1.0)
            affected_fraction = 1.0
            return InfluenceApplication(
                symbol_id=influence.symbol_id,
                affected_fraction=float(affected_fraction),
                amplitude=float(amplitude),
                region=influence.region,
                external_features=external_features,
            )

        if sid == "source_sink":
            h, w = lattice.height, lattice.width
            src_x = int(external_features.get("src_x", w // 4)) if external_features else w // 4
            src_y = int(external_features.get("src_y", h // 2)) if external_features else h // 2
            dst_x = int(external_features.get("dst_x", (3 * w) // 4)) if external_features else (3 * w) // 4
            dst_y = int(external_features.get("dst_y", h // 2)) if external_features else h // 2
            src_value = float(external_features.get("src_value", 1.0)) if external_features else 1.0
            dst_value = float(external_features.get("dst_value", 0.0)) if external_features else 0.0
            strength = float(min(1.0, max(0.0, abs(amplitude))))

            src_x %= w
            src_y %= h
            dst_x %= w
            dst_y %= h
            energy[src_y, src_x] = (1.0 - strength) * energy[src_y, src_x] + strength * src_value
            energy[dst_y, dst_x] = (1.0 - strength) * energy[dst_y, dst_x] + strength * dst_value
            state.energy = np.clip(energy, 0.0, 1.0)
            affected_fraction = float(2.0 / float(max(1, h * w)))
            return InfluenceApplication(
                symbol_id=influence.symbol_id,
                affected_fraction=float(affected_fraction),
                amplitude=float(amplitude),
                region=influence.region,
                external_features=external_features,
            )

        mask = _resolve_mask(lattice, influence)
        noise = influence_rng.normal(loc=0.0, scale=0.05, size=energy.shape)
        energy[mask] = np.clip(energy[mask] + amplitude * (1.0 + noise[mask]), 0.0, 1.0)
        state.energy = energy

    affected_fraction = float(mask.mean()) if mask.size else 0.0

    return InfluenceApplication(
        symbol_id=influence.symbol_id,
        affected_fraction=affected_fraction,
        amplitude=float(amplitude),
        region=influence.region,
        external_features=external_features,
    )


__all__ = ["DETMInfluence", "InfluenceApplication", "apply_influence"]
