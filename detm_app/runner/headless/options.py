"""Option resolution helpers for headless CLI main()."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from detm_app.runner.headless.helpers import (
    as_list,
    default_out_dir,
    flatten_list_args,
    normalize_steps_mode,
    resolve_symbols,
)


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


def resolve_headless_main_options(*, args: Any, runner_defaults: dict[str, Any]) -> HeadlessMainOptions:
    seed0 = int(args.seed0) if args.seed0 is not None else int(runner_defaults.get("seed0", 0))
    seed = int(args.seed) if args.seed is not None else int(runner_defaults.get("seed", 1))
    steps = int(args.steps) if args.steps is not None else int(runner_defaults.get("steps", 4))
    steps_mode = normalize_steps_mode(
        args.steps_mode if args.steps_mode is not None else runner_defaults.get("steps_mode"),
        default="total",
    )
    out_root = default_out_dir(args.out if args.out is not None else runner_defaults.get("out"))

    symbols_cfg = as_list(runner_defaults.get("symbols"))
    symbol_ids = resolve_symbols(args.symbols if args.symbols is not None else symbols_cfg)

    viz_enabled = args.viz if args.viz is not None else bool(runner_defaults.get("viz", False))
    viz_transport_name = (
        str(args.viz_transport) if args.viz_transport is not None else str(runner_defaults.get("viz_transport", "tcp"))
    )
    viz_host = str(args.viz_host) if args.viz_host is not None else str(runner_defaults.get("viz_host", "127.0.0.1"))
    viz_port = int(args.viz_port) if args.viz_port is not None else int(runner_defaults.get("viz_port", 0))
    viz_connect = args.viz_connect if args.viz_connect is not None else bool(runner_defaults.get("viz_connect", False))
    viz_keep_open = (
        args.viz_keep_open if args.viz_keep_open is not None else bool(runner_defaults.get("viz_keep_open", False))
    )
    viz_every_steps = (
        int(args.viz_every_steps)
        if args.viz_every_steps is not None
        else int(runner_defaults.get("viz_every_steps", 1))
    )

    record_fields = (
        args.record_fields if args.record_fields is not None else bool(runner_defaults.get("record_fields", False))
    )
    fields_every_steps = (
        int(args.fields_every_steps)
        if args.fields_every_steps is not None
        else int(runner_defaults.get("fields_every_steps", 1))
    )

    invariant_streams = None
    if args.invariant_stream is not None:
        invariant_streams = list(args.invariant_stream)
    else:
        inv = runner_defaults.get("invariant_streams")
        invariant_streams = as_list(inv)

    fabric_handshake = (
        args.fabric_handshake
        if args.fabric_handshake is not None
        else bool(runner_defaults.get("fabric_handshake", False))
    )
    fabric_required_proof_accepts = (
        int(args.fabric_proof_quorum)
        if args.fabric_proof_quorum is not None
        else int(runner_defaults.get("fabric_required_proof_accepts", 1))
    )
    fabric_required_trust_accepts = (
        int(args.fabric_trust_quorum)
        if args.fabric_trust_quorum is not None
        else int(runner_defaults.get("fabric_required_trust_accepts", 1))
    )
    fabric_required_unique_proof_validators = (
        int(args.fabric_unique_proof_validators)
        if args.fabric_unique_proof_validators is not None
        else int(runner_defaults.get("fabric_required_unique_proof_validators", 1))
    )
    fabric_required_unique_trust_validators = (
        int(args.fabric_unique_trust_validators)
        if args.fabric_unique_trust_validators is not None
        else int(runner_defaults.get("fabric_required_unique_trust_validators", 1))
    )
    if args.fabric_validator_set is not None:
        fabric_required_validator_ids = as_list(args.fabric_validator_set)
    else:
        fabric_required_validator_ids = as_list(runner_defaults.get("fabric_required_validator_ids"))
    fabric_handshake_profile = (
        str(args.fabric_handshake_profile)
        if args.fabric_handshake_profile is not None
        else str(runner_defaults.get("fabric_handshake_profile", "mvp"))
    )
    fabric_enforce_required_validator_ids = (
        bool(args.fabric_enforce_validator_set)
        if args.fabric_enforce_validator_set is not None
        else bool(runner_defaults.get("fabric_enforce_required_validator_ids", False))
    )
    fabric_enforce_active_validator_membership = (
        bool(args.fabric_enforce_active_validator_membership)
        if args.fabric_enforce_active_validator_membership is not None
        else bool(runner_defaults.get("fabric_enforce_active_validator_membership", False))
    )
    fabric_enforce_ack_sender_validator_match = (
        bool(args.fabric_enforce_ack_sender_validator_match)
        if args.fabric_enforce_ack_sender_validator_match is not None
        else bool(runner_defaults.get("fabric_enforce_ack_sender_validator_match", False))
    )
    fabric_enforce_ack_auth_key_id_binding = (
        bool(args.fabric_enforce_ack_auth_key_id_binding)
        if args.fabric_enforce_ack_auth_key_id_binding is not None
        else bool(runner_defaults.get("fabric_enforce_ack_auth_key_id_binding", False))
    )
    if args.fabric_validator_auth_key_id is not None:
        fabric_validator_auth_key_ids = flatten_list_args(list(args.fabric_validator_auth_key_id))
    else:
        fabric_validator_auth_key_ids = as_list(runner_defaults.get("fabric_validator_auth_key_ids"))
    fabric_enforce_ack_transport_identity_binding = (
        bool(args.fabric_enforce_ack_transport_identity_binding)
        if args.fabric_enforce_ack_transport_identity_binding is not None
        else bool(runner_defaults.get("fabric_enforce_ack_transport_identity_binding", False))
    )
    if args.fabric_validator_transport_identity is not None:
        fabric_validator_transport_identities = flatten_list_args(list(args.fabric_validator_transport_identity))
    else:
        fabric_validator_transport_identities = as_list(runner_defaults.get("fabric_validator_transport_identities"))
    fabric_reject_on_any_reject = (
        bool(args.fabric_reject_on_any_reject)
        if args.fabric_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_reject_on_any_reject", False))
    )
    fabric_retry_attempts = (
        int(args.fabric_retry_attempts)
        if args.fabric_retry_attempts is not None
        else int(runner_defaults.get("fabric_retry_attempts", 2))
    )
    fabric_commit_retry_attempts = (
        int(args.fabric_commit_retry_attempts)
        if args.fabric_commit_retry_attempts is not None
        else int(runner_defaults.get("fabric_commit_retry_attempts", 2))
    )
    fabric_pending_timeout_ms = (
        int(args.fabric_pending_timeout_ms)
        if args.fabric_pending_timeout_ms is not None
        else (
            None
            if runner_defaults.get("fabric_pending_timeout_ms") is None
            else int(runner_defaults.get("fabric_pending_timeout_ms"))
        )
    )
    fabric_transport = (
        str(args.fabric_transport)
        if args.fabric_transport is not None
        else str(runner_defaults.get("fabric_transport", "memory"))
    )
    fabric_transport_host = (
        str(args.fabric_transport_host)
        if args.fabric_transport_host is not None
        else str(runner_defaults.get("fabric_transport_host", "127.0.0.1"))
    )
    fabric_transport_port = (
        int(args.fabric_transport_port)
        if args.fabric_transport_port is not None
        else int(runner_defaults.get("fabric_transport_port", 0))
    )
    fabric_transport_connect = (
        bool(args.fabric_transport_connect)
        if args.fabric_transport_connect is not None
        else bool(runner_defaults.get("fabric_transport_connect", False))
    )
    fabric_transport_keep_open = (
        bool(args.fabric_transport_keep_open)
        if args.fabric_transport_keep_open is not None
        else bool(runner_defaults.get("fabric_transport_keep_open", False))
    )
    fabric_transport_backpressure_max_pending = (
        int(args.fabric_transport_backpressure_max_pending)
        if args.fabric_transport_backpressure_max_pending is not None
        else (
            None
            if runner_defaults.get("fabric_transport_backpressure_max_pending") is None
            else int(runner_defaults.get("fabric_transport_backpressure_max_pending"))
        )
    )
    fabric_transport_backpressure_policy = (
        str(args.fabric_transport_backpressure_policy)
        if args.fabric_transport_backpressure_policy is not None
        else str(runner_defaults.get("fabric_transport_backpressure_policy", "block"))
    )
    fabric_transport_backpressure_block_timeout_ms = (
        int(args.fabric_transport_backpressure_block_timeout_ms)
        if args.fabric_transport_backpressure_block_timeout_ms is not None
        else int(runner_defaults.get("fabric_transport_backpressure_block_timeout_ms", 200))
    )
    fabric_transport_dedup_ingress_enabled = (
        bool(args.fabric_transport_dedup_ingress_enabled)
        if args.fabric_transport_dedup_ingress_enabled is not None
        else bool(runner_defaults.get("fabric_transport_dedup_ingress_enabled", False))
    )
    fabric_transport_dedup_ttl_ms = (
        int(args.fabric_transport_dedup_ttl_ms)
        if args.fabric_transport_dedup_ttl_ms is not None
        else int(runner_defaults.get("fabric_transport_dedup_ttl_ms", 30000))
    )
    fabric_transport_dedup_max_entries = (
        int(args.fabric_transport_dedup_max_entries)
        if args.fabric_transport_dedup_max_entries is not None
        else int(runner_defaults.get("fabric_transport_dedup_max_entries", 10000))
    )
    fabric_transport_auth_enabled = (
        bool(args.fabric_transport_auth_enabled)
        if args.fabric_transport_auth_enabled is not None
        else bool(runner_defaults.get("fabric_transport_auth_enabled", False))
    )
    fabric_transport_auth_key = (
        str(args.fabric_transport_auth_key)
        if args.fabric_transport_auth_key is not None
        else (
            None
            if runner_defaults.get("fabric_transport_auth_key") is None
            else str(runner_defaults.get("fabric_transport_auth_key"))
        )
    )
    fabric_transport_auth_key_id = (
        str(args.fabric_transport_auth_key_id)
        if args.fabric_transport_auth_key_id is not None
        else (
            None
            if runner_defaults.get("fabric_transport_auth_key_id") is None
            else str(runner_defaults.get("fabric_transport_auth_key_id"))
        )
    )
    fabric_transport_tls_enabled = (
        bool(args.fabric_transport_tls_enabled)
        if args.fabric_transport_tls_enabled is not None
        else bool(runner_defaults.get("fabric_transport_tls_enabled", False))
    )
    fabric_transport_tls_server_hostname = (
        str(args.fabric_transport_tls_server_hostname)
        if args.fabric_transport_tls_server_hostname is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_server_hostname") is None
            else str(runner_defaults.get("fabric_transport_tls_server_hostname"))
        )
    )
    fabric_transport_tls_ca_file = (
        str(args.fabric_transport_tls_ca_file)
        if args.fabric_transport_tls_ca_file is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_ca_file") is None
            else str(runner_defaults.get("fabric_transport_tls_ca_file"))
        )
    )
    fabric_transport_tls_cert_file = (
        str(args.fabric_transport_tls_cert_file)
        if args.fabric_transport_tls_cert_file is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_cert_file") is None
            else str(runner_defaults.get("fabric_transport_tls_cert_file"))
        )
    )
    fabric_transport_tls_key_file = (
        str(args.fabric_transport_tls_key_file)
        if args.fabric_transport_tls_key_file is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_key_file") is None
            else str(runner_defaults.get("fabric_transport_tls_key_file"))
        )
    )
    fabric_transport_tls_require_client_cert = (
        bool(args.fabric_transport_tls_require_client_cert)
        if args.fabric_transport_tls_require_client_cert is not None
        else bool(runner_defaults.get("fabric_transport_tls_require_client_cert", False))
    )
    fabric_transport_tls_client_ca_file = (
        str(args.fabric_transport_tls_client_ca_file)
        if args.fabric_transport_tls_client_ca_file is not None
        else (
            None
            if runner_defaults.get("fabric_transport_tls_client_ca_file") is None
            else str(runner_defaults.get("fabric_transport_tls_client_ca_file"))
        )
    )
    fabric_transport_tls_insecure_skip_verify = (
        bool(args.fabric_transport_tls_insecure_skip_verify)
        if args.fabric_transport_tls_insecure_skip_verify is not None
        else bool(runner_defaults.get("fabric_transport_tls_insecure_skip_verify", False))
    )
    fabric_transport_tls_identity_source = (
        str(args.fabric_transport_tls_identity_source)
        if args.fabric_transport_tls_identity_source is not None
        else str(runner_defaults.get("fabric_transport_tls_identity_source", "auto"))
    )
    fabric_transport_tls_identity_fallback_to_fingerprint = (
        bool(args.fabric_transport_tls_identity_fallback_to_fingerprint)
        if args.fabric_transport_tls_identity_fallback_to_fingerprint is not None
        else bool(runner_defaults.get("fabric_transport_tls_identity_fallback_to_fingerprint", False))
    )
    fabric_artifact_dir = (
        str(args.fabric_artifact_dir)
        if args.fabric_artifact_dir is not None
        else (
            None
            if runner_defaults.get("fabric_artifact_dir") is None
            else str(runner_defaults.get("fabric_artifact_dir"))
        )
    )
    fabric_inline_bridge = (
        bool(args.fabric_inline_bridge)
        if args.fabric_inline_bridge is not None
        else bool(runner_defaults.get("fabric_inline_bridge", True))
    )
    fabric_replay_sample_stride = (
        int(args.fabric_replay_sample_stride)
        if args.fabric_replay_sample_stride is not None
        else int(runner_defaults.get("fabric_replay_sample_stride", 0))
    )
    fabric_replay_policy_tier = (
        str(args.fabric_replay_policy_tier)
        if args.fabric_replay_policy_tier is not None
        else str(runner_defaults.get("fabric_replay_policy_tier", "sampled"))
    )
    fabric_replay_strict_window_size = (
        int(args.fabric_replay_strict_window_size)
        if args.fabric_replay_strict_window_size is not None
        else int(runner_defaults.get("fabric_replay_strict_window_size", 128))
    )
    fabric_validator_coordination_state_path = (
        str(args.fabric_validator_coordination_state_path)
        if args.fabric_validator_coordination_state_path is not None
        else (
            None
            if runner_defaults.get("fabric_validator_coordination_state_path") is None
            else str(runner_defaults.get("fabric_validator_coordination_state_path"))
        )
    )
    if args.fabric_validator_coordination_replica_state is not None:
        fabric_validator_coordination_replica_state_paths = flatten_list_args(
            list(args.fabric_validator_coordination_replica_state)
        )
    else:
        fabric_validator_coordination_replica_state_paths = as_list(
            runner_defaults.get("fabric_validator_coordination_replica_state_paths")
        )
    fabric_validator_coordination_replica_read_quorum = (
        int(args.fabric_validator_coordination_read_quorum)
        if args.fabric_validator_coordination_read_quorum is not None
        else (
            None
            if runner_defaults.get("fabric_validator_coordination_replica_read_quorum") is None
            else int(runner_defaults.get("fabric_validator_coordination_replica_read_quorum"))
        )
    )
    fabric_validator_coordination_replica_write_quorum = (
        int(args.fabric_validator_coordination_write_quorum)
        if args.fabric_validator_coordination_write_quorum is not None
        else (
            None
            if runner_defaults.get("fabric_validator_coordination_replica_write_quorum") is None
            else int(runner_defaults.get("fabric_validator_coordination_replica_write_quorum"))
        )
    )
    fabric_epoch_state_path = (
        str(args.fabric_epoch_state_path)
        if args.fabric_epoch_state_path is not None
        else (
            None
            if runner_defaults.get("fabric_epoch_state_path") is None
            else str(runner_defaults.get("fabric_epoch_state_path"))
        )
    )
    if args.fabric_epoch_replica_state is not None:
        fabric_epoch_replica_state_paths = flatten_list_args(list(args.fabric_epoch_replica_state))
    else:
        fabric_epoch_replica_state_paths = as_list(runner_defaults.get("fabric_epoch_replica_state_paths"))
    fabric_epoch_replica_read_quorum = (
        int(args.fabric_epoch_read_quorum)
        if args.fabric_epoch_read_quorum is not None
        else (
            None
            if runner_defaults.get("fabric_epoch_replica_read_quorum") is None
            else int(runner_defaults.get("fabric_epoch_replica_read_quorum"))
        )
    )
    fabric_epoch_replica_write_quorum = (
        int(args.fabric_epoch_write_quorum)
        if args.fabric_epoch_write_quorum is not None
        else (
            None
            if runner_defaults.get("fabric_epoch_replica_write_quorum") is None
            else int(runner_defaults.get("fabric_epoch_replica_write_quorum"))
        )
    )
    fabric_epoch_lock_timeout_ms = (
        int(args.fabric_epoch_lock_timeout_ms)
        if args.fabric_epoch_lock_timeout_ms is not None
        else int(runner_defaults.get("fabric_epoch_lock_timeout_ms", 5000))
    )
    fabric_epoch_lock_poll_ms = (
        int(args.fabric_epoch_lock_poll_ms)
        if args.fabric_epoch_lock_poll_ms is not None
        else int(runner_defaults.get("fabric_epoch_lock_poll_ms", 10))
    )
    raw_stale = (
        args.fabric_epoch_lock_stale_ms
        if args.fabric_epoch_lock_stale_ms is not None
        else runner_defaults.get("fabric_epoch_lock_stale_ms", 30000)
    )
    fabric_epoch_lock_stale_ms = None if raw_stale is None or int(raw_stale) <= 0 else int(raw_stale)
    fabric_epoch_consensus_enabled = (
        bool(args.fabric_epoch_consensus_enabled)
        if args.fabric_epoch_consensus_enabled is not None
        else bool(runner_defaults.get("fabric_epoch_consensus_enabled", False))
    )
    fabric_epoch_consensus_required_total_accepts = (
        int(args.fabric_epoch_consensus_required_total_accepts)
        if args.fabric_epoch_consensus_required_total_accepts is not None
        else int(runner_defaults.get("fabric_epoch_consensus_required_total_accepts", 1))
    )
    fabric_epoch_consensus_timeout_ms = (
        int(args.fabric_epoch_consensus_timeout_ms)
        if args.fabric_epoch_consensus_timeout_ms is not None
        else int(runner_defaults.get("fabric_epoch_consensus_timeout_ms", 200))
    )
    fabric_epoch_consensus_max_attempts = (
        int(args.fabric_epoch_consensus_max_attempts)
        if args.fabric_epoch_consensus_max_attempts is not None
        else int(runner_defaults.get("fabric_epoch_consensus_max_attempts", 1))
    )
    fabric_epoch_consensus_reject_on_any_reject = (
        bool(args.fabric_epoch_consensus_reject_on_any_reject)
        if args.fabric_epoch_consensus_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_epoch_consensus_reject_on_any_reject", False))
    )
    fabric_epoch_consensus_channel = (
        str(args.fabric_epoch_consensus_channel)
        if args.fabric_epoch_consensus_channel is not None
        else str(runner_defaults.get("fabric_epoch_consensus_channel", "fabric.epoch"))
    )
    fabric_split_mode_channels = (
        bool(args.fabric_split_mode_channels)
        if args.fabric_split_mode_channels is not None
        else bool(runner_defaults.get("fabric_split_mode_channels", False))
    )
    fabric_delivery_required_receipts = (
        int(args.fabric_delivery_required_receipts)
        if args.fabric_delivery_required_receipts is not None
        else int(runner_defaults.get("fabric_delivery_required_receipts", 0))
    )
    fabric_delivery_guarantee_mode = (
        str(args.fabric_delivery_guarantee_mode)
        if args.fabric_delivery_guarantee_mode is not None
        else str(runner_defaults.get("fabric_delivery_guarantee_mode", "at_least_once_idempotent"))
    )
    if args.fabric_delivery_validator_set is not None:
        fabric_delivery_required_validator_ids = as_list(args.fabric_delivery_validator_set)
    else:
        fabric_delivery_required_validator_ids = as_list(runner_defaults.get("fabric_delivery_required_validator_ids"))
    fabric_delivery_enforce_required_validator_ids = (
        bool(args.fabric_delivery_enforce_validator_set)
        if args.fabric_delivery_enforce_validator_set is not None
        else bool(runner_defaults.get("fabric_delivery_enforce_required_validator_ids", False))
    )
    fabric_delivery_reject_on_any_reject = (
        bool(args.fabric_delivery_reject_on_any_reject)
        if args.fabric_delivery_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_delivery_reject_on_any_reject", False))
    )
    fabric_delivery_retry_interval_ms = (
        int(args.fabric_delivery_retry_interval_ms)
        if args.fabric_delivery_retry_interval_ms is not None
        else int(runner_defaults.get("fabric_delivery_retry_interval_ms", 100))
    )
    fabric_delivery_max_attempts = (
        int(args.fabric_delivery_max_attempts)
        if args.fabric_delivery_max_attempts is not None
        else int(runner_defaults.get("fabric_delivery_max_attempts", 3))
    )
    fabric_delivery_timeout_ms = (
        int(args.fabric_delivery_timeout_ms)
        if args.fabric_delivery_timeout_ms is not None
        else int(runner_defaults.get("fabric_delivery_timeout_ms", 500))
    )
    fabric_delivery_tracking_state_path = (
        str(args.fabric_delivery_tracking_state_path)
        if args.fabric_delivery_tracking_state_path is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_tracking_state_path") is None
            else str(runner_defaults.get("fabric_delivery_tracking_state_path"))
        )
    )
    fabric_delivery_ack_channel = (
        str(args.fabric_delivery_ack_channel)
        if args.fabric_delivery_ack_channel is not None
        else str(runner_defaults.get("fabric_delivery_ack_channel", "fabric.delivery.ack"))
    )
    fabric_delivery_emit_ack = (
        bool(args.fabric_delivery_emit_ack)
        if args.fabric_delivery_emit_ack is not None
        else bool(runner_defaults.get("fabric_delivery_emit_ack", True))
    )
    fabric_delivery_outbox_path = (
        str(args.fabric_delivery_outbox_path)
        if args.fabric_delivery_outbox_path is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_outbox_path") is None
            else str(runner_defaults.get("fabric_delivery_outbox_path"))
        )
    )
    fabric_delivery_outbox_max_entries = (
        int(args.fabric_delivery_outbox_max_entries)
        if args.fabric_delivery_outbox_max_entries is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_outbox_max_entries") is None
            else int(runner_defaults.get("fabric_delivery_outbox_max_entries"))
        )
    )
    fabric_delivery_outbox_flush_limit = (
        int(args.fabric_delivery_outbox_flush_limit)
        if args.fabric_delivery_outbox_flush_limit is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_outbox_flush_limit") is None
            else int(runner_defaults.get("fabric_delivery_outbox_flush_limit"))
        )
    )
    fabric_delivery_outbox_drop_policy = (
        str(args.fabric_delivery_outbox_drop_policy)
        if args.fabric_delivery_outbox_drop_policy is not None
        else str(runner_defaults.get("fabric_delivery_outbox_drop_policy", "audit_first"))
    )

    return HeadlessMainOptions(
        seed0=seed0,
        seed=seed,
        steps=steps,
        steps_mode=steps_mode,
        out_root=out_root,
        symbol_ids=symbol_ids,
        viz_enabled=bool(viz_enabled),
        viz_transport_name=viz_transport_name,
        viz_host=viz_host,
        viz_port=viz_port,
        viz_connect=bool(viz_connect),
        viz_keep_open=bool(viz_keep_open),
        viz_every_steps=viz_every_steps,
        record_fields=bool(record_fields),
        fields_every_steps=fields_every_steps,
        invariant_streams=invariant_streams,
        fabric_handshake=bool(fabric_handshake),
        fabric_required_proof_accepts=fabric_required_proof_accepts,
        fabric_required_trust_accepts=fabric_required_trust_accepts,
        fabric_required_unique_proof_validators=fabric_required_unique_proof_validators,
        fabric_required_unique_trust_validators=fabric_required_unique_trust_validators,
        fabric_required_validator_ids=fabric_required_validator_ids,
        fabric_handshake_profile=fabric_handshake_profile,
        fabric_enforce_required_validator_ids=bool(fabric_enforce_required_validator_ids),
        fabric_enforce_active_validator_membership=bool(fabric_enforce_active_validator_membership),
        fabric_enforce_ack_sender_validator_match=bool(fabric_enforce_ack_sender_validator_match),
        fabric_enforce_ack_auth_key_id_binding=bool(fabric_enforce_ack_auth_key_id_binding),
        fabric_validator_auth_key_ids=fabric_validator_auth_key_ids,
        fabric_enforce_ack_transport_identity_binding=bool(fabric_enforce_ack_transport_identity_binding),
        fabric_validator_transport_identities=fabric_validator_transport_identities,
        fabric_reject_on_any_reject=bool(fabric_reject_on_any_reject),
        fabric_retry_attempts=fabric_retry_attempts,
        fabric_commit_retry_attempts=fabric_commit_retry_attempts,
        fabric_pending_timeout_ms=fabric_pending_timeout_ms,
        fabric_transport=fabric_transport,
        fabric_transport_host=fabric_transport_host,
        fabric_transport_port=fabric_transport_port,
        fabric_transport_connect=bool(fabric_transport_connect),
        fabric_transport_keep_open=bool(fabric_transport_keep_open),
        fabric_transport_backpressure_max_pending=fabric_transport_backpressure_max_pending,
        fabric_transport_backpressure_policy=fabric_transport_backpressure_policy,
        fabric_transport_backpressure_block_timeout_ms=fabric_transport_backpressure_block_timeout_ms,
        fabric_transport_dedup_ingress_enabled=bool(fabric_transport_dedup_ingress_enabled),
        fabric_transport_dedup_ttl_ms=fabric_transport_dedup_ttl_ms,
        fabric_transport_dedup_max_entries=fabric_transport_dedup_max_entries,
        fabric_transport_auth_enabled=bool(fabric_transport_auth_enabled),
        fabric_transport_auth_key=fabric_transport_auth_key,
        fabric_transport_auth_key_id=fabric_transport_auth_key_id,
        fabric_transport_tls_enabled=bool(fabric_transport_tls_enabled),
        fabric_transport_tls_server_hostname=fabric_transport_tls_server_hostname,
        fabric_transport_tls_ca_file=fabric_transport_tls_ca_file,
        fabric_transport_tls_cert_file=fabric_transport_tls_cert_file,
        fabric_transport_tls_key_file=fabric_transport_tls_key_file,
        fabric_transport_tls_require_client_cert=bool(fabric_transport_tls_require_client_cert),
        fabric_transport_tls_client_ca_file=fabric_transport_tls_client_ca_file,
        fabric_transport_tls_insecure_skip_verify=bool(fabric_transport_tls_insecure_skip_verify),
        fabric_transport_tls_identity_source=fabric_transport_tls_identity_source,
        fabric_transport_tls_identity_fallback_to_fingerprint=bool(
            fabric_transport_tls_identity_fallback_to_fingerprint
        ),
        fabric_artifact_dir=fabric_artifact_dir,
        fabric_inline_bridge=bool(fabric_inline_bridge),
        fabric_replay_sample_stride=fabric_replay_sample_stride,
        fabric_replay_policy_tier=fabric_replay_policy_tier,
        fabric_replay_strict_window_size=fabric_replay_strict_window_size,
        fabric_validator_coordination_state_path=fabric_validator_coordination_state_path,
        fabric_validator_coordination_replica_state_paths=fabric_validator_coordination_replica_state_paths,
        fabric_validator_coordination_replica_read_quorum=fabric_validator_coordination_replica_read_quorum,
        fabric_validator_coordination_replica_write_quorum=fabric_validator_coordination_replica_write_quorum,
        fabric_epoch_state_path=fabric_epoch_state_path,
        fabric_epoch_replica_state_paths=fabric_epoch_replica_state_paths,
        fabric_epoch_replica_read_quorum=fabric_epoch_replica_read_quorum,
        fabric_epoch_replica_write_quorum=fabric_epoch_replica_write_quorum,
        fabric_epoch_lock_timeout_ms=fabric_epoch_lock_timeout_ms,
        fabric_epoch_lock_poll_ms=fabric_epoch_lock_poll_ms,
        fabric_epoch_lock_stale_ms=fabric_epoch_lock_stale_ms,
        fabric_epoch_consensus_enabled=bool(fabric_epoch_consensus_enabled),
        fabric_epoch_consensus_required_total_accepts=fabric_epoch_consensus_required_total_accepts,
        fabric_epoch_consensus_timeout_ms=fabric_epoch_consensus_timeout_ms,
        fabric_epoch_consensus_max_attempts=fabric_epoch_consensus_max_attempts,
        fabric_epoch_consensus_reject_on_any_reject=bool(fabric_epoch_consensus_reject_on_any_reject),
        fabric_epoch_consensus_channel=fabric_epoch_consensus_channel,
        fabric_split_mode_channels=bool(fabric_split_mode_channels),
        fabric_delivery_required_receipts=fabric_delivery_required_receipts,
        fabric_delivery_guarantee_mode=fabric_delivery_guarantee_mode,
        fabric_delivery_required_validator_ids=fabric_delivery_required_validator_ids,
        fabric_delivery_enforce_required_validator_ids=bool(fabric_delivery_enforce_required_validator_ids),
        fabric_delivery_reject_on_any_reject=bool(fabric_delivery_reject_on_any_reject),
        fabric_delivery_retry_interval_ms=fabric_delivery_retry_interval_ms,
        fabric_delivery_max_attempts=fabric_delivery_max_attempts,
        fabric_delivery_timeout_ms=fabric_delivery_timeout_ms,
        fabric_delivery_tracking_state_path=fabric_delivery_tracking_state_path,
        fabric_delivery_ack_channel=fabric_delivery_ack_channel,
        fabric_delivery_emit_ack=bool(fabric_delivery_emit_ack),
        fabric_delivery_outbox_path=fabric_delivery_outbox_path,
        fabric_delivery_outbox_max_entries=fabric_delivery_outbox_max_entries,
        fabric_delivery_outbox_flush_limit=fabric_delivery_outbox_flush_limit,
        fabric_delivery_outbox_drop_policy=fabric_delivery_outbox_drop_policy,
    )


__all__ = ["HeadlessMainOptions", "resolve_headless_main_options"]
