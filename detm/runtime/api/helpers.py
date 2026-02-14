"""Helper functions for runtime API execution."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.runtime.backends import Backend, NumpyBackend, TorchBackend
from detm.runtime.config import DETMConfig
from detm.runtime.state import DETMState


def apply_dynamics_overrides(base: DynamicsParameters, overrides: dict[str, float] | None) -> DynamicsParameters:
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
    clean: dict[str, float] = {}
    for key, value in overrides.items():
        if key not in allowed:
            raise ValueError(f"Unsupported dynamics override: {key}")
        clean[key] = float(value)
    return replace(base, **clean)


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


def backend_from_config(config: DETMConfig, lattice: Lattice) -> Backend:
    if config.backend == "torch":
        try:
            backend = TorchBackend(device=config.device)
        except RuntimeError:
            backend = None
        if backend is not None and backend.supports(lattice):
            return backend
    return NumpyBackend()


def select_backend(state: DETMState) -> Backend:
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
            and is_torch_tensor(state.field_state.energy)
            and is_torch_tensor(state.field_state.internal_time)
        ):
            return backend
    return NumpyBackend()


def apply_quality_proxies(signature_vec: list[float]) -> dict[str, float]:
    arr = np.asarray(signature_vec, dtype=float)
    jitter = float(np.abs(np.diff(arr)).mean()) if arr.size > 1 else 0.0
    oscillation = float(np.std(arr))
    saturation = float(np.mean(arr))
    return {
        "jitter_signature": jitter,
        "oscillation_score": oscillation,
        "saturation_score": saturation,
    }


def estimate_array_bytes(x: Any) -> float:
    if is_torch_tensor(x):
        return float(x.numel() * x.element_size())
    arr = np.asarray(x)
    return float(arr.nbytes)


__all__ = [
    "apply_dynamics_overrides",
    "apply_quality_proxies",
    "backend_from_config",
    "estimate_array_bytes",
    "is_torch_tensor",
    "select_backend",
    "to_numpy",
]
