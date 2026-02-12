"""Reusable subscribers for the EventBus."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Sequence

import numpy as np

from detm.runtime import api
from detm.runtime.commit_packet import CommitPacket
from detm.runtime.config import DETMConfig
from detm.runtime.fabric_ack import ProofAck, TrustAck
from detm.runtime.fabric_ack_ingress import FabricAckIngressService
from detm.runtime.fabric_artifact_resolver import FabricArtifactResolver
from detm.runtime.fabric_artifact_store import FileFabricArtifactStore
from detm.runtime.fabric_commit_delivery import FabricCommitDeliveryService
from detm.runtime.fabric_commit_ingress import FabricCommitIngressService
from detm.runtime.fabric_delivery import JsonlFabricEnvelopeOutbox
from detm.runtime.fabric_delivery_receipts import (
    InMemoryDeliveryReceiptCoordinator,
)
from detm.runtime.fabric_delivery_tracking import DeliveryTrackingCoordinator
from detm.runtime.fabric_epoch import (
    FabricEpochCoordinator,
)
from detm.runtime.fabric_epoch_consensus import TransportEpochConsensusCoordinator
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_handshake import FabricHandshakeService
from detm.runtime.fabric_handshake_recorder_config import normalize_fabric_handshake_recorder_attach_kwargs
from detm.runtime.fabric_quorum import InMemoryQuorumCoordinator
from detm.runtime.fabric_quorum_report import FabricQuorumReportBuilder
from detm.runtime.fabric_quorum_runtime import FabricQuorumRuntimeService
from detm.runtime.fabric_report_writer import FabricRuntimeReportWriter
from detm.runtime.fabric_runtime_bundle import FabricHandshakeRuntimeBundle
from detm.runtime.fabric_runtime_composer import compose_fabric_handshake_runtime
from detm.runtime.fabric_runtime_helpers import mode_channels, start_runtime_bundle
from detm.runtime.fabric_transport import FabricTransportAdapter
from detm.runtime.fabric_validator import LocalFabricValidator
from detm.runtime.fabric_validator_registry import ValidatorRegistry
from detm.runtime.fabric_validation import validate_commit_paths
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.outerfields import compute_outerfields_v1
from detm.runtime.schemas import DETM_COMMIT_PACKET_V1
from detm.runtime.state import DETMState
from detm.runtime.watch_contract import OuterFieldsRef, WatchContractPacket
from detm.viz.transport import VizTransport
from detm.metrics.base import MetricContext, MetricPlugin
from detm.metrics.builtin import default_metric_plugins


def _trace_ref_for_tick(tick: int) -> str:
    return f"trace://L0/{int(tick)}"


def _snapshot_digest(get_state_blob: Any | None) -> Dict[str, Any]:
    if not callable(get_state_blob):
        return {}
    blob = get_state_blob()
    if not isinstance(blob, (bytes, bytearray)):
        return {}
    return {
        "snapshot_sha256": hashlib.sha256(bytes(blob)).hexdigest(),
        "snapshot_bytes": int(len(blob)),
    }


def _tail_limit(path: Path, *, max_entries: int) -> None:
    limit = max(0, int(max_entries))
    if limit <= 0 or not path.exists():
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) <= limit:
        return
    path.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")


def _effective_storage_limit(*, retention_window: int, compaction_budget: int) -> int:
    retention = max(0, int(retention_window))
    budget = max(0, int(compaction_budget))
    if retention > 0 and budget > 0:
        return min(retention, budget)
    return max(retention, budget)


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


def _to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


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
            "n_ticks": int(n_ticks),
            "requested_n_ticks": int(requested_n_ticks or n_ticks),
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


@dataclass
class WatchTraceWriter:
    """Writes projection `Watch Trace` (`watch_trace.jsonl`) from `step` events."""

    path: Path
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
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "WatchTraceWriter":
        writer = cls(
            path=path,
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
        n_ticks: int,
        requested_n_ticks: int = 0,
        observables: api.Observables,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
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

        tick = int(state.step_count)
        trace_ref = _trace_ref_for_tick(tick)
        filtered_events = [
            event
            for event in list(observables.events)
            if policy_decision.observability_profile.allows_event_type(str(event.get("type", "")))
        ]
        event_types = [str(event.get("type", "")) for event in filtered_events]
        refinement_count = int(sum(1 for event in filtered_events if str(event.get("type", "")) == "refinement"))
        influence_count = int(sum(1 for event in filtered_events if str(event.get("type", "")) == "influence"))
        attractor_count = int(sum(1 for event in filtered_events if str(event.get("type", "")) == "attractor"))

        entry = {
            "type": "watch_step",
            "tick": tick,
            "trace_ref": trace_ref,
            "event_types": event_types,
            "event_count": int(len(event_types)),
            "watchpoints": {
                "refinement_count": refinement_count,
                "influence_count": influence_count,
                "attractor_count": attractor_count,
                "cpu_time_ms": float(observables.cost.get("cpu_time_ms", 0.0)),
                "step_ops_estimate": float(observables.cost.get("step_ops_estimate", 0.0)),
                "oscillation_score": float(observables.quality.get("oscillation_score", 0.0)),
                "runtime_adaptive_window_active": bool(policy_decision.runtime_adaptive_window_active),
                "runtime_adaptive_signal_triggered": bool(policy_decision.runtime_adaptive_signal_triggered),
                "runtime_adaptive_profile": str(policy_decision.runtime_adaptive_profile),
                "runtime_adaptive_signal_hits": {
                    str(k): bool(v) for k, v in dict(policy_decision.runtime_adaptive_signal_hits).items()
                },
            },
            "policy": {
                "active_level": str(policy_decision.active_level),
                "detail_mode": policy_decision.observability_profile.normalized_detail_mode(),
                "commit_stride": int(policy_decision.commit_stride),
                "runtime_adaptive_window_active": bool(policy_decision.runtime_adaptive_window_active),
                "runtime_adaptive_profile": str(policy_decision.runtime_adaptive_profile),
                "runtime_adaptive_signal_triggered": bool(policy_decision.runtime_adaptive_signal_triggered),
            },
        }

        self._ensure()
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


@dataclass
class WatchContractWriter:
    """Writes `watch_contract.jsonl` + `outerfields/*.npz` projection artifacts."""

    path: Path
    outerfields_dir: Path
    level_src: str = "L0"
    base_level: str = "L0"
    retention_window: int = 0
    compaction_budget: int = 0
    outerfields_retention_window: int | None = None
    outerfields_compaction_budget: int | None = None
    _fh: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        outerfields_dir: Path | None = None,
        level_src: str = "L0",
        base_level: str = "L0",
        retention_window: int = 0,
        compaction_budget: int = 0,
        outerfields_retention_window: int | None = None,
        outerfields_compaction_budget: int | None = None,
    ) -> "WatchContractWriter":
        writer = cls(
            path=path,
            outerfields_dir=(
                Path(outerfields_dir)
                if outerfields_dir is not None
                else (Path(path).parent / "outerfields")
            ),
            level_src=str(level_src),
            base_level=str(base_level),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
            outerfields_retention_window=None
            if outerfields_retention_window is None
            else max(0, int(outerfields_retention_window)),
            outerfields_compaction_budget=None
            if outerfields_compaction_budget is None
            else max(0, int(outerfields_compaction_budget)),
        )
        writer._unsub_step = bus.add_event_listener_unsub("step", writer.on_step)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.outerfields_dir.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def _save_outerfields(self, *, tick: int, outerfields: Any) -> str:
        artifact_path = self.outerfields_dir / f"outerfields_{int(tick):09d}.npz"
        meta_json = json.dumps(dict(getattr(outerfields, "meta", {}) or {}), ensure_ascii=False)
        np.savez_compressed(
            artifact_path,
            dir_x=_to_numpy(outerfields.dir_x).astype(np.float32, copy=False),
            dir_y=_to_numpy(outerfields.dir_y).astype(np.float32, copy=False),
            strength=_to_numpy(outerfields.strength).astype(np.float32, copy=False),
            stability=_to_numpy(outerfields.stability).astype(np.float32, copy=False),
            instability=_to_numpy(outerfields.instability).astype(np.float32, copy=False),
            boundary_activity=_to_numpy(outerfields.boundary_activity).astype(np.float32, copy=False),
            capacity_violation_density=_to_numpy(outerfields.capacity_violation_density).astype(
                np.float32,
                copy=False,
            ),
            meta_json=np.asarray([meta_json]),
        )
        try:
            rel = artifact_path.relative_to(self.path.parent)
            return rel.as_posix()
        except Exception:
            return str(artifact_path)

    def _prune_outerfields(self, *, max_entries: int) -> None:
        limit = max(0, int(max_entries))
        if limit <= 0 or not self.outerfields_dir.exists():
            return
        rows = sorted(self.outerfields_dir.glob("outerfields_*.npz"), key=lambda p: p.name)
        excess = len(rows) - limit
        if excess <= 0:
            return
        for row in rows[:excess]:
            try:
                row.unlink(missing_ok=True)
            except Exception:
                continue

    def _apply_storage_limit(self) -> None:
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)
        outer_limit = _effective_storage_limit(
            retention_window=(
                int(self.retention_window)
                if self.outerfields_retention_window is None
                else int(self.outerfields_retention_window)
            ),
            compaction_budget=(
                int(self.compaction_budget)
                if self.outerfields_compaction_budget is None
                else int(self.outerfields_compaction_budget)
            ),
        )
        if outer_limit > 0:
            self._prune_outerfields(max_entries=outer_limit)

    def on_step(
        self,
        *,
        state: DETMState,
        n_ticks: int,
        requested_n_ticks: int = 0,
        observables: api.Observables,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
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

        tick = int(state.step_count)
        trace_ref = _trace_ref_for_tick(tick)
        filtered_events = [
            event
            for event in list(observables.events)
            if policy_decision.observability_profile.allows_event_type(str(event.get("type", "")))
        ]
        event_types = [str(event.get("type", "")) for event in filtered_events]

        outerfields = compute_outerfields_v1(
            energy=state.field_state.energy,
            entropy=state.field_state.entropy,
            internal_time=state.field_state.internal_time,
        )

        self._ensure()
        uri = self._save_outerfields(tick=tick, outerfields=outerfields)
        outerfields_ref = OuterFieldsRef(
            kind="outerfields",
            level_src=str(self.level_src),
            base_level=str(self.base_level),
            tick=tick,
            window_ticks=max(1, int(n_ticks)),
            stride_ticks=max(1, int(policy_decision.commit_stride)),
            uri=str(uri),
            schema=str((outerfields.meta or {}).get("schema", "OUTERFIELDS_V1")),
        )
        watchpoints = {
            "refinement_count": int(
                sum(1 for event in filtered_events if str(event.get("type", "")) == "refinement")
            ),
            "influence_count": int(
                sum(1 for event in filtered_events if str(event.get("type", "")) == "influence")
            ),
            "attractor_count": int(
                sum(1 for event in filtered_events if str(event.get("type", "")) == "attractor")
            ),
            "runtime_adaptive_window_active": bool(policy_decision.runtime_adaptive_window_active),
            "runtime_adaptive_signal_triggered": bool(policy_decision.runtime_adaptive_signal_triggered),
            "runtime_adaptive_profile": str(policy_decision.runtime_adaptive_profile),
            "runtime_adaptive_signal_hits": {
                str(k): bool(v) for k, v in dict(policy_decision.runtime_adaptive_signal_hits).items()
            },
        }
        packet = WatchContractPacket(
            tick=tick,
            trace_ref=str(trace_ref),
            outerfields_ref=outerfields_ref,
            signature=observables.signature.as_dict(),
            metrics={
                "cost": dict(observables.cost),
                "quality": dict(observables.quality),
                "watchpoints": watchpoints,
            },
            events=[dict(event) for event in filtered_events],
            event_types=event_types,
            event_count=int(len(event_types)),
            policy={
                "active_level": str(policy_decision.active_level),
                "detail_mode": policy_decision.observability_profile.normalized_detail_mode(),
                "commit_stride": int(policy_decision.commit_stride),
                "runtime_adaptive_window_active": bool(policy_decision.runtime_adaptive_window_active),
                "runtime_adaptive_profile": str(policy_decision.runtime_adaptive_profile),
                "runtime_adaptive_signal_triggered": bool(policy_decision.runtime_adaptive_signal_triggered),
            },
        )

        assert self._fh is not None
        self._fh.write(json.dumps(packet.to_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()
        self._apply_storage_limit()

    def on_close(self, **_rest: Any) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        self._apply_storage_limit()
        self.detach()

    def detach(self) -> None:
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


@dataclass
class CommitJsonlWriter:
    """Writes streaming `commits.jsonl` packets linked to `trace_ref`."""

    path: Path
    node_id: str = "local"
    commit_type: str = "state"
    mode: str = "realtime"
    retention_window: int = 0
    compaction_budget: int = 0
    _fh: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None
    _last_commit_id: str | None = None
    _bus: Any | None = None

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        node_id: str = "local",
        commit_type: str = "state",
        mode: str = "realtime",
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "CommitJsonlWriter":
        writer = cls(
            path=path,
            node_id=str(node_id),
            commit_type=str(commit_type),
            mode=str(mode),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        writer._bus = bus
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
        tick = int(state.step_count)
        is_commit_boundary = bool(policy_decision.commit_boundary_crossed)
        is_audit_due = bool(policy_decision.audit_commit_enabled) and (
            tick % max(1, int(policy_decision.audit_commit_stride)) == 0
        )
        if self.mode == "audit":
            should_emit = is_commit_boundary and is_audit_due
        else:
            should_emit = is_commit_boundary
        if not should_emit:
            return

        trace_ref = _trace_ref_for_tick(tick)
        commit_id = f"{self.node_id}:{tick}"
        summary: Dict[str, Any] = {
            "event_count": len(list(observables.events)),
            "requested_n_ticks": int(requested_n_ticks or n_ticks),
            "effective_n_ticks": int(n_ticks),
            "commit_stride": int(policy_decision.commit_stride),
            "audit_commit_enabled": bool(policy_decision.audit_commit_enabled),
            "audit_commit_stride": int(policy_decision.audit_commit_stride),
            "epoch": int(tick),
            "watermark": int(tick),
        }
        if self.mode == "audit":
            summary.update(_snapshot_digest(get_state_blob))
            summary["signature_vector"] = list(observables.signature.vector)

        packet = CommitPacket.from_dict(
            {
                "schema_version": DETM_COMMIT_PACKET_V1,
                "commit_type": self.commit_type,
                "mode": self.mode,
                "node_id": self.node_id,
                "commit_id": commit_id,
                "parent_ref": self._last_commit_id,
                "tick_ref": {"base_level": str(policy_decision.active_level), "tick": tick},
                "inputs_ref": f"influence://{tick}" if influence is not None else None,
                "delta_ref": f"delta://L0/{tick}",
                "invariants_ref": f"invariants://L0/{tick}" if self.commit_type == "proof" else None,
                "trace_ref": trace_ref,
                "summary": summary,
                "signature": f"sig://{self.node_id}/{tick}",
                "created_at_ms": int(tick),
            }
        )

        self._ensure()
        assert self._fh is not None
        self._fh.write(json.dumps(packet.to_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)
        self._last_commit_id = commit_id
        if self._bus is not None:
            payload_ref = f"artifact://commit/{self.node_id}/{commit_id}"
            self._bus.publish(
                "commit_packet",
                packet=packet,
                payload_ref=payload_ref,
                node_id=self.node_id,
                commit_type=self.commit_type,
                mode=self.mode,
                trace_ref=trace_ref,
            )

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


@dataclass
class CommitValidationReporter:
    """Writes local validator report with chain/proof and watermark checks."""

    out_dir: Path
    report_name: str = "commit_validation.json"
    history_name: str = "commit_validation_history.jsonl"
    realtime_name: str = "commits.jsonl"
    audit_name: str = "commits_audit.jsonl"
    retention_window: int = 0
    compaction_budget: int = 0
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        out_dir: Path,
        *,
        report_name: str = "commit_validation.json",
        history_name: str = "commit_validation_history.jsonl",
        realtime_name: str = "commits.jsonl",
        audit_name: str = "commits_audit.jsonl",
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "CommitValidationReporter":
        reporter = cls(
            out_dir=out_dir,
            report_name=str(report_name),
            history_name=str(history_name),
            realtime_name=str(realtime_name),
            audit_name=str(audit_name),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        reporter._unsub_close = bus.add_event_listener_unsub("close", reporter.on_close)
        return reporter

    def on_close(self, **_rest: Any) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        realtime_path = self.out_dir / self.realtime_name
        audit_path = self.out_dir / self.audit_name
        report = validate_commit_paths(realtime_path=realtime_path, audit_path=audit_path)
        report["files"] = {
            "realtime_path": str(realtime_path),
            "audit_path": str(audit_path),
            "realtime_exists": bool(realtime_path.exists()),
            "audit_exists": bool(audit_path.exists()),
        }
        (self.out_dir / self.report_name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        history_path = self.out_dir / self.history_name
        with history_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False) + "\n")
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(history_path, max_entries=limit)
        self.detach()

    def detach(self) -> None:
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


@dataclass
class FabricHandshakeRecorder:
    """Local fabric handshake subscriber (`commit_packet -> proof/trust ack`).

    ARCH-MARKERS:
    - LAYER_BAND: L5
    - ABSTRACT_DISTANCE: 1 (network transport + distributed validator still pending)
    - OOP_TECH_DEBT: quorum/retry policy and durable relay adapters
    """

    out_dir: Path
    node_id: str = "local"
    commit_channel: str = "fabric.commit"
    ack_channel: str = "fabric.ack"
    mode_filter: str | None = "realtime"
    split_mode_channels: bool = False
    required_proof_accepts: int = 1
    required_trust_accepts: int = 1
    required_unique_proof_validators: int = 1
    required_unique_trust_validators: int = 1
    required_validator_ids: List[str] | None = None
    enforce_required_validator_ids: bool = False
    reject_on_any_reject: bool = False
    publish_retry_attempts: int = 2
    commit_publish_retry_attempts: int = 2
    delivery_required_receipts: int = 0
    delivery_required_validator_ids: List[str] | None = None
    delivery_enforce_required_validator_ids: bool = False
    delivery_reject_on_any_reject: bool = False
    delivery_retry_interval_ms: int = 100
    delivery_max_attempts: int = 3
    delivery_timeout_ms: int = 500
    delivery_ack_channel: str = "fabric.delivery.ack"
    delivery_emit_ack: bool = True
    pending_timeout_ms: int | None = None
    transport: str = "memory"
    transport_host: str = "127.0.0.1"
    transport_port: int = 0
    transport_connect: bool = False
    transport_keep_open: bool = False
    transport_backpressure_max_pending: int | None = None
    transport_backpressure_policy: str = "block"
    transport_backpressure_block_timeout_ms: int = 200
    artifact_store_dir: str | None = None
    publish_inline_payload: bool = True
    replay_sample_stride: int = 0
    epoch_state_path: str | None = None
    epoch_replica_state_paths: List[str] | None = None
    epoch_replica_read_quorum: int | None = None
    epoch_replica_write_quorum: int | None = None
    epoch_lock_timeout_ms: int = 5000
    epoch_lock_poll_ms: int = 10
    epoch_lock_stale_ms: int | None = 30000
    epoch_consensus_required_total_accepts: int = 1
    epoch_consensus_timeout_ms: int = 200
    epoch_consensus_reject_on_any_reject: bool = False
    epoch_consensus_channel: str = "fabric.epoch"
    epoch_consensus_enabled: bool = False
    delivery_outbox_path: str | None = None
    delivery_outbox_max_entries: int | None = None
    delivery_outbox_flush_limit: int | None = None
    delivery_outbox_drop_policy: str = "audit_first"
    fabric_acks_retention_window: int = 0
    fabric_acks_compaction_budget: int = 0
    fabric_ack_envelopes_retention_window: int = 0
    fabric_ack_envelopes_compaction_budget: int = 0
    fabric_delivery_acks_retention_window: int = 0
    fabric_delivery_acks_compaction_budget: int = 0
    fabric_dead_letters_retention_window: int = 0
    fabric_dead_letters_compaction_budget: int = 0
    fabric_quorum_report_retention_window: int = 0
    fabric_quorum_report_compaction_budget: int = 0
    _transport: FabricTransportAdapter | None = None
    _artifact_store: FileFabricArtifactStore | None = None
    _artifact_resolver: FabricArtifactResolver | None = None
    _delivery_outbox: JsonlFabricEnvelopeOutbox | None = None
    _validator: LocalFabricValidator | None = None
    _epoch_coordinator: FabricEpochCoordinator | None = None
    _epoch_consensus: TransportEpochConsensusCoordinator | None = None
    _service: FabricHandshakeService | None = None
    _ack_runtime: FabricAckIngressService | None = None
    _quorum_runtime: FabricQuorumRuntimeService | None = None
    _commit_ingress: FabricCommitIngressService | None = None
    _quorum_report_builder: FabricQuorumReportBuilder | None = None
    _fabric_report_writer: FabricRuntimeReportWriter | None = None
    _runtime_bundle: FabricHandshakeRuntimeBundle | None = None
    _quorum: InMemoryQuorumCoordinator | None = None
    _validator_registry: ValidatorRegistry | None = None
    _commit_store: Dict[str, CommitPacket] = None  # type: ignore[assignment]
    _commit_ref_index: Dict[str, str] = None  # type: ignore[assignment]
    _ack_store: Dict[str, ProofAck | TrustAck] = None  # type: ignore[assignment]
    _ack_envelopes: List[FabricEnvelope] = None  # type: ignore[assignment]
    _ack_subscriptions: List[tuple[str, str | None]] = None  # type: ignore[assignment]
    _delivery_ack_envelopes: List[FabricEnvelope] = None  # type: ignore[assignment]
    _delivery_ack_subscriptions: List[tuple[str, str | None]] = None  # type: ignore[assignment]
    _delivery_pending: Dict[str, Dict[str, Any]] = None  # type: ignore[assignment]
    _delivery_receipt_coordinator: InMemoryDeliveryReceiptCoordinator | None = None
    _delivery_tracker: DeliveryTrackingCoordinator | None = None
    _delivery_runtime: FabricCommitDeliveryService | None = None
    _delivery_accepted_count: int = 0
    _delivery_rejected_count: int = 0
    _delivery_retries_total: int = 0
    _delivery_counter: int = 0
    _commit_dead_letters: List[Dict[str, str]] = None  # type: ignore[assignment]
    _replay_checks_total: int = 0
    _replay_checks_failed: int = 0
    _unsub_commit: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        out_dir: Path,
        *,
        node_id: str = "local",
        commit_channel: str = "fabric.commit",
        ack_channel: str = "fabric.ack",
        mode_filter: str | None = "realtime",
        split_mode_channels: bool = False,
        required_proof_accepts: int = 1,
        required_trust_accepts: int = 1,
        required_unique_proof_validators: int = 1,
        required_unique_trust_validators: int = 1,
        required_validator_ids: Sequence[str] | None = None,
        enforce_required_validator_ids: bool = False,
        reject_on_any_reject: bool = False,
        publish_retry_attempts: int = 2,
        commit_publish_retry_attempts: int = 2,
        delivery_required_receipts: int = 0,
        delivery_required_validator_ids: Sequence[str] | None = None,
        delivery_enforce_required_validator_ids: bool = False,
        delivery_reject_on_any_reject: bool = False,
        delivery_retry_interval_ms: int = 100,
        delivery_max_attempts: int = 3,
        delivery_timeout_ms: int = 500,
        delivery_ack_channel: str = "fabric.delivery.ack",
        delivery_emit_ack: bool = True,
        pending_timeout_ms: int | None = None,
        transport: str = "memory",
        transport_host: str = "127.0.0.1",
        transport_port: int = 0,
        transport_connect: bool = False,
        transport_keep_open: bool = False,
        transport_backpressure_max_pending: int | None = None,
        transport_backpressure_policy: str = "block",
        transport_backpressure_block_timeout_ms: int = 200,
        artifact_store_dir: str | None = None,
        publish_inline_payload: bool = True,
        replay_sample_stride: int = 0,
        epoch_state_path: str | None = None,
        epoch_replica_state_paths: Sequence[str] | None = None,
        epoch_replica_read_quorum: int | None = None,
        epoch_replica_write_quorum: int | None = None,
        epoch_lock_timeout_ms: int = 5000,
        epoch_lock_poll_ms: int = 10,
        epoch_lock_stale_ms: int | None = 30000,
        epoch_consensus_required_total_accepts: int = 1,
        epoch_consensus_timeout_ms: int = 200,
        epoch_consensus_reject_on_any_reject: bool = False,
        epoch_consensus_channel: str = "fabric.epoch",
        epoch_consensus_enabled: bool = False,
        delivery_outbox_path: str | None = None,
        delivery_outbox_max_entries: int | None = None,
        delivery_outbox_flush_limit: int | None = None,
        delivery_outbox_drop_policy: str = "audit_first",
        fabric_acks_retention_window: int = 0,
        fabric_acks_compaction_budget: int = 0,
        fabric_ack_envelopes_retention_window: int = 0,
        fabric_ack_envelopes_compaction_budget: int = 0,
        fabric_delivery_acks_retention_window: int = 0,
        fabric_delivery_acks_compaction_budget: int = 0,
        fabric_dead_letters_retention_window: int = 0,
        fabric_dead_letters_compaction_budget: int = 0,
        fabric_quorum_report_retention_window: int = 0,
        fabric_quorum_report_compaction_budget: int = 0,
    ) -> "FabricHandshakeRecorder":
        rec = cls(
            out_dir=out_dir,
            **normalize_fabric_handshake_recorder_attach_kwargs(
                node_id=node_id,
                commit_channel=commit_channel,
                ack_channel=ack_channel,
                mode_filter=mode_filter,
                split_mode_channels=split_mode_channels,
                required_proof_accepts=required_proof_accepts,
                required_trust_accepts=required_trust_accepts,
                required_unique_proof_validators=required_unique_proof_validators,
                required_unique_trust_validators=required_unique_trust_validators,
                required_validator_ids=required_validator_ids,
                enforce_required_validator_ids=enforce_required_validator_ids,
                reject_on_any_reject=reject_on_any_reject,
                publish_retry_attempts=publish_retry_attempts,
                commit_publish_retry_attempts=commit_publish_retry_attempts,
                delivery_required_receipts=delivery_required_receipts,
                delivery_required_validator_ids=delivery_required_validator_ids,
                delivery_enforce_required_validator_ids=delivery_enforce_required_validator_ids,
                delivery_reject_on_any_reject=delivery_reject_on_any_reject,
                delivery_retry_interval_ms=delivery_retry_interval_ms,
                delivery_max_attempts=delivery_max_attempts,
                delivery_timeout_ms=delivery_timeout_ms,
                delivery_ack_channel=delivery_ack_channel,
                delivery_emit_ack=delivery_emit_ack,
                pending_timeout_ms=pending_timeout_ms,
                transport=transport,
                transport_host=transport_host,
                transport_port=transport_port,
                transport_connect=transport_connect,
                transport_keep_open=transport_keep_open,
                transport_backpressure_max_pending=transport_backpressure_max_pending,
                transport_backpressure_policy=transport_backpressure_policy,
                transport_backpressure_block_timeout_ms=transport_backpressure_block_timeout_ms,
                artifact_store_dir=artifact_store_dir,
                publish_inline_payload=publish_inline_payload,
                replay_sample_stride=replay_sample_stride,
                epoch_state_path=epoch_state_path,
                epoch_replica_state_paths=epoch_replica_state_paths,
                epoch_replica_read_quorum=epoch_replica_read_quorum,
                epoch_replica_write_quorum=epoch_replica_write_quorum,
                epoch_lock_timeout_ms=epoch_lock_timeout_ms,
                epoch_lock_poll_ms=epoch_lock_poll_ms,
                epoch_lock_stale_ms=epoch_lock_stale_ms,
                epoch_consensus_required_total_accepts=epoch_consensus_required_total_accepts,
                epoch_consensus_timeout_ms=epoch_consensus_timeout_ms,
                epoch_consensus_reject_on_any_reject=epoch_consensus_reject_on_any_reject,
                epoch_consensus_channel=epoch_consensus_channel,
                epoch_consensus_enabled=epoch_consensus_enabled,
                delivery_outbox_path=delivery_outbox_path,
                delivery_outbox_max_entries=delivery_outbox_max_entries,
                delivery_outbox_flush_limit=delivery_outbox_flush_limit,
                delivery_outbox_drop_policy=delivery_outbox_drop_policy,
                fabric_acks_retention_window=fabric_acks_retention_window,
                fabric_acks_compaction_budget=fabric_acks_compaction_budget,
                fabric_ack_envelopes_retention_window=fabric_ack_envelopes_retention_window,
                fabric_ack_envelopes_compaction_budget=fabric_ack_envelopes_compaction_budget,
                fabric_delivery_acks_retention_window=fabric_delivery_acks_retention_window,
                fabric_delivery_acks_compaction_budget=fabric_delivery_acks_compaction_budget,
                fabric_dead_letters_retention_window=fabric_dead_letters_retention_window,
                fabric_dead_letters_compaction_budget=fabric_dead_letters_compaction_budget,
                fabric_quorum_report_retention_window=fabric_quorum_report_retention_window,
                fabric_quorum_report_compaction_budget=fabric_quorum_report_compaction_budget,
            ),
        )
        rec._commit_store = {}
        rec._commit_ref_index = {}
        rec._ack_store = {}
        rec._ack_envelopes = []
        rec._ack_subscriptions = []
        rec._delivery_ack_envelopes = []
        rec._delivery_ack_subscriptions = []
        rec._delivery_pending = {}
        rec._delivery_receipt_coordinator = None
        rec._delivery_tracker = None
        rec._delivery_accepted_count = 0
        rec._delivery_rejected_count = 0
        rec._delivery_retries_total = 0
        rec._delivery_counter = 0
        rec._commit_dead_letters = []
        rec._replay_checks_total = 0
        rec._replay_checks_failed = 0
        composition = compose_fabric_handshake_runtime(
            rec=rec,
            mode_channels=rec._mode_channels,
        )
        rec._commit_store = composition.commit_store
        rec._commit_ref_index = composition.commit_ref_index
        rec._ack_store = composition.ack_store
        rec._artifact_resolver = composition.artifact_resolver
        rec._ack_envelopes = composition.ack_envelopes
        rec._ack_subscriptions = composition.ack_subscriptions
        rec._delivery_ack_envelopes = composition.delivery_ack_envelopes
        rec._delivery_ack_subscriptions = composition.delivery_ack_subscriptions
        rec._delivery_pending = composition.delivery_pending
        rec._delivery_receipt_coordinator = composition.delivery_receipt_coordinator
        rec._delivery_tracker = composition.delivery_tracker
        rec._commit_dead_letters = composition.commit_dead_letters
        rec._artifact_store = composition.artifact_store
        rec._delivery_outbox = composition.delivery_outbox
        rec._transport = composition.transport
        rec._validator = composition.validator
        rec._epoch_coordinator = composition.epoch_coordinator
        rec._epoch_consensus = composition.epoch_consensus
        rec._quorum_runtime = composition.quorum_runtime
        rec._quorum = composition.quorum
        rec._validator_registry = composition.validator_registry
        rec._service = composition.service
        rec._ack_runtime = composition.ack_runtime
        rec._delivery_runtime = composition.delivery_runtime
        rec._commit_ingress = composition.commit_ingress
        rec._quorum_report_builder = composition.quorum_report_builder
        rec._fabric_report_writer = composition.fabric_report_writer
        rec._runtime_bundle = composition.runtime_bundle
        rec._start_runtime_bundle()
        rec._unsub_commit = bus.add_event_listener_unsub("commit_packet", rec.on_commit_packet)
        rec._unsub_close = bus.add_event_listener_unsub("close", rec.on_close)
        return rec

    def _mode_channels(self, base_channel: str) -> Dict[str, str] | None:
        return mode_channels(bool(self.split_mode_channels), str(base_channel))

    def _start_runtime_bundle(self) -> None:
        ack_subs, delivery_subs = start_runtime_bundle(self._runtime_bundle)
        self._ack_subscriptions = list(ack_subs)
        self._delivery_ack_subscriptions = list(delivery_subs)

    def on_commit_packet(
        self,
        *,
        packet: CommitPacket,
        payload_ref: str,
        mode: str,
        trace_ref: str | None = None,
        **_rest: Any,
    ) -> None:
        if not isinstance(packet, CommitPacket):
            return
        if self._transport is None:
            return
        self._tick_delivery_pending()
        if self._commit_ingress is None:
            return
        self._commit_ingress.on_commit_packet(
            packet=packet,
            payload_ref=str(payload_ref),
            mode=str(mode),
            trace_ref=trace_ref,
        )
        self._delivery_counter = int(self._commit_ingress.delivery_counter)

    def _tick_delivery_pending(self) -> None:
        if self._delivery_runtime is None:
            return
        snap = self._delivery_runtime.tick()
        self._delivery_accepted_count = int(snap.get("accepted_count", 0))
        self._delivery_rejected_count = int(snap.get("rejected_count", 0))
        self._delivery_retries_total = int(snap.get("retries_total", 0))

    def _resolve_commit(self, payload_ref: str) -> CommitPacket | None:
        if self._artifact_resolver is None:
            return None
        return self._artifact_resolver.resolve_commit(payload_ref)

    def _replay_check(self, packet: CommitPacket) -> tuple[bool, str | None]:
        if self._artifact_resolver is None:
            return False, "artifact resolver is not configured"
        ok, reason = self._artifact_resolver.replay_check(packet)
        snap = self._artifact_resolver.replay_snapshot()
        self._replay_checks_total = int(snap.get("checks_total", 0))
        self._replay_checks_failed = int(snap.get("checks_failed", 0))
        return ok, reason

    def _write_ack(self, ack: ProofAck | TrustAck) -> str:
        if self._artifact_resolver is None:
            raise RuntimeError("artifact resolver is not configured")
        return self._artifact_resolver.write_ack(ack)

    def _resolve_ack(self, payload_ref: str) -> ProofAck | TrustAck | None:
        if self._artifact_resolver is None:
            return None
        return self._artifact_resolver.resolve_ack(payload_ref)

    def _on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        if self._ack_runtime is not None:
            self._ack_runtime.on_ack_envelope(envelope)

    def _on_delivery_ack_envelope(self, envelope: FabricEnvelope) -> None:
        if self._delivery_runtime is not None:
            self._delivery_runtime.on_delivery_ack_envelope(envelope)

    def on_close(self, **_rest: Any) -> None:
        self._tick_delivery_pending()
        if self._artifact_resolver is not None:
            replay = self._artifact_resolver.replay_snapshot()
            self._replay_checks_total = int(replay.get("checks_total", 0))
            self._replay_checks_failed = int(replay.get("checks_failed", 0))
        if self._fabric_report_writer is not None:
            self._fabric_report_writer.write_all(
                replay_sample_stride=int(self.replay_sample_stride),
                replay_checks_total=int(self._replay_checks_total),
                replay_checks_failed=int(self._replay_checks_failed),
            )
        self.detach()

    def detach(self) -> None:
        if self._runtime_bundle is not None:
            self._runtime_bundle.stop()
            self._ack_subscriptions = []
            self._delivery_ack_subscriptions = []
            self._runtime_bundle = None
        elif self._transport is not None:
            self._transport.close()
        self._service = None
        self._ack_runtime = None
        self._delivery_runtime = None
        self._commit_ingress = None
        self._transport = None
        self._quorum_runtime = None
        self._quorum_report_builder = None
        self._fabric_report_writer = None
        self._quorum = None
        self._epoch_consensus = None
        self._epoch_coordinator = None
        self._validator_registry = None
        self._artifact_store = None
        self._artifact_resolver = None
        self._delivery_outbox = None
        if self._delivery_tracker is not None:
            self._delivery_tracker.clear()
            self._delivery_tracker = None
        self._delivery_receipt_coordinator = None
        self._delivery_pending = {}
        self._commit_ref_index = {}
        if self._unsub_commit is not None:
            self._unsub_commit()
            self._unsub_commit = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


@dataclass
class InvariantTickJsonlWriter:
    """Writes `invariants.jsonl` from `invariant_tick` events.

    This is intentionally separate from `JsonlTraceWriter` to keep persistence
    concerns isolated from the simulation and from other trace formats.
    """

    path: Path
    include_signature: bool = False
    retention_window: int = 0
    compaction_budget: int = 0
    _fh: Any | None = None
    _unsub_inv: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        include_signature: bool = False,
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "InvariantTickJsonlWriter":
        writer = cls(
            path=path,
            include_signature=bool(include_signature),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        writer._unsub_inv = bus.add_event_listener_unsub("invariant_tick", writer.on_invariant_tick)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def on_invariant_tick(self, **payload: Any) -> None:
        self._ensure()
        entry: Dict[str, Any] = {
            "type": "invariant_tick",
            "stream_id": payload.get("stream_id"),
            "l0_tick": payload.get("l0_tick"),
            "delta_l0_ticks": payload.get("delta_l0_ticks"),
            "dt_num": payload.get("dt_num"),
            "dt_den": payload.get("dt_den"),
            "time_num": payload.get("time_num"),
            "invariant_index": payload.get("invariant_index"),
            "phase_num": payload.get("phase_num"),
            "boundary_crossed": payload.get("boundary_crossed"),
        }

        if self.include_signature:
            obs = payload.get("observables")
            sig = getattr(obs, "signature", None) if obs is not None else None
            if sig is not None and hasattr(sig, "as_dict"):
                entry["signature"] = sig.as_dict()

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
        if self._unsub_inv is not None:
            self._unsub_inv()
            self._unsub_inv = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


@dataclass
class VizStreamer:
    """Streams state updates to a VizTransport.

    For now we stream serialized state blobs; transports can choose how they
    deliver frames (tcp/shared memory/etc.).
    """

    transport: VizTransport
    every_steps: int = 1
    _last_sent_step: int = -1
    _unsub_reset: Callable[[], None] | None = None
    _unsub_step: Callable[[], None] | None = None

    @classmethod
    def attach(cls, bus, transport: VizTransport, *, every_steps: int = 1) -> "VizStreamer":
        inst = cls(transport=transport, every_steps=max(1, int(every_steps)))
        inst._unsub_reset = bus.add_event_listener_unsub("reset", inst.on_reset)
        inst._unsub_step = bus.add_event_listener_unsub("step", inst.on_step)
        return inst

    @staticmethod
    def _resolve_active_level(
        *,
        config: DETMConfig | None = None,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
    ) -> str | None:
        if policy_decision is not None:
            value = str(policy_decision.active_level or "").strip()
            if value:
                return value
        if level_policy is not None:
            value = str(level_policy.active_level or "").strip()
            if value:
                return value
        if config is not None:
            value = str(config.level_policy.active_level or "").strip()
            if value:
                return value
        return None

    def _maybe_send(
        self,
        state: DETMState,
        signature: api.DETMSignature,
        get_state_blob: Any | None = None,
        *,
        active_level: str | None = None,
    ) -> None:
        step_count = int(state.step_count)
        if self._last_sent_step >= 0 and (step_count - self._last_sent_step) < self.every_steps:
            return
        self._last_sent_step = step_count
        blob = get_state_blob() if callable(get_state_blob) else api.serialize(state)
        meta = {"active_level": str(active_level)} if active_level else None
        try:
            self.transport.send_state(state_blob=blob, tick=step_count, signature=signature.vector, meta=meta)
        except Exception:
            # Viz is best-effort: if a transport drops (daemon closed, socket error),
            # keep the simulation running and stop streaming further.
            self.detach()

    def on_reset(
        self,
        *,
        state: DETMState,
        config: DETMConfig | None = None,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
        get_state_blob: Any | None = None,
        **_rest: Any,
    ) -> None:
        self._last_sent_step = -1
        self._maybe_send(
            state,
            api.digest(state),
            get_state_blob,
            active_level=self._resolve_active_level(
                config=config,
                level_policy=level_policy,
                policy_decision=policy_decision,
            ),
        )

    def on_step(
        self,
        *,
        state: DETMState,
        observables: api.Observables,
        config: DETMConfig | None = None,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
        get_state_blob: Any | None = None,
        **_rest: Any,
    ) -> None:
        self._maybe_send(
            state,
            observables.signature,
            get_state_blob,
            active_level=self._resolve_active_level(
                config=config,
                level_policy=level_policy,
                policy_decision=policy_decision,
            ),
        )

    def detach(self) -> None:
        if self._unsub_reset is not None:
            self._unsub_reset()
            self._unsub_reset = None
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None


__all__ = [
    "ArtifactWriter",
    "CommitJsonlWriter",
    "CommitValidationReporter",
    "FabricHandshakeRecorder",
    "FieldHistoryRecorder",
    "InvariantTickJsonlWriter",
    "JsonlTraceWriter",
    "SystemTraceWriter",
    "TraceRecorder",
    "VizStreamer",
    "WatchContractWriter",
    "WatchTraceWriter",
]
