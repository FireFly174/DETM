"""Public runtime API for DETM integration."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Dict, List, Tuple

import numpy as np

from detm.core.fields import Lattice
from detm.core.entropy import DynamicsParameters
from detm.runtime.backends import Backend, NumpyBackend, TorchBackend
from detm.runtime.config import DETMConfig
from detm.runtime.diagnostics.attractors import detect_attractors
from detm.runtime.influence import DETMInfluence, apply_influence
from detm.runtime.serialization import deserialize_state, serialize_state
from detm.runtime.schemas import get_schema_versions
from detm.runtime.signature import DETMSignature, describe_field_from_array, digest_fields
from detm.runtime.state import DETMFieldState, DETMState


@dataclass(frozen=True)
class FieldSummaries:
    energy: Dict[str, float]
    entropy: Dict[str, float]
    internal_time: Dict[str, float]


@dataclass(frozen=True)
class Observables:
    signature: DETMSignature
    field_summaries: FieldSummaries
    events: List[Dict[str, object]]
    cost: Dict[str, float]
    quality: Dict[str, float]


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def _apply_dynamics_overrides(base: DynamicsParameters, overrides: Dict[str, float] | None) -> DynamicsParameters:
    if not overrides:
        return base
    allowed = {
        "equilibrium_energy",
        "beta",
        "gamma",
        "kappa",
        "alpha",
        "lambda_t",
        "activation_threshold",
    }
    clean: Dict[str, float] = {}
    for key, value in overrides.items():
        if key not in allowed:
            raise ValueError(f"Unsupported dynamics override: {key}")
        clean[key] = float(value)
    return replace(base, **clean)


def _to_numpy(array) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None

    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def _is_torch_tensor(array) -> bool:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return False
    return isinstance(array, torch.Tensor)


def _backend_from_config(config: DETMConfig, lattice: Lattice) -> Backend:
    if config.backend == "torch":
        try:
            backend = TorchBackend(device=config.device)
        except RuntimeError:
            backend = None
        if backend is not None and backend.supports(lattice):
            return backend
    return NumpyBackend()


def reset(config: DETMConfig, seed: int) -> DETMState:
    rng = np.random.default_rng(seed)
    lattice = Lattice(config.width, config.height, boundary=config.boundary)
    energy_init = rng.normal(
        loc=config.dynamics.equilibrium_energy, scale=config.initial_noise, size=(lattice.height, lattice.width)
    )
    energy_init = np.clip(energy_init, 0.0, 1.0).astype(float, copy=False)

    backend = _backend_from_config(config, lattice)
    entropy_init = NumpyBackend._compute_entropy(energy_init, config.dynamics, boundary=lattice.boundary)

    if isinstance(backend, TorchBackend):
        torch = backend._torch
        device = torch.device(backend.config.device)
        dtype = torch.float64
        field_state = DETMFieldState(
            lattice=lattice,
            energy=torch.tensor(energy_init, device=device, dtype=dtype),
            entropy=torch.tensor(entropy_init, device=device, dtype=dtype),
            internal_time=torch.zeros((lattice.height, lattice.width), device=device, dtype=dtype),
        )
    else:
        field_state = DETMFieldState(
            lattice=lattice,
            energy=energy_init,
            entropy=entropy_init,
            internal_time=np.zeros((lattice.height, lattice.width), dtype=float),
        )

    state = DETMState(field_state=field_state, step_count=0, config=config.to_dict(), dynamics=config.dynamics)
    state.store_rng(rng)
    return state


def _select_backend(state: DETMState) -> Backend:
    config = DETMConfig.from_dict(state.config) if state.config is not None else DETMConfig()
    backend_name = str(config.backend)
    device = str(config.device)

    if backend_name == "torch":
        try:
            backend = TorchBackend(device=device)
        except RuntimeError:
            backend = None
        if (
            backend is not None
            and backend.supports(state.lattice)
            and _is_torch_tensor(state.field_state.energy)
            and _is_torch_tensor(state.field_state.internal_time)
        ):
            return backend
    return NumpyBackend()


def _apply_quality_proxies(signature_vec: List[float]) -> Dict[str, float]:
    arr = np.asarray(signature_vec, dtype=float)
    jitter = float(np.abs(np.diff(arr)).mean()) if arr.size > 1 else 0.0
    oscillation = float(np.std(arr))
    saturation = float(np.mean(arr))
    return {
        "jitter_signature": jitter,
        "oscillation_score": oscillation,
        "saturation_score": saturation,
    }


def step(
    state: DETMState,
    influence: DETMInfluence | None,
    n_ticks: int,
    rng: np.random.Generator | None = None,
) -> Tuple[DETMState, Observables]:
    rng = rng or state.restore_rng()
    application = apply_influence(state.field_state, influence, rng) if influence is not None else None
    dynamics = _apply_dynamics_overrides(state.dynamics, influence.dynamics_overrides if influence is not None else None)

    start = time.perf_counter()
    backend = _select_backend(state)
    state.field_state = backend.step(state.field_state, dynamics, n_ticks)
    state.step_count += max(0, n_ticks)
    elapsed = time.perf_counter() - start
    state.store_rng(rng)

    lattice = state.lattice
    energy_arr = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width)
    entropy_arr = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width)
    time_arr = _to_numpy(state.field_state.internal_time).reshape(lattice.height, lattice.width)

    signature = digest_fields(energy_arr, entropy_arr, time_arr)
    attractors = detect_attractors(energy_arr)
    summaries = FieldSummaries(
        energy=describe_field_from_array(energy_arr),
        entropy=describe_field_from_array(entropy_arr),
        internal_time=describe_field_from_array(time_arr),
    )

    cost = {
        "cpu_time_ms": elapsed * 1000.0,
        "step_ops_estimate": float(lattice.size * max(1, n_ticks)),
        "memory_bytes_estimate": float(energy_arr.nbytes + entropy_arr.nbytes + time_arr.nbytes),
    }
    quality = _apply_quality_proxies(signature.vector)

    events: List[Dict[str, object]] = [
        {
            "type": "attractor",
            "position": attr.position,
            "strength": attr.strength,
            "stability_score": attr.stability_score,
            "period_estimate": attr.period_estimate,
        }
        for attr in attractors
    ]
    if application is not None:
        events.append({"type": "influence", **application.__dict__})

    observables = Observables(
        signature=signature,
        field_summaries=summaries,
        events=events,
        cost=cost,
        quality=quality,
    )
    return state, observables


def digest(state: DETMState) -> DETMSignature:
    lattice = state.lattice
    energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width)
    entropy = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width)
    internal_time = _to_numpy(state.field_state.internal_time).reshape(lattice.height, lattice.width)
    return digest_fields(energy, entropy, internal_time)


def serialize(state: DETMState) -> bytes:
    return serialize_state(state)


def deserialize(blob: bytes) -> DETMState:
    return deserialize_state(blob)


__all__ = [
    "FieldSummaries",
    "Observables",
    "deserialize",
    "deserialize_state",
    "digest",
    "get_schema_versions",
    "reset",
    "serialize",
    "serialize_state",
    "step",
]
