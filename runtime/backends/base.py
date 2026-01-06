"""Backend protocol for DETM numerical implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.entropy import DynamicsParameters
from core.fields import Lattice
from runtime.state import DETMFieldState


@dataclass(frozen=True)
class BackendConfig:
    name: str
    device: str = "cpu"


class Backend(Protocol):
    config: BackendConfig

    def step(self, state: DETMFieldState, params: DynamicsParameters, n_ticks: int) -> DETMFieldState: ...

    def supports(self, lattice: Lattice) -> bool: ...
