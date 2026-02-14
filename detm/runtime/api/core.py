"""Public runtime API for DETM integration."""

from __future__ import annotations

import time
from typing import Tuple

import numpy as np

from detm.core.fields import Lattice
from detm.runtime.api.helpers import (
    apply_dynamics_overrides as _apply_dynamics_overrides,
    apply_quality_proxies as _apply_quality_proxies,
    backend_from_config as _backend_from_config,
    estimate_array_bytes as _estimate_array_bytes,
    select_backend as _select_backend,
    to_numpy as _to_numpy,
)
from detm.runtime.api.models import FieldSummaries, Observables
from detm.runtime.backends import NumpyBackend, TorchBackend
from detm.runtime.config import DETMConfig
from detm.runtime.diagnostics.attractors import detect_attractors
from detm.runtime.influence import DETMInfluence, apply_influence
from detm.runtime.pattern_memory import get_pattern_runtime_for_state
from detm.runtime.refinement import maybe_apply_refinement
from detm.runtime.serialization import deserialize_state, serialize_state
from detm.runtime.schemas import get_schema_versions
from detm.runtime.signature import DETMSignature, describe_field_any, digest_fields_any
from detm.runtime.state import DETMFieldState, DETMState


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


def step(
    state: DETMState,
    influence: DETMInfluence | None,
    n_ticks: int,
    rng: np.random.Generator | None = None,
) -> Tuple[DETMState, Observables]:
    rng = rng or state.restore_rng()
    config = DETMConfig.from_dict(state.config) if state.config is not None else DETMConfig()
    dynamics = _apply_dynamics_overrides(state.dynamics, influence.dynamics_overrides if influence is not None else None)
    application = None
    if influence is not None:
        is_override_only = (
            abs(float(influence.amplitude)) < 1e-12
            and influence.mask is None
            and influence.region is None
            and influence.external_features is None
            and influence.seed is None
            and influence.phase is None
            and influence.duration is None
            and bool(influence.dynamics_overrides)
        )
        if not is_override_only:
            application = apply_influence(state.field_state, influence, rng)

    start = time.perf_counter()
    backend = _select_backend(state)
    state.field_state = backend.step(state.field_state, dynamics, n_ticks)
    state.step_count += max(0, n_ticks)
    elapsed = time.perf_counter() - start
    state.store_rng(rng)

    pattern_runtime = get_pattern_runtime_for_state(state=state, config=config)
    refinement_runtime = getattr(state, "_refinement_runtime", None)
    if not isinstance(refinement_runtime, dict):
        refinement_runtime = {}
        setattr(state, "_refinement_runtime", refinement_runtime)
    operator_signal_score = getattr(state, "_operator_capacity_signal_score", None)
    if operator_signal_score is not None:
        try:
            refinement_runtime["operator_capacity_signal_score"] = float(operator_signal_score)
        except (TypeError, ValueError):
            pass
    fabric_snapshot = getattr(state, "_fabric_quorum_snapshot", None)
    if isinstance(fabric_snapshot, dict):
        refinement_runtime["fabric_quorum_snapshot"] = dict(fabric_snapshot)
    refinement_event = maybe_apply_refinement(
        field_state=state.field_state,
        dynamics=dynamics,
        allow_refinement=bool(config.level_policy.allow_refinement),
        capacity_overflow_ratio_threshold=float(
            config.level_policy.refinement_capacity_overflow_ratio_threshold
        ),
        capacity_overflow_mean_threshold=float(
            config.level_policy.refinement_capacity_overflow_mean_threshold
        ),
        capacity_min_signals=int(config.level_policy.refinement_capacity_min_signals),
        capacity_temporal_ratio_threshold=float(
            config.level_policy.refinement_capacity_temporal_ratio_threshold
        ),
        capacity_temporal_window=int(config.level_policy.refinement_capacity_temporal_window),
        capacity_temporal_required_hits=int(config.level_policy.refinement_capacity_temporal_required_hits),
        capacity_learned_hits_threshold=int(config.level_policy.refinement_capacity_learned_hits_threshold),
        capacity_cross_level_window=int(config.level_policy.refinement_capacity_cross_level_window),
        capacity_cross_level_min_levels=int(config.level_policy.refinement_capacity_cross_level_min_levels),
        capacity_operator_score_threshold=float(config.level_policy.refinement_capacity_operator_score_threshold),
        capacity_cross_node_min_signals=int(config.level_policy.refinement_capacity_cross_node_min_signals),
        capacity_distributed_accepted_min=int(config.level_policy.refinement_capacity_distributed_accepted_min),
        capacity_signed_acks_min=int(config.level_policy.refinement_capacity_signed_acks_min),
        capacity_consensus_accepted_min=int(config.level_policy.refinement_capacity_consensus_accepted_min),
        capacity_crypto_validator_coverage_min=float(
            config.level_policy.refinement_capacity_crypto_validator_coverage_min
        ),
        capacity_attestation_validator_ids=tuple(config.level_policy.refinement_capacity_attestation_validator_ids),
        capacity_attestation_min_coverage=float(
            config.level_policy.refinement_capacity_attestation_min_coverage
        ),
        capacity_byzantine_clean_min=int(config.level_policy.refinement_capacity_byzantine_clean_min),
        pattern_runtime=pattern_runtime,
        step_count=int(state.step_count),
        active_level=str(config.level_policy.active_level),
        pattern_mode=str(config.observables_mode),
        runtime_memory=refinement_runtime,
    )

    lattice = state.lattice
    energy = state.field_state.energy.reshape(lattice.height, lattice.width)
    entropy = state.field_state.entropy.reshape(lattice.height, lattice.width)
    internal_time = state.field_state.internal_time.reshape(lattice.height, lattice.width)

    signature = digest_fields_any(energy, entropy, internal_time)
    summaries = FieldSummaries(
        energy=describe_field_any(energy),
        entropy=describe_field_any(entropy),
        internal_time=describe_field_any(internal_time),
    )

    attractors = []
    if str(config.observables_mode).strip().lower() == "cpu_full":
        # Explicitly opt-in: this path materializes a dense CPU copy for analysis.
        energy_arr = _to_numpy(energy)
        attractors = detect_attractors(energy_arr)

    cost = {
        "cpu_time_ms": elapsed * 1000.0,
        "step_ops_estimate": float(lattice.size * max(1, n_ticks)),
        "memory_bytes_estimate": _estimate_array_bytes(energy)
        + _estimate_array_bytes(entropy)
        + _estimate_array_bytes(internal_time),
    }
    quality = _apply_quality_proxies(signature.vector)

    events: list[dict[str, object]] = []
    if refinement_event is not None:
        events.append(refinement_event)
    events.extend(
        [
            {
                "type": "attractor",
                "position": attr.position,
                "strength": attr.strength,
                "stability_score": attr.stability_score,
                "period_estimate": attr.period_estimate,
            }
            for attr in attractors
        ]
    )
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
    energy = state.field_state.energy.reshape(lattice.height, lattice.width)
    entropy = state.field_state.entropy.reshape(lattice.height, lattice.width)
    internal_time = state.field_state.internal_time.reshape(lattice.height, lattice.width)
    return digest_fields_any(energy, entropy, internal_time)


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
