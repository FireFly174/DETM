"""State container for DETM L0 dynamics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np

from core.entropy import DynamicsParameters
from core.fields import Lattice
from runtime.schemas import DETM_STATE_V1

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


@dataclass
class DETMFieldState:
    """Backend-owned numeric state for a single DETM tick."""

    lattice: Lattice
    energy: ArrayLike  # shape (H, W)
    entropy: ArrayLike  # shape (H, W)
    internal_time: ArrayLike  # shape (H, W)

    def ensure_alignment(self) -> None:
        h, w = self.lattice.height, self.lattice.width
        expected = (h, w)
        for name, array in [
            ("energy", self.energy),
            ("entropy", self.entropy),
            ("internal_time", self.internal_time),
        ]:
            shape = tuple(array.shape) if _is_torch_tensor(array) else tuple(np.asarray(array).shape)
            if shape != expected:
                raise ValueError(f"{name} shape {shape} does not match lattice {expected}")

    def copy(self) -> "DETMFieldState":
        return DETMFieldState(
            lattice=self.lattice,
            energy=_copy_array(self.energy),
            entropy=_copy_array(self.entropy),
            internal_time=_copy_array(self.internal_time),
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
