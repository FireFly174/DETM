from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Sequence

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricEnvelope, ProofAck, TrustAck
from detm_app.runtime.subscribers.fabric.attach_flow import attach_recorder as _attach_recorder_flow
from detm_app.runtime.subscribers.fabric.flow import (
    detach as _detach_flow,
    mode_channels_for_recorder as _mode_channels_flow,
    on_ack_envelope as _on_ack_envelope_flow,
    on_close as _on_close_flow,
    on_commit_packet as _on_commit_packet_flow,
    on_delivery_ack_envelope as _on_delivery_ack_envelope_flow,
    publish_runtime_snapshot as _publish_runtime_snapshot_flow,
    replay_check as _replay_check_flow,
    resolve_ack as _resolve_ack_flow,
    resolve_commit as _resolve_commit_flow,
    runtime_snapshot as _runtime_snapshot_flow,
    start_bundle_for_recorder as _start_bundle_for_recorder_flow,
    tick_delivery_pending as _tick_delivery_pending_flow,
    write_ack as _write_ack_flow,
)
from detm_app.runtime.subscribers.fabric.model import FabricHandshakeRecorderModel


class FabricHandshakeRecorder(FabricHandshakeRecorderModel):
    """Local fabric handshake subscriber (`commit_packet -> proof/trust ack`).

    ARCH-MARKERS:
    - LAYER_BAND: L5
    - ABSTRACT_DISTANCE: 1 (network transport + distributed validator still pending)
    - OOP_TECH_DEBT: quorum/retry policy and durable relay adapters
    """

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
        kwargs = {
            key: value
            for key, value in locals().items()
            if key not in {"cls", "bus", "out_dir", "__class__"}
        }
        return _attach_recorder_flow(
            cls=cls,
            bus=bus,
            out_dir=out_dir,
            **kwargs,
        )

    def _mode_channels(self, base_channel: str) -> Dict[str, str] | None:
        return _mode_channels_flow(self, base_channel)

    def _start_runtime_bundle(self) -> None:
        _start_bundle_for_recorder_flow(self)

    def on_commit_packet(
        self,
        *,
        packet: CommitPacket,
        payload_ref: str,
        mode: str,
        trace_ref: str | None = None,
        **_rest: Any,
    ) -> None:
        _on_commit_packet_flow(
            self,
            packet=packet,
            payload_ref=payload_ref,
            mode=mode,
            trace_ref=trace_ref,
        )

    def _tick_delivery_pending(self) -> None:
        _tick_delivery_pending_flow(self)

    def _runtime_snapshot(self) -> Dict[str, Any]:
        return _runtime_snapshot_flow(self)

    def _publish_runtime_snapshot(self) -> None:
        _publish_runtime_snapshot_flow(self)

    def _resolve_commit(self, payload_ref: str) -> CommitPacket | None:
        return _resolve_commit_flow(self, payload_ref)

    def _replay_check(self, packet: CommitPacket) -> tuple[bool, str | None]:
        return _replay_check_flow(self, packet)

    def _write_ack(self, ack: ProofAck | TrustAck) -> str:
        return _write_ack_flow(self, ack)

    def _resolve_ack(self, payload_ref: str) -> ProofAck | TrustAck | None:
        return _resolve_ack_flow(self, payload_ref)

    def _on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        _on_ack_envelope_flow(self, envelope)

    def _on_delivery_ack_envelope(self, envelope: FabricEnvelope) -> None:
        _on_delivery_ack_envelope_flow(self, envelope)

    def on_close(self, **_rest: Any) -> None:
        _on_close_flow(self)

    def detach(self) -> None:
        _detach_flow(self)
