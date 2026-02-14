"""Request model for headless runner execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from detm.runtime.config import DETMConfig


DEFAULT_FABRIC_RUN_OPTIONS: dict[str, Any] = {
    "fabric_handshake": False,
    "fabric_required_proof_accepts": 1,
    "fabric_required_trust_accepts": 1,
    "fabric_required_unique_proof_validators": 1,
    "fabric_required_unique_trust_validators": 1,
    "fabric_required_validator_ids": None,
    "fabric_handshake_profile": "mvp",
    "fabric_enforce_required_validator_ids": False,
    "fabric_enforce_active_validator_membership": False,
    "fabric_enforce_ack_sender_validator_match": False,
    "fabric_enforce_ack_auth_key_id_binding": False,
    "fabric_validator_auth_key_ids": None,
    "fabric_enforce_ack_transport_identity_binding": False,
    "fabric_validator_transport_identities": None,
    "fabric_reject_on_any_reject": False,
    "fabric_retry_attempts": 2,
    "fabric_pending_timeout_ms": None,
    "fabric_transport": "memory",
    "fabric_transport_host": "127.0.0.1",
    "fabric_transport_port": 0,
    "fabric_transport_connect": False,
    "fabric_transport_keep_open": False,
    "fabric_transport_backpressure_max_pending": None,
    "fabric_transport_backpressure_policy": "block",
    "fabric_transport_backpressure_block_timeout_ms": 200,
    "fabric_transport_dedup_ingress_enabled": False,
    "fabric_transport_dedup_ttl_ms": 30_000,
    "fabric_transport_dedup_max_entries": 10_000,
    "fabric_transport_auth_enabled": False,
    "fabric_transport_auth_key": None,
    "fabric_transport_auth_key_id": None,
    "fabric_transport_tls_enabled": False,
    "fabric_transport_tls_server_hostname": None,
    "fabric_transport_tls_ca_file": None,
    "fabric_transport_tls_cert_file": None,
    "fabric_transport_tls_key_file": None,
    "fabric_transport_tls_require_client_cert": False,
    "fabric_transport_tls_client_ca_file": None,
    "fabric_transport_tls_insecure_skip_verify": False,
    "fabric_transport_tls_identity_source": "auto",
    "fabric_transport_tls_identity_fallback_to_fingerprint": False,
    "fabric_artifact_dir": None,
    "fabric_inline_bridge": True,
    "fabric_replay_sample_stride": 0,
    "fabric_replay_policy_tier": "sampled",
    "fabric_replay_strict_window_size": 128,
    "fabric_validator_coordination_state_path": None,
    "fabric_validator_coordination_replica_state_paths": None,
    "fabric_validator_coordination_replica_read_quorum": None,
    "fabric_validator_coordination_replica_write_quorum": None,
    "fabric_epoch_state_path": None,
    "fabric_epoch_replica_state_paths": None,
    "fabric_epoch_replica_read_quorum": None,
    "fabric_epoch_replica_write_quorum": None,
    "fabric_epoch_lock_timeout_ms": 5000,
    "fabric_epoch_lock_poll_ms": 10,
    "fabric_epoch_lock_stale_ms": 30000,
    "fabric_epoch_consensus_required_total_accepts": 1,
    "fabric_epoch_consensus_timeout_ms": 200,
    "fabric_epoch_consensus_max_attempts": 1,
    "fabric_epoch_consensus_reject_on_any_reject": False,
    "fabric_epoch_consensus_channel": "fabric.epoch",
    "fabric_epoch_consensus_enabled": False,
    "fabric_split_mode_channels": False,
    "fabric_commit_retry_attempts": 2,
    "fabric_delivery_required_receipts": 0,
    "fabric_delivery_guarantee_mode": "at_least_once_idempotent",
    "fabric_delivery_required_validator_ids": None,
    "fabric_delivery_enforce_required_validator_ids": False,
    "fabric_delivery_reject_on_any_reject": False,
    "fabric_delivery_retry_interval_ms": 100,
    "fabric_delivery_max_attempts": 3,
    "fabric_delivery_timeout_ms": 500,
    "fabric_delivery_tracking_state_path": None,
    "fabric_delivery_ack_channel": "fabric.delivery.ack",
    "fabric_delivery_emit_ack": True,
    "fabric_delivery_outbox_path": None,
    "fabric_delivery_outbox_max_entries": None,
    "fabric_delivery_outbox_flush_limit": None,
    "fabric_delivery_outbox_drop_policy": "audit_first",
}


def _normalize_fabric_kwargs(overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    merged = dict(DEFAULT_FABRIC_RUN_OPTIONS)
    if not overrides:
        return merged
    unknown = sorted(set(overrides.keys()) - set(DEFAULT_FABRIC_RUN_OPTIONS.keys()))
    if unknown:
        raise TypeError(f"Unsupported run_headless fabric option(s): {', '.join(unknown)}")
    merged.update(dict(overrides))
    return merged


@dataclass(frozen=True)
class RunHeadlessRequest:
    config: DETMConfig
    seed: int
    symbol_ids: tuple[str, ...]
    steps: int
    out_dir: Path
    viz_transport: Any
    steps_mode: str
    viz_every_steps: int
    fields_npz: bool
    fields_every_steps: int
    invariant_streams: tuple[str, ...] | None
    fabric_kwargs: dict[str, Any]


def build_run_headless_request(
    *,
    config: DETMConfig,
    seed: int,
    symbol_ids: list[str],
    steps: int,
    out_dir: Path,
    viz_transport: Any,
    steps_mode: str = "per_symbol",
    viz_every_steps: int = 1,
    fields_npz: bool = False,
    fields_every_steps: int = 1,
    invariant_streams: list[str] | None = None,
    fabric_kwargs: Mapping[str, Any] | None = None,
) -> RunHeadlessRequest:
    return RunHeadlessRequest(
        config=config,
        seed=int(seed),
        symbol_ids=tuple(str(sid) for sid in list(symbol_ids)),
        steps=int(steps),
        out_dir=Path(out_dir),
        viz_transport=viz_transport,
        steps_mode=str(steps_mode),
        viz_every_steps=int(viz_every_steps),
        fields_npz=bool(fields_npz),
        fields_every_steps=int(fields_every_steps),
        invariant_streams=None if invariant_streams is None else tuple(str(v) for v in list(invariant_streams)),
        fabric_kwargs=_normalize_fabric_kwargs(fabric_kwargs),
    )


__all__ = [
    "DEFAULT_FABRIC_RUN_OPTIONS",
    "RunHeadlessRequest",
    "build_run_headless_request",
]
