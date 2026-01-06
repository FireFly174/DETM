"""Public runtime API for DETM integration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from core.entropy import DynamicsParameters, compute_entropy, step as entropy_step
from core.fields import FieldState, Lattice, ScalarField
from core.invariants import describe_field
from runtime.config import DETMConfig
from runtime.diagnostics.attractors import detect_attractors
from runtime.influence import DETMInfluence, apply_influence
from runtime.serialization import deserialize_state, serialize_state
from runtime.signature import DETMSignature, digest_fields
from runtime.state import DETMState


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

def reset(config: DETMConfig, seed: int) -> DETMState:
    rng = np.random.default_rng(seed)
    lattice = Lattice(config.width, config.height, boundary=config.boundary)
    energy_values = rng.normal(loc=config.dynamics.equilibrium_energy, scale=config.initial_noise, size=lattice.size)
    energy_values = np.clip(energy_values, 0.0, 1.0).reshape(-1)

    energy = ScalarField(lattice, energy_values.tolist())
    entropy = compute_entropy(energy, config.dynamics)
    internal_time = ScalarField.constant(lattice, value=0.0)
    field_state = FieldState(energy=energy, entropy=entropy, internal_time=internal_time)
    state = DETMState(field_state=field_state, step_count=0, config=config.to_dict(), dynamics=config.dynamics)
    state.store_rng(rng)
    return state


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


def step(state: DETMState, influence: DETMInfluence, n_ticks: int, rng: np.random.Generator | None = None) -> Tuple[DETMState, Observables]:
    rng = rng or state.restore_rng()
    application = apply_influence(state.field_state, influence, rng)

    start = time.perf_counter()
    for _ in range(max(1, n_ticks)):
        state.field_state = entropy_step(state.field_state, state.dynamics)
        state.step_count += 1
    elapsed = time.perf_counter() - start
    state.store_rng(rng)

    lattice = state.lattice
    energy_arr = np.asarray(state.field_state.energy.values).reshape(lattice.height, lattice.width)
    entropy_arr = np.asarray(state.field_state.entropy.values).reshape(lattice.height, lattice.width)
    time_arr = np.asarray(state.field_state.internal_time.values).reshape(lattice.height, lattice.width)

    signature = digest_fields(energy_arr, entropy_arr, time_arr)
    attractors = detect_attractors(energy_arr)
    summaries = FieldSummaries(
        energy=_moments_to_dict(describe_field(state.field_state.energy)),
        entropy=_moments_to_dict(describe_field(state.field_state.entropy)),
        internal_time=_moments_to_dict(describe_field(state.field_state.internal_time)),
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
    energy = np.asarray(state.field_state.energy.values).reshape(lattice.height, lattice.width)
    entropy = np.asarray(state.field_state.entropy.values).reshape(lattice.height, lattice.width)
    internal_time = np.asarray(state.field_state.internal_time.values).reshape(lattice.height, lattice.width)
    return digest_fields(energy, entropy, internal_time)


def serialize(state: DETMState) -> bytes:
    return serialize_state(state)


def deserialize(blob: bytes) -> DETMState:
    return deserialize_state(blob)


def _moments_to_dict(moments) -> Dict[str, float]:
    return {
        "minimum": float(moments.minimum),
        "maximum": float(moments.maximum),
        "mean": float(moments.mean),
        "variance": float(moments.variance),
    }


__all__ = ["Observables", "FieldSummaries", "digest", "deserialize", "reset", "serialize", "step"]
