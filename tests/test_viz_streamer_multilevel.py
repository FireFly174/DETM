from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from detm_app.session import DetmSession
from detm_app.subscribers import VizStreamer
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
        assert dict(frame["meta"] or {}) == {"active_level": "L2"}
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
