"""UI runtime runner (toolkit-agnostic core).

This module contains runtime/session orchestration used by multiple UI frontends.
"""

from __future__ import annotations

from typing import Optional

from detm_app.config.ui_models import UiRunSettings
from detm_app.runtime.bus import EventBus
from detm_app.runtime.coarsening import InvariantCoarsener, parse_invariant_streams
from detm_app.runtime.session import DetmSession
from detm_app.runtime.ui_runtime.influence import resolve_influence_for_settings
from detm_app.runtime.ui_runtime.learning import (
    configure_learning_runtime,
    init_learning_runtime,
    learning_status_compact,
    learning_status_multiline,
    reset_learning_runtime,
    update_learning_snapshot,
)
from detm_app.runtime.ui_runtime.recording import (
    configure_invariant_recording as _configure_invariant_recording_flow,
    configure_recording as _configure_recording_flow,
)
from detm_app.runtime.subscribers import (
    ArtifactWriter,
    CommitJsonlWriter,
    CommitValidationReporter,
    FieldHistoryRecorder,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    OperatorDecisionWriter,
    WatchContractWriter,
    WatchTraceWriter,
    VizStreamer,
)
from detm.runtime.influence import DETMInfluence
from detm_app.transport import VizTransport, open_viz_transport


class DetmUiRunner:
    def __init__(self, settings: UiRunSettings):
        self.settings = settings
        self._bus = EventBus()
        self._session = DetmSession.create(settings.config, settings.seed, bus=self._bus)
        self._last_signature = self._session.digest().vector
        self._running = False
        self._viz_transport: VizTransport | None = None
        self._viz_streamer: VizStreamer | None = None
        self._viz_key: tuple | None = None
        self._trace_writer: JsonlTraceWriter | None = None
        self._watch_trace_writer: WatchTraceWriter | None = None
        self._watch_contract_writer: WatchContractWriter | None = None
        self._operator_decision_writer: OperatorDecisionWriter | None = None
        self._commit_writer: CommitJsonlWriter | None = None
        self._audit_commit_writer: CommitJsonlWriter | None = None
        self._commit_validation_reporter: CommitValidationReporter | None = None
        self._invariant_writer: InvariantTickJsonlWriter | None = None
        self._artifact_writer: ArtifactWriter | None = None
        self._fields_recorder: FieldHistoryRecorder | None = None
        self._coarsener: InvariantCoarsener | None = None
        self._invariant_key: str | None = None
        self._invariant_error: str | None = None
        self._last_influence_key: tuple | None = None
        self._influence_remaining: int = 0
        self._learning_runtime: dict[str, object] = init_learning_runtime(
            window_steps=int(getattr(self.settings, "learning_window_steps", 64))
        )
        self._learning_snapshot: dict[str, object] = {}
        self._learning_unsub_step = self._bus.add_event_listener_unsub("step", self._on_learning_step)

        self._configure_recording()
        self._configure_viz()
        self._configure_invariants()
        self._configure_learning()

    @property
    def state(self):
        return self._session.state

    @property
    def last_observables(self):
        return self._last_signature

    @property
    def learning_snapshot(self) -> dict[str, object]:
        return dict(self._learning_snapshot)

    def runtime_backend_label(self) -> str:
        """Return actual backend/device used by the current state arrays."""
        energy = self._session.state.field_state.energy
        try:
            import torch  # type: ignore
        except ModuleNotFoundError:
            torch = None
        if torch is not None and isinstance(energy, torch.Tensor):
            return f"torch/{str(energy.device)}"
        return "numpy/cpu"

    def learning_status_compact(self, *, max_len: int = 160) -> str:
        return learning_status_compact(
            self._learning_snapshot,
            enabled=bool(getattr(self.settings, "learning_view_enabled", True)),
            max_len=int(max_len),
        )

    def learning_status_multiline(self) -> str:
        return learning_status_multiline(
            self._learning_snapshot,
            enabled=bool(getattr(self.settings, "learning_view_enabled", True)),
        )

    def invariant_status_compact(self) -> str:
        key = str(self.settings.invariant_streams or "").strip()
        if self._invariant_error and key:
            return f"inv=invalid({key})"
        if self._coarsener is None or not key:
            return ""
        return f"inv={key}"

    def close(self) -> None:
        self._running = False
        self._session.close()
        if self._learning_unsub_step is not None:
            self._learning_unsub_step()
            self._learning_unsub_step = None
        self._disable_viz()
        self._disable_recording()
        self._disable_invariants()

    def reset(self) -> None:
        self._session.config = self.settings.config
        self._session.reset(seed=self.settings.seed)
        self._last_signature = self._session.digest().vector
        reset_learning_runtime(
            self._learning_runtime,
            window_steps=int(getattr(self.settings, "learning_window_steps", 64)),
        )
        self._learning_snapshot = {}

    def set_viz_enabled(self, enabled: bool) -> None:
        self.settings.viz_enabled = bool(enabled)
        self._configure_viz()

    def _make_influence(self) -> Optional[DETMInfluence]:
        influence, next_key, remaining = resolve_influence_for_settings(
            self.settings,
            last_key=self._last_influence_key,
            remaining_steps=int(self._influence_remaining),
        )
        self._last_influence_key = next_key
        self._influence_remaining = int(remaining)
        return influence

    def step_once(self) -> None:
        influence = self._make_influence()
        obs = self._session.step(influence, int(self.settings.ticks_per_step))
        self._last_signature = obs.signature.vector

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def _storage_policy(self, artifact: str) -> dict[str, int]:
        level_name = str(self.settings.config.level_policy.active_level or "L0")
        return self.settings.config.resolve_artifact_storage_policy(
            artifact=str(artifact),
            level=level_name,
        )

    def _disable_viz(self) -> None:
        if self._viz_streamer is not None:
            self._viz_streamer.detach()
            self._viz_streamer = None
        if self._viz_transport is not None:
            self._viz_transport.close()
            self._viz_transport = None
        self._viz_key = None

    def _configure_viz(self) -> None:
        transport = str(self.settings.viz_transport).lower().strip()
        if not bool(self.settings.viz_enabled) or transport in {"none", "embedded"}:
            self._disable_viz()
            return

        desired_key = (
            str(self.settings.viz_transport),
            str(self.settings.viz_host),
            int(self.settings.viz_port),
            bool(self.settings.viz_connect),
            bool(self.settings.viz_keep_open),
            int(self.settings.viz_every_steps),
        )
        if self._viz_key is not None and self._viz_key != desired_key:
            self._disable_viz()

        if self._viz_transport is None:
            self._viz_transport = open_viz_transport(
                enabled=True,
                transport=str(self.settings.viz_transport),
                host=str(self.settings.viz_host),
                port=int(self.settings.viz_port),
                connect=bool(self.settings.viz_connect),
                keep_open=bool(self.settings.viz_keep_open),
            )
            self._viz_streamer = VizStreamer.attach(
                self._session.bus,
                self._viz_transport,
                every_steps=int(self.settings.viz_every_steps),
            )
            self._viz_key = desired_key
            self._viz_streamer.on_reset(state=self._session.state)

    def _disable_recording(self) -> None:
        if self._trace_writer is not None:
            self._trace_writer.on_close()
            self._trace_writer = None
        if self._watch_trace_writer is not None:
            self._watch_trace_writer.on_close()
            self._watch_trace_writer = None
        if self._watch_contract_writer is not None:
            self._watch_contract_writer.on_close()
            self._watch_contract_writer = None
        if self._operator_decision_writer is not None:
            self._operator_decision_writer.on_close()
            self._operator_decision_writer = None
        if self._commit_writer is not None:
            self._commit_writer.on_close()
            self._commit_writer = None
        if self._audit_commit_writer is not None:
            self._audit_commit_writer.on_close()
            self._audit_commit_writer = None
        if self._commit_validation_reporter is not None:
            self._commit_validation_reporter.detach()
            self._commit_validation_reporter = None
        if self._invariant_writer is not None:
            self._invariant_writer.on_close()
            self._invariant_writer = None
        if self._artifact_writer is not None:
            self._artifact_writer.detach()
            self._artifact_writer = None
        if self._fields_recorder is not None:
            self._fields_recorder.detach()
            self._fields_recorder = None

    def _disable_invariants(self) -> None:
        if self._coarsener is not None:
            self._coarsener.detach()
            self._coarsener = None
        if self._invariant_writer is not None:
            self._invariant_writer.on_close()
            self._invariant_writer = None
        self._invariant_key = None

    def _configure_invariants(self) -> None:
        key = (self.settings.invariant_streams or "").strip()
        if not key:
            self._disable_invariants()
            self._invariant_error = None
            return
        if self._invariant_key == key and self._coarsener is not None:
            self._invariant_error = None
            return
        self._disable_invariants()
        try:
            self._coarsener = InvariantCoarsener.attach(self._session.bus, parse_invariant_streams(key))
        except ValueError as exc:
            self._disable_invariants()
            self._invariant_error = str(exc)
            return
        self._invariant_key = key
        self._invariant_error = None
        self._configure_invariant_recording()

    def _configure_invariant_recording(self) -> None:
        _configure_invariant_recording_flow(self)

    def _configure_recording(self) -> None:
        _configure_recording_flow(self)

    def _configure_learning(self) -> None:
        configure_learning_runtime(
            self._learning_runtime,
            window_steps=int(getattr(self.settings, "learning_window_steps", 64)),
        )

    def _on_learning_step(
        self,
        *,
        state,
        n_ticks: int,
        requested_n_ticks: int = 0,
        observables,
        level_policy=None,
        policy_decision=None,
        **_rest,
    ) -> None:
        self._configure_learning()
        self._learning_snapshot = update_learning_snapshot(
            self._learning_runtime,
            state=state,
            n_ticks=int(n_ticks),
            requested_n_ticks=int(requested_n_ticks),
            observables=observables,
            level_policy=level_policy,
            policy_decision=policy_decision,
        )

DetmTkRunner = DetmUiRunner

__all__ = ['DetmUiRunner', 'DetmTkRunner', 'UiRunSettings']


