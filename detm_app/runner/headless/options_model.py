"""Option models for headless CLI main()."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HeadlessMainOptions:
    seed0: int
    seed: int
    steps: int
    steps_mode: str
    out_root: Path
    symbol_ids: list[str]
    viz_enabled: bool
    viz_transport_name: str
    viz_host: str
    viz_port: int
    viz_connect: bool
    viz_keep_open: bool
    viz_every_steps: int
    record_fields: bool
    fields_every_steps: int
    invariant_streams: list[str] | None
    fabric_handshake: bool
    fabric_required_proof_accepts: int
    fabric_required_trust_accepts: int
    fabric_required_unique_proof_validators: int
    fabric_required_unique_trust_validators: int
    fabric_required_validator_ids: list[str] | None
    fabric_handshake_profile: str
    fabric_enforce_required_validator_ids: bool
    fabric_enforce_active_validator_membership: bool
    fabric_enforce_ack_sender_validator_match: bool
    fabric_enforce_ack_auth_key_id_binding: bool
    fabric_validator_auth_key_ids: list[str] | None
    fabric_enforce_ack_transport_identity_binding: bool
    fabric_validator_transport_identities: list[str] | None
    fabric_reject_on_any_reject: bool
    fabric_retry_attempts: int
    fabric_commit_retry_attempts: int
    fabric_pending_timeout_ms: int | None
    fabric_transport: str
    fabric_transport_host: str
    fabric_transport_port: int
    fabric_transport_connect: bool
    fabric_transport_keep_open: bool
    fabric_transport_backpressure_max_pending: int | None
    fabric_transport_backpressure_policy: str
    fabric_transport_backpressure_block_timeout_ms: int
    fabric_transport_dedup_ingress_enabled: bool
    fabric_transport_dedup_ttl_ms: int
    fabric_transport_dedup_max_entries: int
    fabric_transport_auth_enabled: bool
    fabric_transport_auth_key: str | None
    fabric_transport_auth_key_id: str | None
    fabric_transport_tls_enabled: bool
    fabric_transport_tls_server_hostname: str | None
    fabric_transport_tls_ca_file: str | None
    fabric_transport_tls_cert_file: str | None
    fabric_transport_tls_key_file: str | None
    fabric_transport_tls_require_client_cert: bool
    fabric_transport_tls_client_ca_file: str | None
    fabric_transport_tls_insecure_skip_verify: bool
    fabric_transport_tls_identity_source: str
    fabric_transport_tls_identity_fallback_to_fingerprint: bool
    fabric_artifact_dir: str | None
    fabric_inline_bridge: bool
    fabric_replay_sample_stride: int
    fabric_replay_policy_tier: str
    fabric_replay_strict_window_size: int
    fabric_validator_coordination_state_path: str | None
    fabric_validator_coordination_replica_state_paths: list[str] | None
    fabric_validator_coordination_replica_read_quorum: int | None
    fabric_validator_coordination_replica_write_quorum: int | None
    fabric_epoch_state_path: str | None
    fabric_epoch_replica_state_paths: list[str] | None
    fabric_epoch_replica_read_quorum: int | None
    fabric_epoch_replica_write_quorum: int | None
    fabric_epoch_lock_timeout_ms: int
    fabric_epoch_lock_poll_ms: int
    fabric_epoch_lock_stale_ms: int | None
    fabric_epoch_consensus_enabled: bool
    fabric_epoch_consensus_required_total_accepts: int
    fabric_epoch_consensus_timeout_ms: int
    fabric_epoch_consensus_max_attempts: int
    fabric_epoch_consensus_reject_on_any_reject: bool
    fabric_epoch_consensus_channel: str
    fabric_split_mode_channels: bool
    fabric_delivery_required_receipts: int
    fabric_delivery_guarantee_mode: str
    fabric_delivery_required_validator_ids: list[str] | None
    fabric_delivery_enforce_required_validator_ids: bool
    fabric_delivery_reject_on_any_reject: bool
    fabric_delivery_retry_interval_ms: int
    fabric_delivery_max_attempts: int
    fabric_delivery_timeout_ms: int
    fabric_delivery_tracking_state_path: str | None
    fabric_delivery_ack_channel: str
    fabric_delivery_emit_ack: bool
    fabric_delivery_outbox_path: str | None
    fabric_delivery_outbox_max_entries: int | None
    fabric_delivery_outbox_flush_limit: int | None
    fabric_delivery_outbox_drop_policy: str


__all__ = ["HeadlessMainOptions"]
