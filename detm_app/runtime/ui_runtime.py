"""UI runtime runner (toolkit-agnostic core).

This module contains runtime/session orchestration used by multiple UI frontends.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from detm_app.config.ui_models import UiRunSettings
from detm_app.runtime.bus import EventBus
from detm_app.runtime.coarsening import InvariantCoarsener, parse_invariant_streams
from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import (
    ArtifactWriter,
    CommitJsonlWriter,
    CommitValidationReporter,
    FieldHistoryRecorder,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    WatchContractWriter,
    WatchTraceWriter,
    VizStreamer,
)
from detm.runtime.influence import DETMInfluence
from detm.runtime.symbols import make_symbol
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
        self._commit_writer: CommitJsonlWriter | None = None
        self._audit_commit_writer: CommitJsonlWriter | None = None
        self._commit_validation_reporter: CommitValidationReporter | None = None
        self._invariant_writer: InvariantTickJsonlWriter | None = None
        self._artifact_writer: ArtifactWriter | None = None
        self._fields_recorder: FieldHistoryRecorder | None = None
        self._coarsener: InvariantCoarsener | None = None
        self._invariant_key: str | None = None
        self._last_influence_key: tuple | None = None
        self._influence_remaining: int = 0

        self._configure_recording()
        self._configure_viz()
        self._configure_invariants()

    @property
    def state(self):
        return self._session.state

    @property
    def last_observables(self):
        return self._last_signature

    def close(self) -> None:
        self._running = False
        self._session.close()
        self._disable_viz()
        self._disable_recording()
        self._disable_invariants()

    def reset(self) -> None:
        self._session.config = self.settings.config
        self._session.reset(seed=self.settings.seed)
        self._last_signature = self._session.digest().vector

    def set_viz_enabled(self, enabled: bool) -> None:
        self.settings.viz_enabled = bool(enabled)
        self._configure_viz()

    def _make_influence(self) -> Optional[DETMInfluence]:
        mode = str(getattr(self.settings, "influence_mode", "symbol") or "symbol").strip().lower()
        duration_steps = int(getattr(self.settings, "influence_duration_steps", 0) or 0)
        amplitude = float(getattr(self.settings, "amplitude", 0.0))

        if mode in {"none", "(none)", ""}:
            return None

        if mode == "symbol":
            symbol_id = (self.settings.symbol_id or "").strip()
            if not symbol_id or symbol_id == "(none)":
                return None
            key = ("symbol", symbol_id, amplitude)
            influence = make_symbol(symbol_id, amplitude=amplitude)
        elif mode == "joystick_field":
            dx = float(getattr(self.settings, "joy_dx", 0.0))
            dy = float(getattr(self.settings, "joy_dy", 0.0))
            key = ("joystick_field", amplitude, dx, dy)
            influence = DETMInfluence(
                symbol_id="joystick_field",
                amplitude=amplitude,
                external_features={"dx": dx, "dy": dy},
            )
        elif mode == "joystick_patch":
            w, h = int(self.settings.config.width), int(self.settings.config.height)
            cx = int(getattr(self.settings, "patch_cx", w // 2)) % max(1, w)
            cy = int(getattr(self.settings, "patch_cy", h // 2)) % max(1, h)
            radius = int(
                getattr(
                    self.settings,
                    "patch_radius",
                    max(1, max(self.settings.config.width, self.settings.config.height) // 8),
                )
            )
            key = ("joystick_patch", amplitude, cx, cy, radius)
            influence = DETMInfluence(symbol_id="joystick_patch", amplitude=amplitude, region=(cx, cy, radius))
        elif mode == "source_sink":
            sx = int(getattr(self.settings, "source_x", 0))
            sy = int(getattr(self.settings, "source_y", 0))
            tx = int(getattr(self.settings, "sink_x", 0))
            ty = int(getattr(self.settings, "sink_y", 0))
            sv = float(getattr(self.settings, "source_value", 1.0))
            tv = float(getattr(self.settings, "sink_value", 0.0))
            key = ("source_sink", amplitude, sx, sy, tx, ty, sv, tv)
            influence = DETMInfluence(
                symbol_id="source_sink",
                amplitude=amplitude,
                external_features={
                    "src_x": float(sx),
                    "src_y": float(sy),
                    "dst_x": float(tx),
                    "dst_y": float(ty),
                    "src_value": float(sv),
                    "dst_value": float(tv),
                },
            )
        else:
            # Unknown mode: fall back to no influence.
            return None

        if duration_steps > 0:
            if self._last_influence_key != key:
                self._last_influence_key = key
                self._influence_remaining = int(duration_steps)
            if self._influence_remaining <= 0:
                return None
            self._influence_remaining -= 1
        else:
            self._last_influence_key = key
            self._influence_remaining = 0

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
            return
        if self._invariant_key == key and self._coarsener is not None:
            return
        self._disable_invariants()
        self._coarsener = InvariantCoarsener.attach(self._session.bus, parse_invariant_streams(key))
        self._invariant_key = key
        self._configure_invariant_recording()

    def _configure_invariant_recording(self) -> None:
        record_dir = self.settings.record_dir
        invariant_key = (self.settings.invariant_streams or "").strip()
        if record_dir is None or not invariant_key:
            if self._invariant_writer is not None:
                self._invariant_writer.on_close()
                self._invariant_writer = None
            return

        record_dir = Path(record_dir)
        desired_path = record_dir / "invariants.jsonl"
        inv_policy = self._storage_policy("invariants")
        if self._invariant_writer is None:
            self._invariant_writer = InvariantTickJsonlWriter.attach(
                self._session.bus,
                desired_path,
                retention_window=int(inv_policy.get("retention_window", 0)),
                compaction_budget=int(inv_policy.get("compaction_budget", 0)),
            )
            return
        if self._invariant_writer.path.resolve() != desired_path.resolve():
            self._invariant_writer.on_close()
            self._invariant_writer = InvariantTickJsonlWriter.attach(
                self._session.bus,
                desired_path,
                retention_window=int(inv_policy.get("retention_window", 0)),
                compaction_budget=int(inv_policy.get("compaction_budget", 0)),
            )

    def _configure_recording(self) -> None:
        record_dir = self.settings.record_dir
        if record_dir is None:
            self._disable_recording()
            return

        record_dir = Path(record_dir)
        trace_policy = self._storage_policy("trace")
        watch_policy = self._storage_policy("watch_trace")
        watch_contract_policy = self._storage_policy("watch_contract")
        outerfields_policy = self._storage_policy("outerfields")
        commits_policy = self._storage_policy("commits")
        commits_audit_policy = self._storage_policy("commits_audit")
        commit_validation_policy = self._storage_policy("commit_validation")
        if self._trace_writer is None:
            self._trace_writer = JsonlTraceWriter.attach(
                self._session.bus,
                record_dir / "trace.jsonl",
                retention_window=int(trace_policy.get("retention_window", 0)),
                compaction_budget=int(trace_policy.get("compaction_budget", 0)),
            )
            if bool(self.settings.config.watch_trace_enabled):
                self._watch_trace_writer = WatchTraceWriter.attach(
                    self._session.bus,
                    record_dir / "watch_trace.jsonl",
                    retention_window=int(watch_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_policy.get("compaction_budget", 0)),
                )
                self._watch_contract_writer = WatchContractWriter.attach(
                    self._session.bus,
                    record_dir / "watch_contract.jsonl",
                    outerfields_dir=record_dir / "outerfields",
                    level_src=str(self.settings.config.level_policy.active_level or "L0"),
                    base_level="L0",
                    retention_window=int(watch_contract_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
                    outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
                    outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
                )
            self._commit_writer = CommitJsonlWriter.attach(
                self._session.bus,
                record_dir / "commits.jsonl",
                node_id=f"ui_seed_{int(self.settings.seed):04d}",
                mode="realtime",
                retention_window=int(commits_policy.get("retention_window", 0)),
                compaction_budget=int(commits_policy.get("compaction_budget", 0)),
            )
            if bool(self.settings.config.level_policy.audit_commit_enabled):
                self._audit_commit_writer = CommitJsonlWriter.attach(
                    self._session.bus,
                    record_dir / "commits_audit.jsonl",
                    node_id=f"ui_seed_{int(self.settings.seed):04d}",
                    commit_type="proof",
                    mode="audit",
                    retention_window=int(commits_audit_policy.get("retention_window", 0)),
                    compaction_budget=int(commits_audit_policy.get("compaction_budget", 0)),
                )
            self._commit_validation_reporter = CommitValidationReporter.attach(
                self._session.bus,
                record_dir,
                retention_window=int(commit_validation_policy.get("retention_window", 0)),
                compaction_budget=int(commit_validation_policy.get("compaction_budget", 0)),
            )
            self._configure_invariant_recording()
            self._artifact_writer = ArtifactWriter.attach(self._session.bus, record_dir)
            if bool(self.settings.record_fields):
                self._fields_recorder = FieldHistoryRecorder.attach(self._session.bus, record_dir / "fields_hist.npz")
            return

        if self._trace_writer.path.resolve() != (record_dir / "trace.jsonl").resolve():
            self._disable_recording()
            self._trace_writer = JsonlTraceWriter.attach(
                self._session.bus,
                record_dir / "trace.jsonl",
                retention_window=int(trace_policy.get("retention_window", 0)),
                compaction_budget=int(trace_policy.get("compaction_budget", 0)),
            )
            if bool(self.settings.config.watch_trace_enabled):
                self._watch_trace_writer = WatchTraceWriter.attach(
                    self._session.bus,
                    record_dir / "watch_trace.jsonl",
                    retention_window=int(watch_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_policy.get("compaction_budget", 0)),
                )
                self._watch_contract_writer = WatchContractWriter.attach(
                    self._session.bus,
                    record_dir / "watch_contract.jsonl",
                    outerfields_dir=record_dir / "outerfields",
                    level_src=str(self.settings.config.level_policy.active_level or "L0"),
                    base_level="L0",
                    retention_window=int(watch_contract_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
                    outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
                    outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
                )
            self._commit_writer = CommitJsonlWriter.attach(
                self._session.bus,
                record_dir / "commits.jsonl",
                node_id=f"ui_seed_{int(self.settings.seed):04d}",
                mode="realtime",
                retention_window=int(commits_policy.get("retention_window", 0)),
                compaction_budget=int(commits_policy.get("compaction_budget", 0)),
            )
            if bool(self.settings.config.level_policy.audit_commit_enabled):
                self._audit_commit_writer = CommitJsonlWriter.attach(
                    self._session.bus,
                    record_dir / "commits_audit.jsonl",
                    node_id=f"ui_seed_{int(self.settings.seed):04d}",
                    commit_type="proof",
                    mode="audit",
                    retention_window=int(commits_audit_policy.get("retention_window", 0)),
                    compaction_budget=int(commits_audit_policy.get("compaction_budget", 0)),
                )
            self._commit_validation_reporter = CommitValidationReporter.attach(
                self._session.bus,
                record_dir,
                retention_window=int(commit_validation_policy.get("retention_window", 0)),
                compaction_budget=int(commit_validation_policy.get("compaction_budget", 0)),
            )
            self._configure_invariant_recording()
            self._artifact_writer = ArtifactWriter.attach(self._session.bus, record_dir)
            if bool(self.settings.record_fields):
                self._fields_recorder = FieldHistoryRecorder.attach(self._session.bus, record_dir / "fields_hist.npz")
        else:
            watch_enabled = bool(self.settings.config.watch_trace_enabled)
            if watch_enabled and self._watch_trace_writer is None:
                self._watch_trace_writer = WatchTraceWriter.attach(
                    self._session.bus,
                    record_dir / "watch_trace.jsonl",
                    retention_window=int(watch_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_policy.get("compaction_budget", 0)),
                )
            if watch_enabled and self._watch_contract_writer is None:
                self._watch_contract_writer = WatchContractWriter.attach(
                    self._session.bus,
                    record_dir / "watch_contract.jsonl",
                    outerfields_dir=record_dir / "outerfields",
                    level_src=str(self.settings.config.level_policy.active_level or "L0"),
                    base_level="L0",
                    retention_window=int(watch_contract_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
                    outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
                    outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
                )
            if (not watch_enabled) and self._watch_trace_writer is not None:
                self._watch_trace_writer.on_close()
                self._watch_trace_writer = None
            if (not watch_enabled) and self._watch_contract_writer is not None:
                self._watch_contract_writer.on_close()
                self._watch_contract_writer = None
            # Toggle field recorder without changing directory
            if bool(self.settings.record_fields) and self._fields_recorder is None:
                self._fields_recorder = FieldHistoryRecorder.attach(self._session.bus, record_dir / "fields_hist.npz")
            if (not bool(self.settings.record_fields)) and self._fields_recorder is not None:
                self._fields_recorder.detach()
                self._fields_recorder = None
            self._configure_invariant_recording()

DetmTkRunner = DetmUiRunner

__all__ = ['DetmUiRunner', 'DetmTkRunner', 'UiRunSettings']


