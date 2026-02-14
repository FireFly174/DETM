"""Array conversion and field-state writeback helpers for refinement runtime."""

from __future__ import annotations

from typing import Any

import numpy as np

from detm.runtime.state import DETMFieldState


def to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def is_torch_tensor(array: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(array, torch.Tensor)


def apply_field_state(
    field_state: DETMFieldState,
    *,
    energy_np: np.ndarray,
    entropy_np: np.ndarray,
    internal_time_np: np.ndarray | None = None,
) -> None:
    if is_torch_tensor(field_state.energy):
        import torch  # type: ignore

        energy_t = field_state.energy
        entropy_t = field_state.entropy
        tau_t = field_state.internal_time
        field_state.energy = torch.tensor(energy_np, device=energy_t.device, dtype=energy_t.dtype)
        field_state.entropy = torch.tensor(entropy_np, device=entropy_t.device, dtype=entropy_t.dtype)
        if internal_time_np is not None:
            field_state.internal_time = torch.tensor(internal_time_np, device=tau_t.device, dtype=tau_t.dtype)
        return
    field_state.energy = np.asarray(energy_np, dtype=float)
    field_state.entropy = np.asarray(entropy_np, dtype=float)
    if internal_time_np is not None:
        field_state.internal_time = np.asarray(internal_time_np, dtype=float)


__all__ = ["apply_field_state", "is_torch_tensor", "to_numpy"]
