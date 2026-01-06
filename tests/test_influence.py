from __future__ import annotations

import numpy as np

from detm.core.fields import Lattice
from detm.runtime.influence import DETMInfluence, apply_influence
from detm.runtime.state import DETMFieldState


def _field_state(w: int, h: int) -> DETMFieldState:
    lattice = Lattice(w, h, boundary="periodic")
    zeros = np.zeros((h, w), dtype=float)
    return DETMFieldState(lattice=lattice, energy=zeros.copy(), entropy=zeros.copy(), internal_time=zeros.copy())


def test_ring_mask_is_thinner_than_pulse_mask() -> None:
    rng = np.random.default_rng(0)

    base = _field_state(11, 11)
    pulse = DETMInfluence(symbol_id="pulse", amplitude=0.1, region=(5, 5, 4))
    app_pulse = apply_influence(base, pulse, rng)

    base2 = _field_state(11, 11)
    ring = DETMInfluence(symbol_id="ring", amplitude=0.1, region=(5, 5, 4))
    app_ring = apply_influence(base2, ring, rng)

    assert app_ring.affected_fraction < app_pulse.affected_fraction


def test_joystick_field_produces_left_right_gradient() -> None:
    rng = np.random.default_rng(0)
    state = _field_state(7, 3)
    infl = DETMInfluence(symbol_id="joystick_field", amplitude=0.5, external_features={"dx": 1.0, "dy": 0.0})
    apply_influence(state, infl, rng)

    mid_row = 1
    assert float(state.energy[mid_row, -1]) > float(state.energy[mid_row, 0])


def test_source_sink_forces_points() -> None:
    rng = np.random.default_rng(0)
    state = _field_state(6, 6)
    infl = DETMInfluence(
        symbol_id="source_sink",
        amplitude=1.0,
        external_features={"src_x": 0, "src_y": 0, "dst_x": 5, "dst_y": 5, "src_value": 1.0, "dst_value": 0.0},
    )
    apply_influence(state, infl, rng)

    assert float(state.energy[0, 0]) == 1.0
    assert float(state.energy[5, 5]) == 0.0

