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


def apply_field_plane_state(
    field_state: DETMFieldState,
    *,
    plane_index: tuple[int, ...],
    energy_np: np.ndarray,
    entropy_np: np.ndarray,
    internal_time_np: np.ndarray | None = None,
) -> None:
    shape = tuple(int(dim) for dim in field_state.shape)
    expected_plane_index_len = max(0, len(shape) - 2)
    if len(tuple(plane_index)) != expected_plane_index_len:
        raise ValueError(
            f"plane index length {len(tuple(plane_index))} does not match field leading rank {expected_plane_index_len}"
        )
    plane_shape = tuple(int(dim) for dim in shape[-2:])
    if tuple(np.asarray(energy_np).shape) != plane_shape:
        raise ValueError(f"energy plane shape {tuple(np.asarray(energy_np).shape)} does not match {plane_shape}")
    if tuple(np.asarray(entropy_np).shape) != plane_shape:
        raise ValueError(f"entropy plane shape {tuple(np.asarray(entropy_np).shape)} does not match {plane_shape}")
    if internal_time_np is not None and tuple(np.asarray(internal_time_np).shape) != plane_shape:
        raise ValueError(
            f"internal_time plane shape {tuple(np.asarray(internal_time_np).shape)} does not match {plane_shape}"
        )

    if expected_plane_index_len == 0:
        apply_field_state(
            field_state,
            energy_np=np.asarray(energy_np, dtype=float),
            entropy_np=np.asarray(entropy_np, dtype=float),
            internal_time_np=None if internal_time_np is None else np.asarray(internal_time_np, dtype=float),
        )
        return

    if is_torch_tensor(field_state.energy):
        import torch  # type: ignore

        energy_t = field_state.energy
        entropy_t = field_state.entropy
        tau_t = field_state.internal_time
        plane_key = tuple(int(v) for v in plane_index)
        energy_t[plane_key] = torch.tensor(energy_np, device=energy_t.device, dtype=energy_t.dtype)
        entropy_t[plane_key] = torch.tensor(entropy_np, device=entropy_t.device, dtype=entropy_t.dtype)
        if internal_time_np is not None:
            tau_t[plane_key] = torch.tensor(internal_time_np, device=tau_t.device, dtype=tau_t.dtype)
        return

    plane_key = tuple(int(v) for v in plane_index)
    energy = np.asarray(field_state.energy, dtype=float)
    entropy = np.asarray(field_state.entropy, dtype=float)
    energy[plane_key] = np.asarray(energy_np, dtype=float)
    entropy[plane_key] = np.asarray(entropy_np, dtype=float)
    if internal_time_np is not None:
        internal_time = np.asarray(field_state.internal_time, dtype=float)
        internal_time[plane_key] = np.asarray(internal_time_np, dtype=float)


__all__ = ["apply_field_plane_state", "apply_field_state", "is_torch_tensor", "to_numpy"]
