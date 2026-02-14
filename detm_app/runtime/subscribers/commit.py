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
            "step_requested_n_ticks": int(step_requested_n_ticks or requested_n_ticks or n_ticks),
            "step_effective_n_ticks": int(step_effective_n_ticks or n_ticks),
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

