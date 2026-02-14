from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Sequence

import numpy as np

from detm.runtime import api
from detm.runtime.commit_packet import CommitPacket
from detm.runtime.config import DETMConfig
from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FabricAckIngressService
from detm.runtime.fabric import FabricArtifactResolver
from detm.runtime.fabric import FileFabricArtifactStore
from detm.runtime.fabric import FabricCommitDeliveryService
from detm.runtime.fabric import FabricCommitIngressService
from detm.runtime.fabric import JsonlFabricEnvelopeOutbox
from detm.runtime.fabric import (
    InMemoryDeliveryReceiptCoordinator,
)
from detm.runtime.fabric import DeliveryTrackingCoordinator
from detm.runtime.fabric import (
    FabricEpochCoordinator,
)
from detm.runtime.fabric import TransportEpochConsensusCoordinator
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import FabricHandshakeService
from detm.runtime.fabric import normalize_fabric_handshake_recorder_attach_kwargs
from detm.runtime.fabric import InMemoryQuorumCoordinator
from detm.runtime.fabric import FabricQuorumReportBuilder
from detm.runtime.fabric import FabricQuorumRuntimeService
from detm.runtime.fabric import FabricRuntimeReportWriter
from detm.runtime.fabric import FabricHandshakeRuntimeBundle
from detm.runtime.fabric import compose_fabric_handshake_runtime
from detm.runtime.fabric import mode_channels, start_runtime_bundle
from detm.runtime.fabric import FabricTransportAdapter
from detm.runtime.fabric import LocalFabricValidator
from detm.runtime.fabric import ValidatorRegistry
from detm.runtime.fabric import validate_commit_paths
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.outerfields import compute_outerfields_v1
from detm.runtime.schemas import DETM_COMMIT_PACKET_V1
from detm.runtime.state import DETMState
from detm.runtime.watch_contract import OuterFieldsRef, WatchContractPacket
from detm_app.transport import VizTransport
from detm.metrics.base import MetricContext, MetricPlugin
from detm.metrics.builtin import default_metric_plugins

from detm_app.runtime.subscribers.common import _effective_storage_limit, _snapshot_digest, _tail_limit, _to_numpy, _trace_ref_for_tick

@dataclass
class TraceRecorder:
    """Collects step history and writes `history.jsonl` on close/finish."""

    out_dir: Path
    history: List[Dict[str, Any]]
    retention_window: int = 0
    compaction_budget: int = 0

    @classmethod
    def attach(
        cls,
        bus,
        out_dir: Path,
        *,
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "TraceRecorder":
        rec = cls(
            out_dir=out_dir,
            history=[],
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        bus.add_event_listener("step", rec.on_step)
        bus.add_event_listener("close", rec.on_close)
        return rec

    def on_step(
        self,
        *,
        observables: api.Observables,
        **_rest: Any,
    ) -> None:
        self.history.append(
            {
                "signature": observables.signature.as_dict(),
                "events": list(observables.events),
                "cost": dict(observables.cost),
                "quality": dict(observables.quality),
            }
        )

    def on_close(self, **_rest: Any) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / "history.jsonl"
        rows = list(self.history)
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            rows = rows[-limit:]
        path.write_text("\n".join(json.dumps(entry) for entry in rows), encoding="utf-8")

@dataclass
class ArtifactWriter:
    """Writes `state.msgpack`, `digest.json`, and `config.json` on close."""

    out_dir: Path
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(cls, bus, out_dir: Path) -> "ArtifactWriter":
        writer = cls(out_dir=out_dir)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def on_close(
        self,
        *,
        config: DETMConfig,
        state: DETMState,
        **_rest: Any,
    ) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "config.json").write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
        (self.out_dir / "state.msgpack").write_bytes(api.serialize(state))
        digest = api.digest(state)
        (self.out_dir / "digest.json").write_text(json.dumps(digest.as_dict(), indent=2), encoding="utf-8")
        self.detach()

    def detach(self) -> None:
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None

@dataclass
class FieldHistoryRecorder:
    """Record field histories into `fields_hist.npz` (legacy-friendly).

    Stores:
      t: [T] step_count values
      E_hist: [T,H,W]
      S_hist: [T,H,W]
      tau_hist: [T,H,W]
    Also stores a simple gradient-based vector field for quiver-like analysis:
      Jx_hist, Jy_hist: central differences of E (approximate)
    """

    out_path: Path
    every_steps: int = 1
    dtype: str = "float32"
    _t: List[int] = None  # type: ignore[assignment]
    _E: List[np.ndarray] = None  # type: ignore[assignment]
    _S: List[np.ndarray] = None  # type: ignore[assignment]
    _tau: List[np.ndarray] = None  # type: ignore[assignment]
    _Jx: List[np.ndarray] = None  # type: ignore[assignment]
    _Jy: List[np.ndarray] = None  # type: ignore[assignment]
    _last_step: int = -1
    _unsub_reset: Callable[[], None] | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        out_path: Path,
        *,
        every_steps: int = 1,
        dtype: str = "float32",
    ) -> "FieldHistoryRecorder":
        rec = cls(out_path=out_path, every_steps=max(1, int(every_steps)), dtype=str(dtype))
        rec._t, rec._E, rec._S, rec._tau, rec._Jx, rec._Jy = [], [], [], [], [], []
        rec._unsub_reset = bus.add_event_listener_unsub("reset", rec.on_reset)
        rec._unsub_step = bus.add_event_listener_unsub("step", rec.on_step)
        rec._unsub_close = bus.add_event_listener_unsub("close", rec.on_close)
        return rec

    def _append_state(self, state: DETMState) -> None:
        lattice = state.lattice
        H, W = lattice.height, lattice.width

        E = _to_numpy(state.field_state.energy).astype(np.float32, copy=False).reshape(H, W)
        S = _to_numpy(state.field_state.entropy).astype(np.float32, copy=False).reshape(H, W)
        tau = _to_numpy(state.field_state.internal_time).astype(np.float32, copy=False).reshape(H, W)

        # Approximate vector field from E gradient (for quiver/analysis)
        Jx = 0.5 * (np.roll(E, -1, axis=1) - np.roll(E, 1, axis=1))
        Jy = 0.5 * (np.roll(E, -1, axis=0) - np.roll(E, 1, axis=0))

        self._t.append(int(state.step_count))
        self._E.append(E)
        self._S.append(S)
        self._tau.append(tau)
        self._Jx.append(Jx)
        self._Jy.append(Jy)

    def on_reset(self, *, state: DETMState, **_rest: Any) -> None:
        self._last_step = -1
        self._append_state(state)
        self._last_step = int(state.step_count)

    def on_step(self, *, state: DETMState, **_rest: Any) -> None:
        step = int(state.step_count)
        if self._last_step >= 0 and (step - self._last_step) < self.every_steps:
            return
        self._append_state(state)
        self._last_step = step

    def on_close(self, **_rest: Any) -> None:
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        dtype = np.float16 if self.dtype.lower() == "float16" else np.float32

        t = np.asarray(self._t, dtype=float)
        E_hist = np.asarray(self._E, dtype=dtype)
        S_hist = np.asarray(self._S, dtype=dtype)
        tau_hist = np.asarray(self._tau, dtype=dtype)
        Jx_hist = np.asarray(self._Jx, dtype=dtype)
        Jy_hist = np.asarray(self._Jy, dtype=dtype)

        np.savez_compressed(
            self.out_path,
            t=t,
            E_hist=E_hist,
            S_hist=S_hist,
            tau_hist=tau_hist,
            Jx_hist=Jx_hist,
            Jy_hist=Jy_hist,
        )
        self.detach()

    def detach(self) -> None:
        if self._unsub_reset is not None:
            self._unsub_reset()
            self._unsub_reset = None
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None

@dataclass
class JsonlTraceWriter:
    """Writes canonical `System Trace` (`trace.jsonl`) from `step` events."""

    path: Path
    metric_plugins: Sequence[MetricPlugin]
    retention_window: int = 0
    compaction_budget: int = 0
    _fh: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        metric_plugins: Sequence[MetricPlugin] | None = None,
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "JsonlTraceWriter":
        writer = cls(
            path=path,
            metric_plugins=list(metric_plugins or default_metric_plugins()),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        writer._unsub_step = bus.add_event_listener_unsub("step", writer.on_step)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def on_step(
        self,
        *,
        state: DETMState,
        influence: DETMInfluence | None,
        n_ticks: int,
        requested_n_ticks: int = 0,
        step_requested_n_ticks: int = 0,
        step_effective_n_ticks: int = 0,
        observables: api.Observables,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
        get_state_blob: Any | None = None,
        **_rest: Any,
    ) -> None:
        if policy_decision is None:
            inferred_policy = level_policy if level_policy is not None else LevelPolicy()
            policy_decision = inferred_policy.decide(
                step_count=max(0, int(state.step_count) - int(n_ticks)),
                requested_n_ticks=int(requested_n_ticks or n_ticks),
            )
        if not bool(policy_decision.commit_boundary_crossed):
            return

        self._ensure()
        detail_mode = policy_decision.observability_profile.normalized_detail_mode()
        filtered_events = [
            event
            for event in list(observables.events)
            if policy_decision.observability_profile.allows_event_type(str(event.get("type", "")))
        ]

        metrics: Dict[str, Any] = {}
        if detail_mode != "minimal":
            filtered_observables = api.Observables(
                signature=observables.signature,
                field_summaries=observables.field_summaries,
                events=filtered_events,
                cost=observables.cost,
                quality=observables.quality,
            )
            ctx = MetricContext(
                state=state,
                observables=filtered_observables,
                influence=influence,
                n_ticks=int(n_ticks),
                get_state_blob=get_state_blob,
            )
            for plugin in self.metric_plugins:
                try:
                    metrics[str(getattr(plugin, "name", plugin.__class__.__name__))] = plugin.compute(ctx)
                except Exception as exc:
                    metrics[str(getattr(plugin, "name", plugin.__class__.__name__))] = {"error": str(exc)}

        entry = {
            "type": "step",
            "tick": int(state.step_count),
            "trace_ref": _trace_ref_for_tick(int(state.step_count)),
            # Backward-compatible alias: historically n_ticks is publish chunk size.
            "n_ticks": int(n_ticks),
            "chunk_n_ticks": int(n_ticks),
            "requested_n_ticks": int(requested_n_ticks or n_ticks),
            "step_requested_n_ticks": int(step_requested_n_ticks or requested_n_ticks or n_ticks),
            "step_effective_n_ticks": int(step_effective_n_ticks or n_ticks),
            "influence": influence.__dict__ if (influence is not None and detail_mode == "debug") else None,
            "signature": observables.signature.as_dict(),
            "field_summaries": None
            if detail_mode == "minimal"
            else {
                "energy": observables.field_summaries.energy,
                "entropy": observables.field_summaries.entropy,
                "internal_time": observables.field_summaries.internal_time,
            },
            "cost": dict(observables.cost),
            "quality": dict(observables.quality),
            "events": filtered_events if detail_mode != "minimal" else [],
            "event_types": [str(event.get("type", "")) for event in filtered_events],
            "event_count": len(filtered_events),
            "metrics": metrics,
            "detail_mode": detail_mode,
            "policy": policy_decision.to_dict(),
        }
        assert self._fh is not None
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)

    def on_close(self, **_rest: Any) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)
        self.detach()

    def detach(self) -> None:
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None

SystemTraceWriter = JsonlTraceWriter

