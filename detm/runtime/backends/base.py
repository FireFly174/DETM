"""Backend protocol for DETM numerical implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.runtime.state import DETMFieldState


@dataclass(frozen=True)
class BackendConfig:
    name: str
    device: str = "cpu"


class Backend(Protocol):
    config: BackendConfig

    def step(self, state: DETMFieldState, params: DynamicsParameters, n_ticks: int) -> DETMFieldState: ...

    def supports(self, lattice: Lattice) -> bool: ...
