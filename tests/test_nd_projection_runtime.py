from __future__ import annotations

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.metrics.base import MetricContext
from detm.metrics.boundary_flux import BoundaryFluxMetrics
from detm.runtime.api.step_flow import build_observables
from detm.runtime.config import DETMConfig
from detm.runtime.diagnostics.attractors import detect_attractors, signature_from_state
from detm.runtime.state import DETMFieldState, DETMState


def _make_nd_state(*, shape: tuple[int, ...] = (2, 6, 6), peak: float = 3.0) -> DETMState:
    lattice = Lattice(width=shape[-1], height=shape[-2], boundary="periodic")
    energy = np.zeros(shape, dtype=float)
    energy[-1, 2, 3] = peak
    entropy = np.zeros(shape, dtype=float)
    internal_time = np.zeros(shape, dtype=float)
    config = DETMConfig(shape=shape, backend="numpy", device="cpu", observables_mode="cpu_full")
    state = DETMState(
        field_state=DETMFieldState(
            lattice=lattice,
            energy=energy,
            entropy=entropy,
            internal_time=internal_time,
            shape=shape,
        ),
        config=config.to_dict(),
        dynamics=DynamicsParameters(),
    )
    return state


def test_detect_attractors_projects_nd_state_to_canonical_plane():
    state = _make_nd_state()

    attractors = detect_attractors(state, threshold=0.5, top_k=2)

    assert attractors
    assert attractors[0].position == (3, 2)


def test_signature_from_state_accepts_nd_state():
    state = _make_nd_state()

    sig = signature_from_state(state)

    assert sig.shape == (9,)
    assert float(sig[0]) >= 0.0


def test_build_observables_accepts_nd_state_via_projection():
    state = _make_nd_state()
    config = DETMConfig.from_dict(dict(state.config or {}))

    observables = build_observables(
        state=state,
        config=config,
        n_ticks=1,
        elapsed_s=0.01,
        refinement_event=None,
        influence_application=None,
    )

    assert observables.signature.version
    assert observables.field_summaries.energy["maximum"] > 1.0
    assert any(str(event.get("type")) == "attractor" for event in observables.events)


def test_boundary_flux_metrics_accept_nd_state_via_projection():
    state = _make_nd_state()
    cfg = DETMConfig.from_dict(dict(state.config or {}))
    state.config = {**cfg.to_dict(), "trace_boundary_flux": True}
    observables = build_observables(
        state=state,
        config=cfg,
        n_ticks=1,
        elapsed_s=0.01,
        refinement_event=None,
        influence_application=None,
    )

    payload = BoundaryFluxMetrics().compute(
        MetricContext(state=state, observables=observables, influence=None, n_ticks=1)
    )

    assert payload["enabled"] is True
    assert "phi_outer_normal_abs" in payload
    assert float(payload["grad_mag_mean"]) >= 0.0
