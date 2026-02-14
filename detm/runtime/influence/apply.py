"""Influence structures and helpers for DETM."""

from __future__ import annotations

from typing import Dict

import numpy as np

from detm.runtime.influence.contracts import DETMInfluence, InfluenceApplication
from detm.runtime.influence.mask import is_torch_tensor as _is_torch_tensor
from detm.runtime.influence.mask import resolve_mask as _resolve_mask
from detm.runtime.state import DETMFieldState


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
