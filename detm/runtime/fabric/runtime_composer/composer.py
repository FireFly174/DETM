"""Factory/composer for fabric handshake runtime components."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FabricAckIngressService
from detm.runtime.fabric import FabricArtifactResolver
from detm.runtime.fabric import FileFabricArtifactStore
from detm.runtime.fabric import FabricCommitDeliveryService
from detm.runtime.fabric import FabricCommitIngressService
from detm.runtime.fabric import OUTBOX_DROP_POLICIES, JsonlFabricEnvelopeOutbox, ReplicatedJsonlFabricEnvelopeOutbox
from detm.runtime.fabric import (
    CountDeliveryReceiptPolicy,
    InMemoryDeliveryReceiptCoordinator,
    ValidatorSetDeliveryReceiptPolicy,
)
from detm.runtime.fabric import DeliveryTrackingCoordinator
from detm.runtime.fabric import (
    FabricEpochCoordinator,
    FileEpochWatermarkCoordinator,
    InMemoryEpochWatermarkCoordinator,
    ReplicatedFileEpochWatermarkCoordinator,
)
from detm.runtime.fabric import TransportEpochConsensusCoordinator
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import FabricHandshakeService, RetryPolicy
from detm.runtime.fabric.runtime_composer.contracts import FabricHandshakeRuntimeComposition
from detm.runtime.fabric import InMemoryQuorumCoordinator
from detm.runtime.fabric import FabricQuorumReportBuilder
from detm.runtime.fabric import FabricQuorumRuntimeService
from detm.runtime.fabric import FabricRuntimeReportWriter
from detm.runtime.fabric import FabricHandshakeRuntimeBundle
from detm.runtime.fabric import open_fabric_transport
from detm.runtime.fabric import BACKPRESSURE_POLICIES, BufferedFabricTransport, FabricTransportAdapter
from detm.runtime.fabric import LocalFabricValidator, ReplaySamplePolicy
from detm.runtime.fabric import ValidatorRegistry
from detm.runtime.fabric.validator.policies import normalize_replay_policy_tier

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (runtime composition extracted from subscriber attach path)
# - OOP_TECH_DEBT: distributed config/schema for runtime-composer presets


def compose_fabric_handshake_runtime(
    *,
    rec: Any,
    mode_channels: Callable[[str], dict[str, str] | None],
) -> FabricHandshakeRuntimeComposition:
    """Build runtime composition from normalized recorder settings."""

    commit_store: dict[str, CommitPacket] = {}
    commit_ref_index: dict[str, str] = {}
    ack_store: dict[str, ProofAck | TrustAck] = {}
    ack_envelopes: list[FabricEnvelope] = []
    ack_subscriptions: list[tuple[str, str | None]] = []
    delivery_ack_envelopes: list[FabricEnvelope] = []
    delivery_ack_subscriptions: list[tuple[str, str | None]] = []
    delivery_pending: dict[str, dict[str, Any]] = {}
    commit_dead_letters: list[dict[str, str]] = []
    delivery_tracking_state_path = (
        Path(str(rec.delivery_tracking_state_path))
        if getattr(rec, "delivery_tracking_state_path", None) is not None
        else Path(rec.out_dir) / "fabric_delivery_tracking_state.json"
    )

    if bool(rec.delivery_enforce_required_validator_ids) or bool(list(rec.delivery_required_validator_ids or [])):
        delivery_policy = ValidatorSetDeliveryReceiptPolicy(
            required_receipts=max(0, int(rec.delivery_required_receipts)),
            required_validator_ids=frozenset(str(v).strip() for v in list(rec.delivery_required_validator_ids or [])),
            enforce_required_validator_ids=bool(rec.delivery_enforce_required_validator_ids),
            reject_on_any_reject=bool(rec.delivery_reject_on_any_reject),
        )
    else:
        delivery_policy = CountDeliveryReceiptPolicy(
            required_receipts=max(0, int(rec.delivery_required_receipts)),
            reject_on_any_reject=bool(rec.delivery_reject_on_any_reject),
        )

    delivery_receipt_coordinator = InMemoryDeliveryReceiptCoordinator(policy=delivery_policy)
    delivery_tracker = DeliveryTrackingCoordinator(
        receipt_coordinator=delivery_receipt_coordinator,
        required_receipts=max(0, int(rec.delivery_required_receipts)),
        retry_interval_ms=max(0, int(rec.delivery_retry_interval_ms)),
        max_attempts=max(1, int(rec.delivery_max_attempts)),
        timeout_ms=max(1, int(rec.delivery_timeout_ms)),
        tracking_enabled=bool(
            int(rec.delivery_required_receipts) > 0
            or (bool(rec.delivery_enforce_required_validator_ids) and bool(list(rec.delivery_required_validator_ids or [])))
            or bool(rec.delivery_reject_on_any_reject)
        ),
        pending=delivery_pending,
        state_path=str(delivery_tracking_state_path),
    )

    outbox_drop_policy = (
        str(rec.delivery_outbox_drop_policy).strip().lower()
        if str(rec.delivery_outbox_drop_policy).strip().lower() in OUTBOX_DROP_POLICIES
        else "audit_first"
    )
    outbox_replica_paths = [str(v).strip() for v in list(getattr(rec, "delivery_outbox_replica_paths", []) or [])]
    if outbox_replica_paths:
        delivery_outbox = ReplicatedJsonlFabricEnvelopeOutbox(
            paths=outbox_replica_paths,
            read_quorum=getattr(rec, "delivery_outbox_replica_read_quorum", None),
            write_quorum=getattr(rec, "delivery_outbox_replica_write_quorum", None),
            max_entries=rec.delivery_outbox_max_entries,
            drop_policy=outbox_drop_policy,
        )
    else:
        outbox_path = (
            Path(rec.delivery_outbox_path)
            if rec.delivery_outbox_path is not None
            else Path(rec.out_dir) / "fabric_delivery_outbox.jsonl"
        )
        delivery_outbox = JsonlFabricEnvelopeOutbox(
            path=Path(outbox_path),
            max_entries=rec.delivery_outbox_max_entries,
            drop_policy=outbox_drop_policy,
        )

    artifact_store: FileFabricArtifactStore | None = None
    if rec.artifact_store_dir is not None:
        artifact_store = FileFabricArtifactStore(Path(rec.artifact_store_dir))
    artifact_resolver = FabricArtifactResolver(
        node_id=str(rec.node_id),
        artifact_store=artifact_store,
        commit_store=commit_store,
        commit_ref_index=commit_ref_index,
        ack_store=ack_store,
    )

    transport = open_fabric_transport(
        transport=str(rec.transport),
        host=str(rec.transport_host),
        port=int(rec.transport_port),
        connect=bool(rec.transport_connect),
        keep_open=bool(rec.transport_keep_open),
        dedup_ingress_enabled=bool(getattr(rec, "transport_dedup_ingress_enabled", False)),
        dedup_ttl_ms=int(getattr(rec, "transport_dedup_ttl_ms", 30_000)),
        dedup_max_entries=int(getattr(rec, "transport_dedup_max_entries", 10_000)),
        auth_enabled=bool(getattr(rec, "transport_auth_enabled", False)),
        auth_key=getattr(rec, "transport_auth_key", None),
        auth_key_id=getattr(rec, "transport_auth_key_id", None),
        tls_enabled=bool(getattr(rec, "transport_tls_enabled", False)),
        tls_server_hostname=getattr(rec, "transport_tls_server_hostname", None),
        tls_ca_file=getattr(rec, "transport_tls_ca_file", None),
        tls_cert_file=getattr(rec, "transport_tls_cert_file", None),
        tls_key_file=getattr(rec, "transport_tls_key_file", None),
        tls_require_client_cert=bool(getattr(rec, "transport_tls_require_client_cert", False)),
        tls_client_ca_file=getattr(rec, "transport_tls_client_ca_file", None),
        tls_insecure_skip_verify=bool(getattr(rec, "transport_tls_insecure_skip_verify", False)),
        tls_identity_source=getattr(rec, "transport_tls_identity_source", "auto"),
        tls_identity_fallback_to_fingerprint=bool(
            getattr(rec, "transport_tls_identity_fallback_to_fingerprint", False)
        ),
    )
    if rec.transport_backpressure_max_pending is not None:
        transport = BufferedFabricTransport(
            base=transport,
            max_pending=int(rec.transport_backpressure_max_pending),
            policy=(
                str(rec.transport_backpressure_policy).strip().lower()
                if str(rec.transport_backpressure_policy).strip().lower() in BACKPRESSURE_POLICIES
                else "block"
            ),
            block_timeout_ms=int(rec.transport_backpressure_block_timeout_ms),
            close_base_on_close=True,
        )

    replay_tier = normalize_replay_policy_tier(getattr(rec, "replay_policy_tier", "sampled"))
    replay_stride = max(1, int(getattr(rec, "replay_sample_stride", 1) or 1))
    replay_enabled = bool(
        replay_tier == "strict_window"
        or (replay_tier == "sampled" and int(getattr(rec, "replay_sample_stride", 0)) > 0)
    )
    validator = LocalFabricValidator(
        validator_id=f"validator.{rec.node_id}",
        replay_policy=ReplaySamplePolicy(
            tier=replay_tier,
            enabled=bool(replay_enabled),
            sample_stride=replay_stride,
            sample_offset=0,
            strict_window_size=max(1, int(getattr(rec, "replay_strict_window_size", 128))),
        ),
        replay_checker=artifact_resolver.replay_check if replay_enabled else None,
    )

    epoch_coordinator: FabricEpochCoordinator
    if list(rec.epoch_replica_state_paths or []):
        epoch_coordinator = ReplicatedFileEpochWatermarkCoordinator(
            state_paths=list(rec.epoch_replica_state_paths or []),
            read_quorum=rec.epoch_replica_read_quorum,
            write_quorum=rec.epoch_replica_write_quorum,
            lock_timeout_ms=int(rec.epoch_lock_timeout_ms),
            lock_poll_ms=int(rec.epoch_lock_poll_ms),
            lock_stale_ms=None if rec.epoch_lock_stale_ms is None else int(rec.epoch_lock_stale_ms),
        )
    elif rec.epoch_state_path is not None:
        epoch_coordinator = FileEpochWatermarkCoordinator(
            Path(rec.epoch_state_path),
            lock_timeout_ms=int(rec.epoch_lock_timeout_ms),
            lock_poll_ms=int(rec.epoch_lock_poll_ms),
            lock_stale_ms=None if rec.epoch_lock_stale_ms is None else int(rec.epoch_lock_stale_ms),
        )
    elif artifact_store is not None:
        epoch_coordinator = FileEpochWatermarkCoordinator(
            artifact_store.root_dir / "epoch_state.json",
            lock_timeout_ms=int(rec.epoch_lock_timeout_ms),
            lock_poll_ms=int(rec.epoch_lock_poll_ms),
            lock_stale_ms=None if rec.epoch_lock_stale_ms is None else int(rec.epoch_lock_stale_ms),
        )
    else:
        epoch_coordinator = InMemoryEpochWatermarkCoordinator()

    epoch_consensus: TransportEpochConsensusCoordinator | None = None
    use_consensus = bool(rec.epoch_consensus_enabled) or int(rec.epoch_consensus_required_total_accepts) > 1
    if use_consensus:
        epoch_consensus = TransportEpochConsensusCoordinator(
            coordinator_id=f"epoch.{rec.node_id}",
            transport=transport,
            base_coordinator=epoch_coordinator,
            channel=str(rec.epoch_consensus_channel),
            mode_filter=rec.mode_filter,
            required_total_accepts=int(rec.epoch_consensus_required_total_accepts),
            timeout_ms=int(rec.epoch_consensus_timeout_ms),
            max_attempts=int(getattr(rec, "epoch_consensus_max_attempts", 1)),
            reject_on_any_peer_reject=bool(rec.epoch_consensus_reject_on_any_reject),
        )
        epoch_consensus.start()
        epoch_coordinator = epoch_consensus

    quorum_runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=int(rec.required_proof_accepts),
        required_trust_accepts=int(rec.required_trust_accepts),
        required_unique_proof_validators=int(rec.required_unique_proof_validators),
        required_unique_trust_validators=int(rec.required_unique_trust_validators),
        required_validator_ids=rec.required_validator_ids,
        enforce_required_validator_ids=bool(rec.enforce_required_validator_ids),
        reject_on_any_reject=bool(rec.reject_on_any_reject),
        pending_timeout_ms=rec.pending_timeout_ms,
        ack_resolver=artifact_resolver.resolve_ack,
        enforce_active_validator_membership=bool(getattr(rec, "enforce_active_validator_membership", False)),
        enforce_ack_sender_validator_match=bool(getattr(rec, "enforce_ack_sender_validator_match", False)),
        enforce_ack_auth_key_id_binding=bool(getattr(rec, "enforce_ack_auth_key_id_binding", False)),
        validator_auth_key_ids=getattr(rec, "validator_auth_key_ids", None),
        enforce_ack_transport_identity_binding=bool(
            getattr(rec, "enforce_ack_transport_identity_binding", False)
        ),
        validator_transport_identities=getattr(rec, "validator_transport_identities", None),
        validator_coordination_state_path=getattr(rec, "validator_coordination_state_path", None),
        validator_coordination_replica_paths=getattr(rec, "validator_coordination_replica_paths", None),
        validator_coordination_replica_read_quorum=getattr(rec, "validator_coordination_replica_read_quorum", None),
        validator_coordination_replica_write_quorum=getattr(rec, "validator_coordination_replica_write_quorum", None),
    )
    quorum = quorum_runtime.coordinator
    validator_registry = quorum_runtime.validator_registry

    service = FabricHandshakeService(
        transport=transport,
        validator=validator,
        commit_resolver=artifact_resolver.resolve_commit,
        ack_writer=artifact_resolver.write_ack,
        commit_channel=rec.commit_channel,
        ack_channel=rec.ack_channel,
        delivery_ack_channel=rec.delivery_ack_channel,
        emit_delivery_ack=bool(rec.delivery_emit_ack),
        commit_channels_by_mode=mode_channels(rec.commit_channel),
        ack_channels_by_mode=mode_channels(rec.ack_channel),
        delivery_ack_channels_by_mode=mode_channels(rec.delivery_ack_channel),
        mode_filter=rec.mode_filter,
        delivery_outbox=delivery_outbox,
        outbox_flush_limit=rec.delivery_outbox_flush_limit,
        epoch_coordinator=epoch_coordinator,
        retry_policy=RetryPolicy(max_attempts=int(rec.publish_retry_attempts)),
    )
    ack_runtime = FabricAckIngressService(
        transport=transport,
        ack_channel=rec.ack_channel,
        ack_channels_by_mode=mode_channels(rec.ack_channel),
        mode_filter=rec.mode_filter,
        consumer=quorum_runtime,
        ack_envelopes=ack_envelopes,
    )
    delivery_runtime = FabricCommitDeliveryService(
        transport=transport,
        tracker=delivery_tracker,
        outbox=delivery_outbox,
        delivery_ack_channel=rec.delivery_ack_channel,
        delivery_ack_channels_by_mode=mode_channels(rec.delivery_ack_channel),
        mode_filter=rec.mode_filter,
        outbox_flush_limit=rec.delivery_outbox_flush_limit,
        commit_publish_retry_attempts=int(rec.commit_publish_retry_attempts),
        dead_letters=commit_dead_letters,
        delivery_ack_envelopes=delivery_ack_envelopes,
    )
    commit_ingress = FabricCommitIngressService(
        artifact_resolver=artifact_resolver,
        delivery_runtime=delivery_runtime,
        commit_channel=str(rec.commit_channel),
        commit_channels_by_mode=mode_channels(rec.commit_channel),
        delivery_required_receipts=int(rec.delivery_required_receipts),
        publish_inline_payload=bool(rec.publish_inline_payload),
        quorum_runtime=quorum_runtime,
    )
    quorum_report_builder = FabricQuorumReportBuilder(
        quorum_runtime=quorum_runtime,
        artifact_store=artifact_store,
        publish_inline_payload=bool(rec.publish_inline_payload),
        split_mode_channels=bool(rec.split_mode_channels),
        commit_channels_by_mode=mode_channels(rec.commit_channel),
        ack_channels_by_mode=mode_channels(rec.ack_channel),
        delivery_ack_channels_by_mode=mode_channels(rec.delivery_ack_channel),
        mode_filter=rec.mode_filter,
        transport=transport if hasattr(transport, "snapshot") else None,
        delivery_outbox=delivery_outbox,
        delivery_runtime=delivery_runtime,
        delivery_required_receipts=int(rec.delivery_required_receipts),
        delivery_guarantee_mode=str(getattr(rec, "delivery_guarantee_mode", "at_least_once_idempotent")),
        delivery_required_validator_ids=list(rec.delivery_required_validator_ids or []),
        delivery_enforce_required_validator_ids=bool(rec.delivery_enforce_required_validator_ids),
        delivery_reject_on_any_reject=bool(rec.delivery_reject_on_any_reject),
        delivery_retry_interval_ms=int(rec.delivery_retry_interval_ms),
        delivery_max_attempts=int(rec.delivery_max_attempts),
        delivery_timeout_ms=int(rec.delivery_timeout_ms),
        transport_dedup_ingress_enabled=bool(getattr(rec, "transport_dedup_ingress_enabled", False)),
        replay_policy_tier=str(getattr(rec, "replay_policy_tier", "sampled")),
        replay_strict_window_size=int(getattr(rec, "replay_strict_window_size", 128)),
        handshake_profile=str(getattr(rec, "handshake_profile", "mvp")),
        epoch_coordinator=epoch_coordinator,
    )
    fabric_report_writer = FabricRuntimeReportWriter(
        out_dir=rec.out_dir,
        ack_store=ack_store,
        ack_envelopes=ack_envelopes,
        delivery_ack_envelopes=delivery_ack_envelopes,
        quorum_report_builder=quorum_report_builder,
        service=service,
        commit_dead_letters=commit_dead_letters,
        acks_retention_window=int(getattr(rec, "fabric_acks_retention_window", 0)),
        acks_compaction_budget=int(getattr(rec, "fabric_acks_compaction_budget", 0)),
        ack_envelopes_retention_window=int(getattr(rec, "fabric_ack_envelopes_retention_window", 0)),
        ack_envelopes_compaction_budget=int(getattr(rec, "fabric_ack_envelopes_compaction_budget", 0)),
        delivery_acks_retention_window=int(getattr(rec, "fabric_delivery_acks_retention_window", 0)),
        delivery_acks_compaction_budget=int(getattr(rec, "fabric_delivery_acks_compaction_budget", 0)),
        dead_letters_retention_window=int(getattr(rec, "fabric_dead_letters_retention_window", 0)),
        dead_letters_compaction_budget=int(getattr(rec, "fabric_dead_letters_compaction_budget", 0)),
        quorum_report_retention_window=int(getattr(rec, "fabric_quorum_report_retention_window", 0)),
        quorum_report_compaction_budget=int(getattr(rec, "fabric_quorum_report_compaction_budget", 0)),
    )
    runtime_bundle = FabricHandshakeRuntimeBundle(
        service=service,
        ack_runtime=ack_runtime,
        delivery_runtime=delivery_runtime,
        transport=transport,
        epoch_consensus=epoch_consensus,
    )
    return FabricHandshakeRuntimeComposition(
        commit_store=commit_store,
        commit_ref_index=commit_ref_index,
        ack_store=ack_store,
        artifact_resolver=artifact_resolver,
        ack_envelopes=ack_envelopes,
        ack_subscriptions=ack_subscriptions,
        delivery_ack_envelopes=delivery_ack_envelopes,
        delivery_ack_subscriptions=delivery_ack_subscriptions,
        delivery_pending=delivery_pending,
        delivery_receipt_coordinator=delivery_receipt_coordinator,
        delivery_tracker=delivery_tracker,
        commit_dead_letters=commit_dead_letters,
        artifact_store=artifact_store,
        delivery_outbox=delivery_outbox,
        transport=transport,
        validator=validator,
        epoch_coordinator=epoch_coordinator,
        epoch_consensus=epoch_consensus,
        quorum_runtime=quorum_runtime,
        quorum=quorum,
        validator_registry=validator_registry,
        service=service,
        ack_runtime=ack_runtime,
        delivery_runtime=delivery_runtime,
        commit_ingress=commit_ingress,
        quorum_report_builder=quorum_report_builder,
        fabric_report_writer=fabric_report_writer,
        runtime_bundle=runtime_bundle,
    )


__all__ = ["FabricHandshakeRuntimeComposition", "compose_fabric_handshake_runtime"]



