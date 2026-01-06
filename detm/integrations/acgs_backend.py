"""Adapter for running DETM behind the ACGS `DETMBackend` protocol.

ACGS defines its own lightweight protocol and influence/observables types
(`symbols: list[int]` and a small 5-float signature). In a shared environment
(e.g. ComfyUI) we want DETM to be usable without importing ACGS internals, so
this adapter:

- Accepts an ACGS-like influence object (must have `.symbols: list[int]`).
- Executes DETM L0 dynamics via `detm.runtime.api`.
- Returns an ACGS-like observables object (`signature`, `cost_proxy`).

The returned signature keeps the current ACGS expectation:
`[sin, cos, target_x, target_y, confidence]`.
"""

from __future__ import annotations

import base64
import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, Protocol

import numpy as np

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.serialization import serialize_state
from detm.runtime.state import DETMState
from detm.runtime.symbols import list_symbols, make_symbol


JSONValue = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


class ACGSInfluenceLike(Protocol):
    symbols: list[int]


@dataclass(frozen=True, slots=True)
class ACGSObservablesLike:
    signature: list[float]
    cost_proxy: float

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "signature": [float(v) for v in self.signature],
            "cost_proxy": float(self.cost_proxy),
        }


def _to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None

    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def _hash_state(state: DETMState) -> str:
    """Deterministic digest that does not depend on zip timestamps in serialization."""

    lattice = state.lattice
    energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width).astype(np.float64, copy=False)
    entropy = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width).astype(np.float64, copy=False)
    internal_time = (
        _to_numpy(state.field_state.internal_time)
        .reshape(lattice.height, lattice.width)
        .astype(np.float64, copy=False)
    )

    hasher = hashlib.sha256()
    hasher.update(state.state_version.encode("utf-8"))
    hasher.update(str(state.step_count).encode("utf-8"))
    hasher.update(str(lattice.width).encode("utf-8"))
    hasher.update(str(lattice.height).encode("utf-8"))
    hasher.update(str(lattice.boundary).encode("utf-8"))
    hasher.update(energy.tobytes(order="C"))
    hasher.update(entropy.tobytes(order="C"))
    hasher.update(internal_time.tobytes(order="C"))
    return hasher.hexdigest()


class ACGSDetmBackend:
    """Stateful DETM backend compatible with the current ACGS scheduler stub."""

    def __init__(
        self,
        *,
        config: DETMConfig | None = None,
        n_ticks_per_step: int = 1,
        symbol_alphabet: list[str] | None = None,
    ) -> None:
        self.config = config or DETMConfig()
        self.n_ticks_per_step = int(n_ticks_per_step)
        if self.n_ticks_per_step <= 0:
            raise ValueError("n_ticks_per_step must be > 0")

        self.symbol_alphabet = list(symbol_alphabet) if symbol_alphabet is not None else list_symbols()
        if not self.symbol_alphabet:
            raise ValueError("symbol_alphabet must not be empty")

        self._seed = 0
        self._tick = 0
        self._state: DETMState | None = None

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = int(seed)
        self._tick = 0
        self._state = api.reset(self.config, seed=self._seed)

    def _region_for_symbol(self, symbol: int) -> tuple[int, int, int]:
        if self._state is None:
            raise RuntimeError("Backend not initialised; call reset() first")

        lattice = self._state.lattice
        w, h = lattice.width, lattice.height
        n = max(1, len(self.symbol_alphabet))
        angle = 2.0 * math.pi * (int(symbol) % n) / float(n)

        cx0 = (w - 1) / 2.0
        cy0 = (h - 1) / 2.0
        orbit = max(0.0, min(w, h) * 0.35)

        cx = int(round(cx0 + orbit * math.cos(angle)))
        cy = int(round(cy0 + orbit * math.sin(angle)))
        cx = max(0, min(w - 1, cx))
        cy = max(0, min(h - 1, cy))

        radius = max(1, int(round(min(w, h) * 0.18)))
        return (cx, cy, radius)

    def _symbol_to_influence(self, symbol: int):
        symbol_id = self.symbol_alphabet[int(symbol) % len(self.symbol_alphabet)]
        region = self._region_for_symbol(symbol)
        influence_seed = self._seed + int(symbol) + self._tick * 1009
        return make_symbol(symbol_id, region=region, seed=influence_seed)

    def step(self, influence: ACGSInfluenceLike) -> ACGSObservablesLike:
        if self._state is None:
            self.reset(seed=self._seed)

        self._tick += 1
        symbols = list(getattr(influence, "symbols", []))
        symbol = symbols[-1] if symbols else None

        if symbol is None or int(symbol) < 0:
            self._state, obs = api.step(self._state, None, n_ticks=self.n_ticks_per_step, rng=None)
            return ACGSObservablesLike(signature=[0.0, 0.0, 0.0, 0.0, 0.0], cost_proxy=float(obs.cost["cpu_time_ms"]))

        detm_influence = self._symbol_to_influence(int(symbol))
        self._state, obs = api.step(self._state, detm_influence, n_ticks=self.n_ticks_per_step, rng=None)

        detm_sig = obs.signature.vector
        n = float(len(self.symbol_alphabet))
        angle = 2.0 * math.pi * (int(symbol) % int(n)) / n
        sin_v = math.sin(angle)
        cos_v = math.cos(angle)

        w = float(self._state.lattice.width - 1) if self._state.lattice.width > 1 else 1.0
        h = float(self._state.lattice.height - 1) if self._state.lattice.height > 1 else 1.0
        center_x = float(detm_sig[7])
        center_y = float(detm_sig[8])
        tx = (center_x / w) * 2.0 - 1.0
        ty = (center_y / h) * 2.0 - 1.0
        confidence = 1.0

        signature = [float(sin_v), float(cos_v), float(tx), float(ty), float(confidence)]
        return ACGSObservablesLike(signature=signature, cost_proxy=float(obs.cost["cpu_time_ms"]))

    def digest(self) -> str:
        if self._state is None:
            self.reset(seed=self._seed)
        return _hash_state(self._state)

    def serialize(self) -> dict[str, JSONValue]:
        if self._state is None:
            self.reset(seed=self._seed)

        blob = serialize_state(self._state)
        return {
            "backend": "ACGSDetmBackend",
            "tick": int(self._tick),
            "seed": int(self._seed),
            "config": self.config.to_dict(),
            "state_b64": base64.b64encode(blob).decode("ascii"),
        }


__all__ = ["ACGSDetmBackend", "ACGSInfluenceLike", "ACGSObservablesLike", "JSONValue"]

