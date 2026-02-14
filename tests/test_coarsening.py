from __future__ import annotations

from fractions import Fraction

from detm_app.runtime.coarsening import InvariantCoarsener, InvariantStreamSpec
from detm_app.runtime.session import DetmSession
from detm.runtime.config import DETMConfig


def test_invariant_stream_emits_expected_ticks():
    cfg = DETMConfig(width=6, height=6, backend="numpy", device="cpu", initial_noise=0.01)
    sess = DetmSession.create(cfg, seed=123)

    emitted = []
    sess.bus.add_event_listener("invariant_tick", lambda **p: emitted.append(p))
    InvariantCoarsener.attach(sess.bus, [InvariantStreamSpec("inv_0p1", Fraction(1, 10))])

    for _ in range(20):
        sess.step(None, 1, rng=sess.state.restore_rng())

    assert len(emitted) == 20
    assert [e["l0_tick"] for e in emitted] == list(range(1, 21))
    assert [e["l0_tick"] for e in emitted if e["boundary_crossed"]] == [10, 20]
    assert emitted[8]["invariant_index"] == 0  # l0_tick=9
    assert emitted[9]["invariant_index"] == 1  # l0_tick=10
    assert emitted[9]["phase_num"] == 0  # exact boundary (10/10)


def test_invariant_fractional_dt_emits_multiple_per_window():
    cfg = DETMConfig(width=6, height=6, backend="numpy", device="cpu", initial_noise=0.01)
    sess = DetmSession.create(cfg, seed=7)

    emitted = []
    sess.bus.add_event_listener("invariant_tick", lambda **p: emitted.append(p))
    # dt=0.16 => 4/25; over 25 l0 ticks, should emit 4 invariant ticks
    InvariantCoarsener.attach(sess.bus, [InvariantStreamSpec("inv_0p16", Fraction(4, 25))])

    for _ in range(25):
        sess.step(None, 1, rng=sess.state.restore_rng())

    assert len(emitted) == 25
    assert [e["l0_tick"] for e in emitted if e["boundary_crossed"]] == [7, 13, 19, 25]
    assert emitted[-1]["invariant_index"] == 4
    assert emitted[-1]["phase_num"] == 0
    assert emitted[-1]["time_num"] == 25 * 4

