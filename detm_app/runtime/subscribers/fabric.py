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
from detm.runtime.fabric import FabricEnvelopeOutbox
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
    handshake_profile: str = "mvp"
    enforce_required_validator_ids: bool = False
    enforce_active_validator_membership: bool = False
    enforce_ack_sender_validator_match: bool = False
    enforce_ack_auth_key_id_binding: bool = False
    validator_auth_key_ids: Dict[str, List[str]] | None = None
    enforce_ack_transport_identity_binding: bool = False
    validator_transport_identities: Dict[str, List[str]] | None = None
    reject_on_any_reject: bool = False
    publish_retry_attempts: int = 2
    commit_publish_retry_attempts: int = 2
    delivery_required_receipts: int = 0
    delivery_guarantee_mode: str = "at_least_once_idempotent"
    delivery_required_validator_ids: List[str] | None = None
    delivery_enforce_required_validator_ids: bool = False
    delivery_reject_on_any_reject: bool = False
    delivery_retry_interval_ms: int = 100
    delivery_max_attempts: int = 3
    delivery_timeout_ms: int = 500
    delivery_tracking_state_path: str | None = None
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
    transport_dedup_ingress_enabled: bool = False
    transport_dedup_ttl_ms: int = 30_000
    transport_dedup_max_entries: int = 10_000
    transport_auth_enabled: bool = False
    transport_auth_key: str | None = None
    transport_auth_key_id: str | None = None
    transport_tls_enabled: bool = False
    transport_tls_server_hostname: str | None = None
    transport_tls_ca_file: str | None = None
    transport_tls_cert_file: str | None = None
    transport_tls_key_file: str | None = None
    transport_tls_require_client_cert: bool = False
    transport_tls_client_ca_file: str | None = None
    transport_tls_insecure_skip_verify: bool = False
    transport_tls_identity_source: str = "auto"
    transport_tls_identity_fallback_to_fingerprint: bool = False
    artifact_store_dir: str | None = None
    publish_inline_payload: bool = True
    replay_sample_stride: int = 0
    replay_policy_tier: str = "sampled"
    replay_strict_window_size: int = 128
    validator_coordination_state_path: str | None = None
    validator_coordination_replica_paths: List[str] | None = None
    validator_coordination_replica_read_quorum: int | None = None
    validator_coordination_replica_write_quorum: int | None = None
    epoch_state_path: str | None = None
    epoch_replica_state_paths: List[str] | None = None
    epoch_replica_read_quorum: int | None = None
    epoch_replica_write_quorum: int | None = None
    epoch_lock_timeout_ms: int = 5000
    epoch_lock_poll_ms: int = 10
    epoch_lock_stale_ms: int | None = 30000
    epoch_consensus_required_total_accepts: int = 1
    epoch_consensus_timeout_ms: int = 200
    epoch_consensus_max_attempts: int = 1
    epoch_consensus_reject_on_any_reject: bool = False
    epoch_consensus_channel: str = "fabric.epoch"
    epoch_consensus_enabled: bool = False
    delivery_outbox_path: str | None = None
    delivery_outbox_replica_paths: List[str] | None = None
    delivery_outbox_replica_read_quorum: int | None = None
    delivery_outbox_replica_write_quorum: int | None = None
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
    _delivery_outbox: FabricEnvelopeOutbox | None = None
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
    _bus: Any | None = None
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
        handshake_profile: str = "mvp",
        enforce_required_validator_ids: bool = False,
        enforce_active_validator_membership: bool = False,
        enforce_ack_sender_validator_match: bool = False,
        enforce_ack_auth_key_id_binding: bool = False,
        validator_auth_key_ids: Dict[str, Sequence[str] | str] | Sequence[str] | str | None = None,
        enforce_ack_transport_identity_binding: bool = False,
        validator_transport_identities: Dict[str, Sequence[str] | str] | Sequence[str] | str | None = None,
        reject_on_any_reject: bool = False,
        publish_retry_attempts: int = 2,
        commit_publish_retry_attempts: int = 2,
        delivery_required_receipts: int = 0,
        delivery_guarantee_mode: str = "at_least_once_idempotent",
        delivery_required_validator_ids: Sequence[str] | None = None,
        delivery_enforce_required_validator_ids: bool = False,
        delivery_reject_on_any_reject: bool = False,
        delivery_retry_interval_ms: int = 100,
        delivery_max_attempts: int = 3,
        delivery_timeout_ms: int = 500,
        delivery_tracking_state_path: str | None = None,
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
        transport_dedup_ingress_enabled: bool = False,
        transport_dedup_ttl_ms: int = 30_000,
        transport_dedup_max_entries: int = 10_000,
        transport_auth_enabled: bool = False,
        transport_auth_key: str | None = None,
        transport_auth_key_id: str | None = None,
        transport_tls_enabled: bool = False,
        transport_tls_server_hostname: str | None = None,
        transport_tls_ca_file: str | None = None,
        transport_tls_cert_file: str | None = None,
        transport_tls_key_file: str | None = None,
        transport_tls_require_client_cert: bool = False,
        transport_tls_client_ca_file: str | None = None,
        transport_tls_insecure_skip_verify: bool = False,
        transport_tls_identity_source: str = "auto",
        transport_tls_identity_fallback_to_fingerprint: bool = False,
        artifact_store_dir: str | None = None,
        publish_inline_payload: bool = True,
        replay_sample_stride: int = 0,
        replay_policy_tier: str = "sampled",
        replay_strict_window_size: int = 128,
        validator_coordination_state_path: str | None = None,
        validator_coordination_replica_paths: Sequence[str] | None = None,
        validator_coordination_replica_read_quorum: int | None = None,
        validator_coordination_replica_write_quorum: int | None = None,
        epoch_state_path: str | None = None,
        epoch_replica_state_paths: Sequence[str] | None = None,
        epoch_replica_read_quorum: int | None = None,
        epoch_replica_write_quorum: int | None = None,
        epoch_lock_timeout_ms: int = 5000,
        epoch_lock_poll_ms: int = 10,
        epoch_lock_stale_ms: int | None = 30000,
        epoch_consensus_required_total_accepts: int = 1,
        epoch_consensus_timeout_ms: int = 200,
        epoch_consensus_max_attempts: int = 1,
        epoch_consensus_reject_on_any_reject: bool = False,
        epoch_consensus_channel: str = "fabric.epoch",
        epoch_consensus_enabled: bool = False,
        delivery_outbox_path: str | None = None,
        delivery_outbox_replica_paths: Sequence[str] | None = None,
        delivery_outbox_replica_read_quorum: int | None = None,
        delivery_outbox_replica_write_quorum: int | None = None,
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
                handshake_profile=handshake_profile,
                enforce_required_validator_ids=enforce_required_validator_ids,
                enforce_active_validator_membership=enforce_active_validator_membership,
                enforce_ack_sender_validator_match=enforce_ack_sender_validator_match,
                enforce_ack_auth_key_id_binding=enforce_ack_auth_key_id_binding,
                validator_auth_key_ids=validator_auth_key_ids,
                enforce_ack_transport_identity_binding=enforce_ack_transport_identity_binding,
                validator_transport_identities=validator_transport_identities,
                reject_on_any_reject=reject_on_any_reject,
                publish_retry_attempts=publish_retry_attempts,
                commit_publish_retry_attempts=commit_publish_retry_attempts,
                delivery_required_receipts=delivery_required_receipts,
                delivery_guarantee_mode=delivery_guarantee_mode,
                delivery_required_validator_ids=delivery_required_validator_ids,
                delivery_enforce_required_validator_ids=delivery_enforce_required_validator_ids,
                delivery_reject_on_any_reject=delivery_reject_on_any_reject,
                delivery_retry_interval_ms=delivery_retry_interval_ms,
                delivery_max_attempts=delivery_max_attempts,
                delivery_timeout_ms=delivery_timeout_ms,
                delivery_tracking_state_path=delivery_tracking_state_path,
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
                transport_dedup_ingress_enabled=transport_dedup_ingress_enabled,
                transport_dedup_ttl_ms=transport_dedup_ttl_ms,
                transport_dedup_max_entries=transport_dedup_max_entries,
                transport_auth_enabled=transport_auth_enabled,
                transport_auth_key=transport_auth_key,
                transport_auth_key_id=transport_auth_key_id,
                transport_tls_enabled=transport_tls_enabled,
                transport_tls_server_hostname=transport_tls_server_hostname,
                transport_tls_ca_file=transport_tls_ca_file,
                transport_tls_cert_file=transport_tls_cert_file,
                transport_tls_key_file=transport_tls_key_file,
                transport_tls_require_client_cert=transport_tls_require_client_cert,
                transport_tls_client_ca_file=transport_tls_client_ca_file,
                transport_tls_insecure_skip_verify=transport_tls_insecure_skip_verify,
                transport_tls_identity_source=transport_tls_identity_source,
                transport_tls_identity_fallback_to_fingerprint=transport_tls_identity_fallback_to_fingerprint,
                artifact_store_dir=artifact_store_dir,
                publish_inline_payload=publish_inline_payload,
                replay_sample_stride=replay_sample_stride,
                replay_policy_tier=replay_policy_tier,
                replay_strict_window_size=replay_strict_window_size,
                validator_coordination_state_path=validator_coordination_state_path,
                validator_coordination_replica_paths=validator_coordination_replica_paths,
                validator_coordination_replica_read_quorum=validator_coordination_replica_read_quorum,
                validator_coordination_replica_write_quorum=validator_coordination_replica_write_quorum,
                epoch_state_path=epoch_state_path,
                epoch_replica_state_paths=epoch_replica_state_paths,
                epoch_replica_read_quorum=epoch_replica_read_quorum,
                epoch_replica_write_quorum=epoch_replica_write_quorum,
                epoch_lock_timeout_ms=epoch_lock_timeout_ms,
                epoch_lock_poll_ms=epoch_lock_poll_ms,
                epoch_lock_stale_ms=epoch_lock_stale_ms,
                epoch_consensus_required_total_accepts=epoch_consensus_required_total_accepts,
                epoch_consensus_timeout_ms=epoch_consensus_timeout_ms,
                epoch_consensus_max_attempts=epoch_consensus_max_attempts,
                epoch_consensus_reject_on_any_reject=epoch_consensus_reject_on_any_reject,
                epoch_consensus_channel=epoch_consensus_channel,
                epoch_consensus_enabled=epoch_consensus_enabled,
                delivery_outbox_path=delivery_outbox_path,
                delivery_outbox_replica_paths=delivery_outbox_replica_paths,
                delivery_outbox_replica_read_quorum=delivery_outbox_replica_read_quorum,
                delivery_outbox_replica_write_quorum=delivery_outbox_replica_write_quorum,
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
        rec._bus = bus
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
        self._publish_runtime_snapshot()

    def _tick_delivery_pending(self) -> None:
        if self._delivery_runtime is None:
            return
        snap = self._delivery_runtime.tick()
        self._delivery_accepted_count = int(snap.get("accepted_count", 0))
        self._delivery_rejected_count = int(snap.get("rejected_count", 0))
        self._delivery_retries_total = int(snap.get("retries_total", 0))

    def _runtime_snapshot(self) -> Dict[str, Any]:
        delivery = (
            self._delivery_runtime.snapshot()
            if self._delivery_runtime is not None
            else {
                "accepted_count": int(self._delivery_accepted_count),
                "rejected_count": int(self._delivery_rejected_count),
                "pending_count": int(len(self._delivery_pending or {})),
                "retries_total": int(self._delivery_retries_total),
            }
        )
        quorum = self._quorum_runtime.snapshot() if self._quorum_runtime is not None else {}
        return {
            "enabled": True,
            "commit_count": int(len(self._commit_store or {})),
            "ack_count": int(len(self._ack_store or {})),
            "ack_envelope_count": int(len(self._ack_envelopes or [])),
            "delivery_ack_count": int(len(self._delivery_ack_envelopes or [])),
            "dead_letter_count": int(len(self._commit_dead_letters or [])),
            "delivery": {
                "accepted_count": int(delivery.get("accepted_count", 0)),
                "rejected_count": int(delivery.get("rejected_count", 0)),
                "pending_count": int(delivery.get("pending_count", 0)),
                "retries_total": int(delivery.get("retries_total", 0)),
            },
            "quorum": {
                "commit_count": int(quorum.get("commit_count", 0)),
                "accepted_count": int(quorum.get("accepted_count", 0)),
                "pending_count": int(quorum.get("pending_count", 0)),
                "rejected_count": int(quorum.get("rejected_count", 0)),
            },
            "replay": {
                "checks_total": int(self._replay_checks_total),
                "checks_failed": int(self._replay_checks_failed),
            },
        }

    def _publish_runtime_snapshot(self) -> None:
        if self._bus is None:
            return
        self._bus.publish("fabric_runtime_snapshot", snapshot=self._runtime_snapshot())

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
        self._publish_runtime_snapshot()
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

