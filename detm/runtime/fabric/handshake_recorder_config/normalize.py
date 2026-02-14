"""Normalization helpers for FabricHandshakeRecorder.attach(...) settings."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from detm.runtime.fabric import OUTBOX_DROP_POLICIES
from detm.runtime.fabric import BACKPRESSURE_POLICIES
from detm.runtime.fabric.validator.policies import normalize_replay_policy_tier

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
    handshake_profile: str = "mvp",
    enforce_required_validator_ids: bool = False,
    enforce_active_validator_membership: bool = False,
    enforce_ack_sender_validator_match: bool = False,
    enforce_ack_auth_key_id_binding: bool = False,
    validator_auth_key_ids: Mapping[str, Sequence[str] | str] | Sequence[str] | str | None = None,
    enforce_ack_transport_identity_binding: bool = False,
    validator_transport_identities: Mapping[str, Sequence[str] | str] | Sequence[str] | str | None = None,
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
) -> dict[str, Any]:
    out = {
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
        "handshake_profile": _normalize_handshake_profile(handshake_profile),
        "enforce_required_validator_ids": bool(enforce_required_validator_ids),
        "enforce_active_validator_membership": bool(enforce_active_validator_membership),
        "enforce_ack_sender_validator_match": bool(enforce_ack_sender_validator_match),
        "enforce_ack_auth_key_id_binding": bool(enforce_ack_auth_key_id_binding),
        "validator_auth_key_ids": _normalize_validator_auth_key_ids(validator_auth_key_ids),
        "enforce_ack_transport_identity_binding": bool(enforce_ack_transport_identity_binding),
        "validator_transport_identities": _normalize_validator_auth_key_ids(validator_transport_identities),
        "reject_on_any_reject": bool(reject_on_any_reject),
        "publish_retry_attempts": max(1, int(publish_retry_attempts)),
        "commit_publish_retry_attempts": max(1, int(commit_publish_retry_attempts)),
        "delivery_required_receipts": max(0, int(delivery_required_receipts)),
        "delivery_guarantee_mode": _normalize_delivery_guarantee_mode(delivery_guarantee_mode),
        "delivery_required_validator_ids": [
            str(v).strip() for v in list(delivery_required_validator_ids or []) if str(v).strip()
        ],
        "delivery_enforce_required_validator_ids": bool(delivery_enforce_required_validator_ids),
        "delivery_reject_on_any_reject": bool(delivery_reject_on_any_reject),
        "delivery_retry_interval_ms": max(0, int(delivery_retry_interval_ms)),
        "delivery_max_attempts": max(1, int(delivery_max_attempts)),
        "delivery_timeout_ms": max(1, int(delivery_timeout_ms)),
        "delivery_tracking_state_path": None
        if delivery_tracking_state_path is None or not str(delivery_tracking_state_path).strip()
        else str(delivery_tracking_state_path).strip(),
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
        "transport_dedup_ingress_enabled": bool(transport_dedup_ingress_enabled),
        "transport_dedup_ttl_ms": max(1, int(transport_dedup_ttl_ms)),
        "transport_dedup_max_entries": max(1, int(transport_dedup_max_entries)),
        "transport_auth_enabled": bool(transport_auth_enabled),
        "transport_auth_key": None
        if transport_auth_key is None or not str(transport_auth_key).strip()
        else str(transport_auth_key),
        "transport_auth_key_id": None
        if transport_auth_key_id is None or not str(transport_auth_key_id).strip()
        else str(transport_auth_key_id).strip(),
        "transport_tls_enabled": bool(transport_tls_enabled),
        "transport_tls_server_hostname": None
        if transport_tls_server_hostname is None or not str(transport_tls_server_hostname).strip()
        else str(transport_tls_server_hostname).strip(),
        "transport_tls_ca_file": None
        if transport_tls_ca_file is None or not str(transport_tls_ca_file).strip()
        else str(transport_tls_ca_file).strip(),
        "transport_tls_cert_file": None
        if transport_tls_cert_file is None or not str(transport_tls_cert_file).strip()
        else str(transport_tls_cert_file).strip(),
        "transport_tls_key_file": None
        if transport_tls_key_file is None or not str(transport_tls_key_file).strip()
        else str(transport_tls_key_file).strip(),
        "transport_tls_require_client_cert": bool(transport_tls_require_client_cert),
        "transport_tls_client_ca_file": None
        if transport_tls_client_ca_file is None or not str(transport_tls_client_ca_file).strip()
        else str(transport_tls_client_ca_file).strip(),
        "transport_tls_insecure_skip_verify": bool(transport_tls_insecure_skip_verify),
        "transport_tls_identity_source": _normalize_transport_tls_identity_source(transport_tls_identity_source),
        "transport_tls_identity_fallback_to_fingerprint": bool(transport_tls_identity_fallback_to_fingerprint),
        "artifact_store_dir": None
        if artifact_store_dir is None or not str(artifact_store_dir).strip()
        else str(artifact_store_dir),
        "publish_inline_payload": bool(publish_inline_payload),
        "replay_sample_stride": max(0, int(replay_sample_stride)),
        "replay_policy_tier": normalize_replay_policy_tier(replay_policy_tier),
        "replay_strict_window_size": max(1, int(replay_strict_window_size)),
        "validator_coordination_state_path": None
        if validator_coordination_state_path is None or not str(validator_coordination_state_path).strip()
        else str(validator_coordination_state_path).strip(),
        "validator_coordination_replica_paths": [
            str(path).strip() for path in list(validator_coordination_replica_paths or []) if str(path).strip()
        ],
        "validator_coordination_replica_read_quorum": None
        if validator_coordination_replica_read_quorum is None
        else max(1, int(validator_coordination_replica_read_quorum)),
        "validator_coordination_replica_write_quorum": None
        if validator_coordination_replica_write_quorum is None
        else max(1, int(validator_coordination_replica_write_quorum)),
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
        "epoch_consensus_max_attempts": max(1, int(epoch_consensus_max_attempts)),
        "epoch_consensus_reject_on_any_reject": bool(epoch_consensus_reject_on_any_reject),
        "epoch_consensus_channel": str(epoch_consensus_channel),
        "epoch_consensus_enabled": bool(epoch_consensus_enabled),
        "delivery_outbox_path": None
        if delivery_outbox_path is None or not str(delivery_outbox_path).strip()
        else str(delivery_outbox_path),
        "delivery_outbox_replica_paths": [
            str(path).strip() for path in list(delivery_outbox_replica_paths or []) if str(path).strip()
        ],
        "delivery_outbox_replica_read_quorum": None
        if delivery_outbox_replica_read_quorum is None
        else max(1, int(delivery_outbox_replica_read_quorum)),
        "delivery_outbox_replica_write_quorum": None
        if delivery_outbox_replica_write_quorum is None
        else max(1, int(delivery_outbox_replica_write_quorum)),
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
    return _apply_handshake_profile(out)


def _normalize_validator_auth_key_ids(
    raw: Mapping[str, Sequence[str] | str] | Sequence[str] | str | None,
) -> dict[str, list[str]]:
    out: dict[str, set[str]] = {}

    def _add_pair(raw_validator: object, raw_key: object) -> None:
        validator_id = str(raw_validator).strip()
        key_id = str(raw_key).strip()
        if not validator_id or not key_id:
            return
        out.setdefault(validator_id, set()).add(key_id)

    def _parse_binding(binding: object) -> None:
        text = str(binding).strip()
        if not text:
            return
        chunks = [chunk.strip() for chunk in text.split(",") if chunk.strip()]
        for chunk in chunks:
            if "=" in chunk:
                validator_id, key_id = chunk.split("=", 1)
            elif ":" in chunk:
                validator_id, key_id = chunk.split(":", 1)
            else:
                continue
            _add_pair(validator_id, key_id)

    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        for validator_id, key_values in dict(raw).items():
            if isinstance(key_values, str):
                for key_id in [chunk.strip() for chunk in str(key_values).split(",") if chunk.strip()]:
                    _add_pair(validator_id, key_id)
            elif isinstance(key_values, Sequence):
                for key_id in list(key_values):
                    _add_pair(validator_id, key_id)
            else:
                _add_pair(validator_id, key_values)
    elif isinstance(raw, str):
        _parse_binding(raw)
    elif isinstance(raw, Sequence):
        for row in list(raw):
            _parse_binding(row)
    else:
        _parse_binding(raw)

    return {
        validator_id: sorted(list(key_ids))
        for validator_id, key_ids in sorted(out.items())
        if key_ids
    }


def _normalize_transport_tls_identity_source(raw: str | object) -> str:
    source = str(raw).strip().lower()
    if source not in {"auto", "cn", "san", "fingerprint"}:
        return "auto"
    return source


def _normalize_handshake_profile(raw: str | object) -> str:
    profile = str(raw).strip().lower()
    aliases = {
        "mvp": "mvp",
        "default": "mvp",
        "baseline": "mvp",
        "production": "production",
        "prod": "production",
        "strict": "production",
    }
    return aliases.get(profile, "mvp")


def _apply_handshake_profile(cfg: dict[str, Any]) -> dict[str, Any]:
    profile = str(cfg.get("handshake_profile", "mvp"))
    if profile != "production":
        return cfg

    required_validator_ids = [str(v).strip() for v in list(cfg.get("required_validator_ids", [])) if str(v).strip()]
    if not required_validator_ids:
        raise ValueError("handshake_profile=production requires non-empty required_validator_ids")

    auth_map = dict(cfg.get("validator_auth_key_ids", {}))
    transport_map = dict(cfg.get("validator_transport_identities", {}))
    if not auth_map and not transport_map:
        raise ValueError(
            "handshake_profile=production requires validator_auth_key_ids and/or validator_transport_identities"
        )

    if auth_map:
        missing_auth = [validator_id for validator_id in required_validator_ids if validator_id not in auth_map]
        if missing_auth:
            raise ValueError(
                "handshake_profile=production requires auth key-id bindings for required validators: "
                + ", ".join(sorted(missing_auth))
            )
        cfg["enforce_ack_auth_key_id_binding"] = True

    if transport_map:
        missing_transport = [
            validator_id for validator_id in required_validator_ids if validator_id not in transport_map
        ]
        if missing_transport:
            raise ValueError(
                "handshake_profile=production requires transport identity bindings for required validators: "
                + ", ".join(sorted(missing_transport))
            )
        cfg["enforce_ack_transport_identity_binding"] = True

    cfg["enforce_required_validator_ids"] = True
    cfg["enforce_active_validator_membership"] = True
    cfg["enforce_ack_sender_validator_match"] = True
    cfg["reject_on_any_reject"] = True
    return cfg


def _normalize_delivery_guarantee_mode(raw: str | object) -> str:
    mode = str(raw).strip().lower()
    aliases = {
        "best_effort": "best_effort",
        "best-effort": "best_effort",
        "at_least_once": "at_least_once",
        "at-least-once": "at_least_once",
        "at_least_once_idempotent": "at_least_once_idempotent",
        "at-least-once-idempotent": "at_least_once_idempotent",
        "at_least_once+idempotency": "at_least_once_idempotent",
        "at-least-once+idempotency": "at_least_once_idempotent",
    }
    return aliases.get(mode, "at_least_once_idempotent")


__all__ = ["normalize_fabric_handshake_recorder_attach_kwargs"]


