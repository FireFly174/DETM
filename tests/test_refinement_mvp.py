from __future__ import annotations

import json

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm_app.session import DetmSession
from detm_app.subscribers import JsonlTraceWriter


def _seed_overflow_hotspot(session: DetmSession) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.zeros((h, w), dtype=float)
    energy[h // 2, w // 2] = 3.0
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(energy, session.config.dynamics, boundary=state.lattice.boundary)


def _seed_nonfinite_hotspot(session: DetmSession) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.zeros((h, w), dtype=float)
    energy[h // 2, w // 2] = np.nan
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = np.zeros_like(energy)


def _seed_capacity_pressure(session: DetmSession) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.full((h, w), 3.0, dtype=float)
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(energy, session.config.dynamics, boundary=state.lattice.boundary)


def _seed_capacity_mild_overflow(session: DetmSession) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.full((h, w), 1.05, dtype=float)
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(energy, session.config.dynamics, boundary=state.lattice.boundary)


def test_refinement_emits_event_and_reports_correction():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=1)
    _seed_overflow_hotspot(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "energy_overflow"
    correction = dict(event.get("correction", {}))

    assert int(dict(event.get("roi", {})).get("area", 0)) > 0
    assert float(correction.get("blend", 0.0)) > 0.0
    assert int(correction.get("overflow_count_after", 999)) < int(correction.get("overflow_count_before", 0))


def test_refinement_is_disabled_by_policy_flag():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=False, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=1)
    _seed_overflow_hotspot(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert refinement_events == []


def test_trace_records_refinement_event(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=5)
    _seed_overflow_hotspot(session)
    trace_path = tmp_path / "trace.jsonl"
    JsonlTraceWriter.attach(session.bus, trace_path, metric_plugins=[])

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(entries) >= 1
    first = entries[0]
    events = list(first.get("events", []))
    assert any(str(event.get("type")) == "refinement" for event in events)


def test_refinement_sanitizes_nonfinite_state():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=9)
    _seed_nonfinite_hotspot(session)

    obs = session.step(None, 0, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "state_nonfinite"
    counts = dict(event.get("detector_nonfinite_counts", {}))
    assert int(counts.get("total", 0)) >= 1
    correction = dict(event.get("correction", {}))
    assert int(correction.get("nonfinite_total_after", 999)) == 0

    energy = np.asarray(session.state.field_state.energy, dtype=float)
    entropy = np.asarray(session.state.field_state.entropy, dtype=float)
    internal_time = np.asarray(session.state.field_state.internal_time, dtype=float)
    assert bool(np.isfinite(energy).all())
    assert bool(np.isfinite(entropy).all())
    assert bool(np.isfinite(internal_time).all())


def test_refinement_detects_capacity_pressure_for_mass_overflow():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(allow_refinement=True, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=11)
    _seed_capacity_pressure(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    assert bool(event.get("detector_capacity_triggered")) is True
    assert float(event.get("detector_overflow_ratio", 0.0)) >= float(event.get("detector_capacity_ratio_threshold", 1.0))
    assert int(event.get("detector_capacity_secondary_hits", 0)) >= int(event.get("detector_capacity_secondary_required", 0))


def test_refinement_capacity_detector_respects_policy_threshold():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=2.0,
        ),
    )
    session = DetmSession.create(cfg, seed=12)
    _seed_capacity_pressure(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "energy_overflow"
    assert bool(event.get("detector_capacity_triggered")) is False


def test_refinement_capacity_detector_multisignal_policy_gate():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=0.5,
            refinement_capacity_min_signals=2,
        ),
    )
    session = DetmSession.create(cfg, seed=13)
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "energy_overflow"
    assert bool(event.get("detector_capacity_triggered")) is False
    assert int(event.get("detector_capacity_min_signals", 0)) == 2
    assert int(event.get("detector_capacity_secondary_required", 0)) == 1
    assert int(event.get("detector_capacity_secondary_hits", 0)) == 0


def test_refinement_capacity_detector_temporal_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=0.5,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=0.15,
            refinement_capacity_temporal_window=3,
            refinement_capacity_temporal_required_hits=3,
        ),
    )
    session = DetmSession.create(cfg, seed=14)
    detectors: list[str] = []
    temporal_passed: list[bool] = []

    for _ in range(3):
        _seed_capacity_mild_overflow(session)
        obs = session.step(None, 1, rng=session.state.restore_rng())
        events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
        assert len(events) == 1
        event = events[0]
        detectors.append(str(event.get("detector")))
        signals = dict(event.get("detector_capacity_signals", {}))
        temporal = dict(signals.get("temporal_sustained", {}))
        temporal_passed.append(bool(temporal.get("passed")))

    session.close()

    assert detectors[:2] == ["energy_overflow", "energy_overflow"]
    assert detectors[2] == "capacity_pressure"
    assert temporal_passed == [False, False, True]


def test_refinement_capacity_detector_learned_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        pattern_reuse_enabled=True,
        pattern_prune_error_threshold=1.0,
        pattern_prune_deviation_threshold=10.0,
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=2,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=2,
        ),
    )
    session = DetmSession.create(cfg, seed=15)
    detectors: list[str] = []
    learned_passed: list[bool] = []

    for _ in range(3):
        _seed_capacity_mild_overflow(session)
        obs = session.step(None, 1, rng=session.state.restore_rng())
        events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
        assert len(events) == 1
        event = events[0]
        detectors.append(str(event.get("detector")))
        signals = dict(event.get("detector_capacity_signals", {}))
        learned = dict(signals.get("learned_reuse", {}))
        learned_passed.append(bool(learned.get("passed")))

    session.close()

    assert detectors[:2] == ["energy_overflow", "energy_overflow"]
    assert detectors[2] == "capacity_pressure"
    assert learned_passed == [False, False, True]


def test_refinement_capacity_detector_cross_level_signal_can_trigger():
    def _cfg(active_level: str) -> DETMConfig:
        return DETMConfig(
            backend="numpy",
            device="cpu",
            width=11,
            height=11,
            initial_noise=0.0,
            dynamics=DynamicsParameters(energy_bounds=None),
                level_policy=LevelPolicy(
                    active_level=active_level,
                    allow_refinement=True,
                    commit_stride=1,
                    refinement_capacity_overflow_ratio_threshold=0.0,
                    refinement_capacity_overflow_mean_threshold=1.0,
                    refinement_capacity_min_signals=2,
                refinement_capacity_temporal_ratio_threshold=2.0,
                refinement_capacity_temporal_window=2,
                refinement_capacity_temporal_required_hits=2,
                refinement_capacity_learned_hits_threshold=0,
                refinement_capacity_cross_level_window=2,
                refinement_capacity_cross_level_min_levels=2,
            ),
        )

    session = DetmSession.create(_cfg("L0"), seed=16)
    detectors: list[str] = []
    cross_level_passed: list[bool] = []

    for level in ["L0", "L1"]:
        session.config = _cfg(level)
        session.state.config = session.config.to_dict()
        _seed_capacity_mild_overflow(session)
        obs = session.step(None, 1, rng=session.state.restore_rng())
        events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
        assert len(events) == 1
        event = events[0]
        detectors.append(str(event.get("detector")))
        signals = dict(event.get("detector_capacity_signals", {}))
        cross_level = dict(signals.get("cross_level", {}))
        cross_level_passed.append(bool(cross_level.get("passed")))

    session.close()

    assert detectors == ["energy_overflow", "capacity_pressure"]
    assert cross_level_passed == [False, True]


def test_refinement_capacity_detector_operator_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=999,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=3,
            refinement_capacity_operator_score_threshold=0.8,
            refinement_capacity_cross_node_min_signals=3,
        ),
    )
    session = DetmSession.create(cfg, seed=17)
    setattr(session.state, "_operator_capacity_signal_score", 1.0)
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    signals = dict(event.get("detector_capacity_signals", {}))
    operator_signal = dict(signals.get("operator_signal", {}))
    assert bool(operator_signal.get("passed")) is True


def test_refinement_capacity_detector_cross_node_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=999,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=3,
            refinement_capacity_operator_score_threshold=999.0,
            refinement_capacity_cross_node_min_signals=2,
        ),
    )
    session = DetmSession.create(cfg, seed=18)
    setattr(
        session.state,
        "_fabric_quorum_snapshot",
        {
            "replay_checks_failed": 1,
            "delivery_receipts": {"rejected_count": 0, "pending_count": 1},
        },
    )
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    signals = dict(event.get("detector_capacity_signals", {}))
    cross_node = dict(signals.get("cross_node", {}))
    assert bool(cross_node.get("passed")) is True


def test_refinement_capacity_detector_distributed_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=999,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=3,
            refinement_capacity_operator_score_threshold=999.0,
            refinement_capacity_cross_node_min_signals=3,
            refinement_capacity_distributed_accepted_min=1,
            refinement_capacity_signed_acks_min=0,
        ),
    )
    session = DetmSession.create(cfg, seed=19)
    setattr(
        session.state,
        "_fabric_quorum_snapshot",
        {
            "accepted_count": 1,
            "evaluations": [],
        },
    )
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    signals = dict(event.get("detector_capacity_signals", {}))
    distributed = dict(signals.get("distributed_quorum", {}))
    assert bool(distributed.get("passed")) is True


def test_refinement_capacity_detector_signed_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=999,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=3,
            refinement_capacity_operator_score_threshold=999.0,
            refinement_capacity_cross_node_min_signals=3,
            refinement_capacity_distributed_accepted_min=0,
            refinement_capacity_signed_acks_min=2,
        ),
    )
    session = DetmSession.create(cfg, seed=20)
    setattr(
        session.state,
        "_fabric_quorum_snapshot",
        {
            "accepted_count": 0,
            "evaluations": [
                {
                    "proof": {"accepted": 1},
                    "trust": {"accepted": 1},
                }
            ],
        },
    )
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    signals = dict(event.get("detector_capacity_signals", {}))
    signed = dict(signals.get("signed_ack_evidence", {}))
    assert bool(signed.get("passed")) is True


def test_refinement_capacity_detector_consensus_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=999,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=3,
            refinement_capacity_operator_score_threshold=999.0,
            refinement_capacity_cross_node_min_signals=3,
            refinement_capacity_distributed_accepted_min=0,
            refinement_capacity_signed_acks_min=0,
            refinement_capacity_consensus_accepted_min=1,
            refinement_capacity_crypto_validator_coverage_min=0.0,
        ),
    )
    session = DetmSession.create(cfg, seed=21)
    setattr(
        session.state,
        "_fabric_quorum_snapshot",
        {
            "accepted_count": 1,
            "pending_count": 0,
            "rejected_count": 0,
            "evaluations": [],
        },
    )
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    signals = dict(event.get("detector_capacity_signals", {}))
    consensus = dict(signals.get("consensus_grade", {}))
    assert bool(consensus.get("passed")) is True


def test_refinement_capacity_detector_cryptographic_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=999,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=3,
            refinement_capacity_operator_score_threshold=999.0,
            refinement_capacity_cross_node_min_signals=3,
            refinement_capacity_distributed_accepted_min=0,
            refinement_capacity_signed_acks_min=0,
            refinement_capacity_consensus_accepted_min=0,
            refinement_capacity_crypto_validator_coverage_min=1.0,
        ),
    )
    session = DetmSession.create(cfg, seed=22)
    setattr(
        session.state,
        "_fabric_quorum_snapshot",
        {
            "accepted_count": 0,
            "pending_count": 0,
            "rejected_count": 0,
            "validator_registry": {"validators": ["validator-1", "validator-2"]},
            "evaluations": [
                {
                    "status": "accepted",
                    "proof": {"unique_accepted_validators": ["validator-1", "validator-2"]},
                    "trust": {"unique_accepted_validators": ["validator-1", "validator-2"]},
                }
            ],
        },
    )
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    signals = dict(event.get("detector_capacity_signals", {}))
    crypto = dict(signals.get("cryptographic_grade", {}))
    assert bool(crypto.get("passed")) is True


def test_refinement_capacity_detector_attestation_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=999,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=3,
            refinement_capacity_operator_score_threshold=999.0,
            refinement_capacity_cross_node_min_signals=3,
            refinement_capacity_distributed_accepted_min=0,
            refinement_capacity_signed_acks_min=0,
            refinement_capacity_consensus_accepted_min=0,
            refinement_capacity_crypto_validator_coverage_min=0.0,
            refinement_capacity_attestation_validator_ids=("validator-1", "validator-2"),
            refinement_capacity_attestation_min_coverage=1.0,
            refinement_capacity_byzantine_clean_min=0,
        ),
    )
    session = DetmSession.create(cfg, seed=23)
    setattr(
        session.state,
        "_fabric_quorum_snapshot",
        {
            "accepted_count": 0,
            "pending_count": 0,
            "rejected_count": 0,
            "evaluations": [
                {
                    "status": "accepted",
                    "proof": {"unique_accepted_validators": ["validator-1", "validator-2"]},
                    "trust": {"unique_accepted_validators": ["validator-1", "validator-2"]},
                }
            ],
        },
    )
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    signals = dict(event.get("detector_capacity_signals", {}))
    attestation = dict(signals.get("attestation_grade", {}))
    assert bool(attestation.get("passed")) is True


def test_refinement_capacity_detector_byzantine_signal_can_trigger():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        level_policy=LevelPolicy(
            allow_refinement=True,
            commit_stride=1,
            refinement_capacity_overflow_ratio_threshold=0.15,
            refinement_capacity_overflow_mean_threshold=1.0,
            refinement_capacity_min_signals=2,
            refinement_capacity_temporal_ratio_threshold=2.0,
            refinement_capacity_temporal_window=2,
            refinement_capacity_temporal_required_hits=2,
            refinement_capacity_learned_hits_threshold=999,
            refinement_capacity_cross_level_window=2,
            refinement_capacity_cross_level_min_levels=3,
            refinement_capacity_operator_score_threshold=999.0,
            refinement_capacity_cross_node_min_signals=3,
            refinement_capacity_distributed_accepted_min=0,
            refinement_capacity_signed_acks_min=0,
            refinement_capacity_consensus_accepted_min=0,
            refinement_capacity_crypto_validator_coverage_min=0.0,
            refinement_capacity_attestation_validator_ids=(),
            refinement_capacity_attestation_min_coverage=0.0,
            refinement_capacity_byzantine_clean_min=1,
        ),
    )
    session = DetmSession.create(cfg, seed=24)
    setattr(
        session.state,
        "_fabric_quorum_snapshot",
        {
            "accepted_count": 1,
            "pending_count": 0,
            "rejected_count": 0,
            "replay_checks_failed": 0,
            "delivery_receipts": {"rejected_count": 0, "pending_count": 0},
            "evaluations": [],
        },
    )
    _seed_capacity_mild_overflow(session)

    obs = session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    refinement_events = [event for event in list(obs.events) if str(event.get("type")) == "refinement"]
    assert len(refinement_events) == 1
    event = refinement_events[0]
    assert str(event.get("detector")) == "capacity_pressure"
    signals = dict(event.get("detector_capacity_signals", {}))
    byzantine = dict(signals.get("byzantine_grade", {}))
    assert bool(byzantine.get("passed")) is True
