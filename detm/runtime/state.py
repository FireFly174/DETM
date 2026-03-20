"""State container for DETM L0 dynamics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.runtime.schemas import DETM_STATE_V1

if TYPE_CHECKING:  # pragma: no cover
    import torch

    ArrayLike = np.ndarray | torch.Tensor
else:  # pragma: no cover
    ArrayLike = Any


def _is_torch_tensor(value: Any) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(value, torch.Tensor)


def _copy_array(value: ArrayLike) -> ArrayLike:
    if _is_torch_tensor(value):
        return value.clone()
    return np.asarray(value, dtype=float).copy()


def _array_shape(value: ArrayLike) -> tuple[int, ...]:
    if _is_torch_tensor(value):
        return tuple(int(dim) for dim in value.shape)
    return tuple(int(dim) for dim in np.asarray(value).shape)


def _normalize_field_shape(raw_shape: Any, *, fallback: ArrayLike) -> tuple[int, ...]:
    if raw_shape in (None, "", (), []):
        shape = _array_shape(fallback)
    else:
        shape = tuple(int(dim) for dim in raw_shape)
    if len(shape) < 2:
        raise ValueError("field shape must contain at least two axes")
    if any(int(dim) <= 0 for dim in shape):
        raise ValueError("field shape axes must be positive")
    return tuple(int(dim) for dim in shape)


@dataclass
class DETMFieldState:
    """Backend-owned numeric state for a single DETM tick."""

    lattice: Lattice
    energy: ArrayLike  # shape (H, W)
    entropy: ArrayLike  # shape (H, W)
    internal_time: ArrayLike  # shape (H, W)
    shape: tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.shape = _normalize_field_shape(self.shape, fallback=self.energy)
        self.ensure_alignment()

    def ensure_alignment(self) -> None:
        h, w = self.lattice.height, self.lattice.width
        expected = self.shape
        if tuple(expected[-2:]) != (h, w):
            raise ValueError(f"field shape tail {tuple(expected[-2:])} does not match lattice {(h, w)}")
        for name, array in [
            ("energy", self.energy),
            ("entropy", self.entropy),
            ("internal_time", self.internal_time),
        ]:
            shape = _array_shape(array)
            if shape != expected:
                raise ValueError(f"{name} shape {shape} does not match field shape {expected}")

    def copy(self) -> "DETMFieldState":
        return DETMFieldState(
            lattice=self.lattice,
            energy=_copy_array(self.energy),
            entropy=_copy_array(self.entropy),
            internal_time=_copy_array(self.internal_time),
            shape=self.shape,
        )


def _default_field_state() -> DETMFieldState:
    lattice = Lattice(1, 1, boundary="periodic")
    zeros = np.zeros((1, 1), dtype=float)
    return DETMFieldState(lattice=lattice, energy=zeros.copy(), entropy=zeros.copy(), internal_time=zeros.copy())


@dataclass
class DETMState:
    """Complete runtime state for DETM.

    All mutable data required for evolution is stored here to avoid hidden
    globals and to make serialization straightforward.
    """

    state_version: str = DETM_STATE_V1
    field_state: DETMFieldState = field(default_factory=_default_field_state)
    step_count: int = 0
    rng_state: Dict[str, Any] = field(default_factory=dict)
    config: Optional[Dict[str, Any]] = None
    dynamics: DynamicsParameters = field(default_factory=DynamicsParameters)

    @property
    def lattice(self) -> Lattice:
        return self.field_state.lattice

    @property
    def shape(self) -> tuple[int, ...]:
        return self.field_state.shape

    def copy(self) -> "DETMState":
        return DETMState(
            state_version=self.state_version,
            field_state=self.field_state.copy(),
            step_count=self.step_count,
            rng_state=dict(self.rng_state),
            config=dict(self.config) if self.config is not None else None,
            dynamics=self.dynamics,
        )

    def restore_rng(self) -> np.random.Generator:
        rng = np.random.Generator(np.random.PCG64(0))
        if self.rng_state:
            rng.bit_generator.state = _from_serializable_rng_state(self.rng_state)
        return rng

    def store_rng(self, rng: np.random.Generator) -> None:
        self.rng_state = _to_serializable_rng_state(rng.bit_generator.state)


def _to_serializable_rng_state(state: Dict[str, Any]) -> Dict[str, Any]:
    def _convert(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: _convert(v) for k, v in value.items()}
        if isinstance(value, np.ndarray):
            return value.astype(int).tolist()
        if isinstance(value, (int, np.integer)):
            # PCG64 uses 128-bit state; store as decimal strings to avoid msgpack overflow
            return str(int(value))
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        return value

    return {key: _convert(val) for key, val in state.items()}


def _from_serializable_rng_state(state: Dict[str, Any]) -> Dict[str, Any]:
    def _restore(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: _restore(v) for k, v in value.items()}
        if isinstance(value, list):
            return np.asarray(value, dtype=np.uint64)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value

    return {key: _restore(val) for key, val in state.items()}


__all__ = ["DETMFieldState", "DETMState"]
