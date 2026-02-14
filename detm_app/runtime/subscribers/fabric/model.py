"""Data model for FabricHandshakeRecorder settings and runtime handles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import (
    DeliveryTrackingCoordinator,
    FabricAckIngressService,
    FabricArtifactResolver,
    FabricCommitDeliveryService,
    FabricCommitIngressService,
    FabricEnvelope,
    FabricEnvelopeOutbox,
    FabricEpochCoordinator,
    FabricHandshakeRuntimeBundle,
    FabricHandshakeService,
    FabricQuorumReportBuilder,
    FabricQuorumRuntimeService,
    FabricRuntimeReportWriter,
    FabricTransportAdapter,
    FileFabricArtifactStore,
    InMemoryDeliveryReceiptCoordinator,
    InMemoryQuorumCoordinator,
    LocalFabricValidator,
    ProofAck,
    TransportEpochConsensusCoordinator,
    TrustAck,
    ValidatorRegistry,
)


@dataclass
class FabricHandshakeRecorderModel:
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


__all__ = ["FabricHandshakeRecorderModel"]
