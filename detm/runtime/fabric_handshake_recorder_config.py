"""Normalization helpers for FabricHandshakeRecorder.attach(...) settings."""

from __future__ import annotations

from typing import Any, Sequence

from detm.runtime.fabric_delivery import OUTBOX_DROP_POLICIES
from detm.runtime.fabric_transport import BACKPRESSURE_POLICIES

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (attach normalization extracted from subscriber orchestration)
# - OOP_TECH_DEBT: schema-driven config validation and versioned runtime presets


def normalize_fabric_handshake_recorder_attach_kwargs(
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
) -> dict[str, Any]:
    return {
        "node_id": str(node_id),
        "commit_channel": str(commit_channel),
        "ack_channel": str(ack_channel),
        "mode_filter": None if mode_filter is None else str(mode_filter),
        "split_mode_channels": bool(split_mode_channels),
        "required_proof_accepts": max(1, int(required_proof_accepts)),
        "required_trust_accepts": max(1, int(required_trust_accepts)),
        "required_unique_proof_validators": max(1, int(required_unique_proof_validators)),
        "required_unique_trust_validators": max(1, int(required_unique_trust_validators)),
        "required_validator_ids": [str(v).strip() for v in list(required_validator_ids or []) if str(v).strip()],
        "enforce_required_validator_ids": bool(enforce_required_validator_ids),
        "reject_on_any_reject": bool(reject_on_any_reject),
        "publish_retry_attempts": max(1, int(publish_retry_attempts)),
        "commit_publish_retry_attempts": max(1, int(commit_publish_retry_attempts)),
        "delivery_required_receipts": max(0, int(delivery_required_receipts)),
        "delivery_required_validator_ids": [
            str(v).strip() for v in list(delivery_required_validator_ids or []) if str(v).strip()
        ],
        "delivery_enforce_required_validator_ids": bool(delivery_enforce_required_validator_ids),
        "delivery_reject_on_any_reject": bool(delivery_reject_on_any_reject),
        "delivery_retry_interval_ms": max(0, int(delivery_retry_interval_ms)),
        "delivery_max_attempts": max(1, int(delivery_max_attempts)),
        "delivery_timeout_ms": max(1, int(delivery_timeout_ms)),
        "delivery_ack_channel": str(delivery_ack_channel),
        "delivery_emit_ack": bool(delivery_emit_ack),
        "pending_timeout_ms": None if pending_timeout_ms is None else max(0, int(pending_timeout_ms)),
        "transport": str(transport),
        "transport_host": str(transport_host),
        "transport_port": int(transport_port),
        "transport_connect": bool(transport_connect),
        "transport_keep_open": bool(transport_keep_open),
        "transport_backpressure_max_pending": None
        if transport_backpressure_max_pending is None
        else max(1, int(transport_backpressure_max_pending)),
        "transport_backpressure_policy": (
            str(transport_backpressure_policy).strip().lower()
            if str(transport_backpressure_policy).strip().lower() in BACKPRESSURE_POLICIES
            else "block"
        ),
        "transport_backpressure_block_timeout_ms": max(0, int(transport_backpressure_block_timeout_ms)),
        "artifact_store_dir": None
        if artifact_store_dir is None or not str(artifact_store_dir).strip()
        else str(artifact_store_dir),
        "publish_inline_payload": bool(publish_inline_payload),
        "replay_sample_stride": max(0, int(replay_sample_stride)),
        "epoch_state_path": None if epoch_state_path is None or not str(epoch_state_path).strip() else str(epoch_state_path),
        "epoch_replica_state_paths": [
            str(path).strip() for path in list(epoch_replica_state_paths or []) if str(path).strip()
        ],
        "epoch_replica_read_quorum": None if epoch_replica_read_quorum is None else max(1, int(epoch_replica_read_quorum)),
        "epoch_replica_write_quorum": None
        if epoch_replica_write_quorum is None
        else max(1, int(epoch_replica_write_quorum)),
        "epoch_lock_timeout_ms": max(1, int(epoch_lock_timeout_ms)),
        "epoch_lock_poll_ms": max(1, int(epoch_lock_poll_ms)),
        "epoch_lock_stale_ms": None if epoch_lock_stale_ms is None else max(1, int(epoch_lock_stale_ms)),
        "epoch_consensus_required_total_accepts": max(1, int(epoch_consensus_required_total_accepts)),
        "epoch_consensus_timeout_ms": max(1, int(epoch_consensus_timeout_ms)),
        "epoch_consensus_reject_on_any_reject": bool(epoch_consensus_reject_on_any_reject),
        "epoch_consensus_channel": str(epoch_consensus_channel),
        "epoch_consensus_enabled": bool(epoch_consensus_enabled),
        "delivery_outbox_path": None
        if delivery_outbox_path is None or not str(delivery_outbox_path).strip()
        else str(delivery_outbox_path),
        "delivery_outbox_max_entries": None
        if delivery_outbox_max_entries is None
        else max(1, int(delivery_outbox_max_entries)),
        "delivery_outbox_flush_limit": None
        if delivery_outbox_flush_limit is None
        else max(1, int(delivery_outbox_flush_limit)),
        "delivery_outbox_drop_policy": (
            str(delivery_outbox_drop_policy).strip().lower()
            if str(delivery_outbox_drop_policy).strip().lower() in OUTBOX_DROP_POLICIES
            else "audit_first"
        ),
        "fabric_acks_retention_window": max(0, int(fabric_acks_retention_window)),
        "fabric_acks_compaction_budget": max(0, int(fabric_acks_compaction_budget)),
        "fabric_ack_envelopes_retention_window": max(0, int(fabric_ack_envelopes_retention_window)),
        "fabric_ack_envelopes_compaction_budget": max(0, int(fabric_ack_envelopes_compaction_budget)),
        "fabric_delivery_acks_retention_window": max(0, int(fabric_delivery_acks_retention_window)),
        "fabric_delivery_acks_compaction_budget": max(0, int(fabric_delivery_acks_compaction_budget)),
        "fabric_dead_letters_retention_window": max(0, int(fabric_dead_letters_retention_window)),
        "fabric_dead_letters_compaction_budget": max(0, int(fabric_dead_letters_compaction_budget)),
        "fabric_quorum_report_retention_window": max(0, int(fabric_quorum_report_retention_window)),
        "fabric_quorum_report_compaction_budget": max(0, int(fabric_quorum_report_compaction_budget)),
    }


__all__ = ["normalize_fabric_handshake_recorder_attach_kwargs"]
