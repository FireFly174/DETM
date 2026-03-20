"""Public runtime API for DETM integration."""

from __future__ import annotations

import time
from typing import Tuple

import numpy as np

from detm.core.fields import Lattice
from detm.runtime.api.helpers import (
    apply_dynamics_overrides as _apply_dynamics_overrides,
    select_backend as _select_backend,
)
from detm.runtime.api.models import FieldSummaries, Observables
from detm.runtime.api.reset_flow import build_initial_field_state
from detm.runtime.api.step_flow import (
    build_observables as _build_observables_flow,
    ensure_refinement_runtime_memory as _ensure_refinement_runtime_memory_flow,
    is_override_only_influence as _is_override_only_influence_flow,
    maybe_refinement_event as _maybe_refinement_event_flow,
)
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence, apply_influence
from detm.runtime.pattern_memory import get_pattern_runtime_for_state
from detm.runtime.serialization import deserialize_state, migrate_state, serialize_state
from detm.runtime.schemas import get_schema_versions
from detm.runtime.signature import DETMSignature, digest_fields_any, project_field_plane_any
from detm.runtime.state import DETMState


def reset(config: DETMConfig, seed: int) -> DETMState:
    rng = np.random.default_rng(seed)
    lattice = Lattice(config.width, config.height, boundary=config.boundary)
    field_state = build_initial_field_state(config=config, lattice=lattice, rng=rng)

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
        is_override_only = _is_override_only_influence_flow(influence)
        if not is_override_only:
            application = apply_influence(state.field_state, influence, rng)

    start = time.perf_counter()
    backend = _select_backend(state)
    state.field_state = backend.step(state.field_state, dynamics, n_ticks)
    state.step_count += max(0, n_ticks)
    elapsed = time.perf_counter() - start
    state.store_rng(rng)

    pattern_runtime = get_pattern_runtime_for_state(state=state, config=config)
    refinement_runtime = _ensure_refinement_runtime_memory_flow(state)
    refinement_event = _maybe_refinement_event_flow(
        state=state,
        config=config,
        dynamics=dynamics,
        pattern_runtime=pattern_runtime,
        refinement_runtime=refinement_runtime,
    )
    observables = _build_observables_flow(
        state=state,
        config=config,
        n_ticks=int(n_ticks),
        elapsed_s=float(elapsed),
        refinement_event=refinement_event,
        influence_application=application,
    )
    return state, observables


def digest(state: DETMState) -> DETMSignature:
    energy = project_field_plane_any(state.field_state.energy)
    entropy = project_field_plane_any(state.field_state.entropy)
    internal_time = project_field_plane_any(state.field_state.internal_time)
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
    "migrate_state",
    "reset",
    "serialize",
    "serialize_state",
    "step",
]
