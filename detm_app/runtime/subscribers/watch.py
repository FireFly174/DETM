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

