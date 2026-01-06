"""State container for DETM L0 dynamics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np

from core.entropy import DynamicsParameters
from core.fields import FieldState, Lattice, ScalarField
from runtime.schemas import DETM_STATE_V1


@dataclass
class DETMState:
    """Complete runtime state for DETM.

    All mutable data required for evolution is stored here to avoid hidden
    globals and to make serialization straightforward.
    """

    state_version: str = DETM_STATE_V1
    field_state: FieldState = field(default_factory=lambda: FieldState(ScalarField(Lattice(1, 1), [0.0]), ScalarField(Lattice(1, 1), [0.0]), ScalarField(Lattice(1, 1), [0.0])))
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
        rng = np.random.default_rng()
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


__all__ = ["DETMState"]
