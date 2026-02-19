from __future__ import annotations

from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm_app import (
    CommitJsonlWriter,
    DetmSession,
    EventBus,
    JsonlTraceWriter,
    OperatorDecisionWriter,
    TickRunner,
    TickScheduler,
    parse_invariant_streams,
)


def test_detm_app_shim_exports_run_primitives():
    bus = EventBus()
    scheduler = TickScheduler(bus=bus, tick0=0)
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=4,
        height=4,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=100, bus=bus)
    runner = TickRunner(session, scheduler)
    runner.run(2)

    assert int(session.state.step_count) == 2
    assert int(scheduler.tick) == 2


def test_detm_app_shim_exports_parse_invariant_streams():
    specs = parse_invariant_streams(["inv0=2/5"])
    assert len(specs) == 1
    assert str(specs[0].stream_id) == "inv0"


def test_detm_app_shim_exports_subscribers():
    assert JsonlTraceWriter is not None
    assert CommitJsonlWriter is not None
    assert OperatorDecisionWriter is not None
