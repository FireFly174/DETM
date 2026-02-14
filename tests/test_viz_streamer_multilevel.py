from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import VizStreamer
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy, ObservabilityProfile, PolicyDecision


@dataclass
class _CaptureTransport:
    frames: list[dict[str, Any]] = field(default_factory=list)

    def send_state(
        self,
        *,
        state_blob: bytes,
        tick: int,
        signature: list[float] | None = None,
        meta: dict[str, object] | None = None,
    ) -> None:
        self.frames.append(
            {
                "state_blob": bytes(state_blob),
                "tick": int(tick),
                "signature": None if signature is None else [float(x) for x in list(signature)],
                "meta": None if meta is None else dict(meta),
            }
        )

    def close(self) -> None:
        return


def test_viz_streamer_step_emits_active_level_meta():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(active_level="L2", microsteps_per_global_tick=1, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=41)
    transport = _CaptureTransport()
    streamer = VizStreamer.attach(session.bus, transport, every_steps=1)

    try:
        session.step(None, 1)
        assert len(transport.frames) == 1
        frame = transport.frames[0]
        assert int(frame["tick"]) == 1
        meta = dict(frame["meta"] or {})
        assert str(meta.get("active_level")) == "L2"
        assert int(meta.get("chunk_n_ticks", 0)) == 1
        assert int(meta.get("requested_n_ticks", 0)) == 1
        assert int(meta.get("step_requested_n_ticks", 0)) == 1
        assert int(meta.get("step_effective_n_ticks", 0)) == 1
    finally:
        streamer.detach()
        session.close()


def test_viz_streamer_step_emits_chunk_and_step_tick_semantics_for_chunked_step():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(active_level="L2", microsteps_per_global_tick=1, batch_size=1, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=42)
    transport = _CaptureTransport()
    streamer = VizStreamer.attach(session.bus, transport, every_steps=1)

    try:
        session.step(None, 3)
        assert len(transport.frames) == 3
        first_meta = dict(transport.frames[0]["meta"] or {})
        assert int(first_meta.get("chunk_n_ticks", 0)) == 1
        assert int(first_meta.get("requested_n_ticks", 0)) == 3
        assert int(first_meta.get("step_requested_n_ticks", 0)) == 3
        assert int(first_meta.get("step_effective_n_ticks", 0)) == 3
    finally:
        streamer.detach()
        session.close()


def test_viz_streamer_step_emits_commit_and_fabric_runtime_meta():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(active_level="L0", microsteps_per_global_tick=1, commit_stride=1),
    )
    session = DetmSession.create(cfg, seed=44)
    transport = _CaptureTransport()
    streamer = VizStreamer.attach(session.bus, transport, every_steps=1)

    try:
        session.bus.publish("commit_packet", mode="realtime")
        session.bus.publish("commit_packet", mode="audit")
        session.bus.publish(
            "fabric_runtime_snapshot",
            snapshot={
                "enabled": True,
                "commit_count": 2,
                "ack_count": 4,
                "delivery": {"accepted_count": 2, "pending_count": 0, "rejected_count": 0},
                "quorum": {"accepted_count": 2, "pending_count": 0, "rejected_count": 0},
                "replay": {"checks_total": 2, "checks_failed": 0},
            },
        )
        session.step(None, 1)
        assert len(transport.frames) == 1
        meta = dict(transport.frames[0]["meta"] or {})
        assert int(meta.get("commit_packets_total", 0)) == 2
        modes = dict(meta.get("commit_packets_by_mode", {}))
        assert int(modes.get("realtime", 0)) == 1
        assert int(modes.get("audit", 0)) == 1
        fabric = dict(meta.get("fabric", {}))
        assert int(fabric.get("commit_count", 0)) == 2
        assert int(fabric.get("ack_count", 0)) == 4
    finally:
        streamer.detach()
        session.close()


def test_viz_streamer_resolve_active_level_prefers_policy_decision():
    cfg = DETMConfig(level_policy=LevelPolicy(active_level="L0"))
    resolved = VizStreamer._resolve_active_level(
        config=cfg,
        level_policy=LevelPolicy(active_level="L1"),
        policy_decision=PolicyDecision(
            active_level="L3",
            requested_n_ticks=1,
            effective_n_ticks=1,
            batch_size=1,
            commit_stride=1,
            audit_commit_enabled=False,
            audit_commit_stride=10,
            commit_boundary_crossed=True,
            allow_refinement=True,
            observability_profile=ObservabilityProfile(),
        ),
    )
    assert resolved == "L3"

