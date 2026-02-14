"""Subscriber wiring for headless runtime runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from detm_app.runtime.coarsening import InvariantCoarsener, parse_invariant_streams
from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import (
    ArtifactWriter,
    CommitJsonlWriter,
    CommitValidationReporter,
    FabricHandshakeRecorder,
    FieldHistoryRecorder,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    TraceRecorder,
    VizStreamer,
    WatchContractWriter,
    WatchTraceWriter,
)
from detm.runtime.config import DETMConfig


def _storage_policy(*, config: DETMConfig, level_name: str, artifact: str) -> dict[str, int]:
    return config.resolve_artifact_storage_policy(artifact=str(artifact), level=str(level_name))


def _attach_core_subscribers(
    *,
    session: DetmSession,
    config: DETMConfig,
    seed: int,
    out_dir: Path,
    level_name: str,
    invariant_streams: list[str] | None,
) -> None:
    if invariant_streams:
        inv_policy = _storage_policy(config=config, level_name=level_name, artifact="invariants")
        InvariantCoarsener.attach(session.bus, parse_invariant_streams(invariant_streams))
        InvariantTickJsonlWriter.attach(
            session.bus,
            out_dir / "invariants.jsonl",
            retention_window=int(inv_policy.get("retention_window", 0)),
            compaction_budget=int(inv_policy.get("compaction_budget", 0)),
        )

    history_policy = _storage_policy(config=config, level_name=level_name, artifact="history")
    TraceRecorder.attach(
        session.bus,
        out_dir,
        retention_window=int(history_policy.get("retention_window", 0)),
        compaction_budget=int(history_policy.get("compaction_budget", 0)),
    )
    ArtifactWriter.attach(session.bus, out_dir)

    trace_policy = _storage_policy(config=config, level_name=level_name, artifact="trace")
    JsonlTraceWriter.attach(
        session.bus,
        out_dir / "trace.jsonl",
        retention_window=int(trace_policy.get("retention_window", 0)),
        compaction_budget=int(trace_policy.get("compaction_budget", 0)),
    )

    if bool(config.watch_trace_enabled):
        watch_policy = _storage_policy(config=config, level_name=level_name, artifact="watch_trace")
        watch_contract_policy = _storage_policy(config=config, level_name=level_name, artifact="watch_contract")
        outerfields_policy = _storage_policy(config=config, level_name=level_name, artifact="outerfields")
        WatchTraceWriter.attach(
            session.bus,
            out_dir / "watch_trace.jsonl",
            retention_window=int(watch_policy.get("retention_window", 0)),
            compaction_budget=int(watch_policy.get("compaction_budget", 0)),
        )
        WatchContractWriter.attach(
            session.bus,
            out_dir / "watch_contract.jsonl",
            outerfields_dir=out_dir / "outerfields",
            level_src=level_name,
            base_level="L0",
            retention_window=int(watch_contract_policy.get("retention_window", 0)),
            compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
            outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
            outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
        )

    commits_policy = _storage_policy(config=config, level_name=level_name, artifact="commits")
    CommitJsonlWriter.attach(
        session.bus,
        out_dir / "commits.jsonl",
        node_id=f"seed_{int(seed):04d}",
        mode="realtime",
        retention_window=int(commits_policy.get("retention_window", 0)),
        compaction_budget=int(commits_policy.get("compaction_budget", 0)),
    )
    if bool(config.level_policy.audit_commit_enabled):
        commits_audit_policy = _storage_policy(config=config, level_name=level_name, artifact="commits_audit")
        CommitJsonlWriter.attach(
            session.bus,
            out_dir / "commits_audit.jsonl",
            node_id=f"seed_{int(seed):04d}",
            commit_type="proof",
            mode="audit",
            retention_window=int(commits_audit_policy.get("retention_window", 0)),
            compaction_budget=int(commits_audit_policy.get("compaction_budget", 0)),
        )

    commit_validation_policy = _storage_policy(config=config, level_name=level_name, artifact="commit_validation")
    CommitValidationReporter.attach(
        session.bus,
        out_dir,
        retention_window=int(commit_validation_policy.get("retention_window", 0)),
        compaction_budget=int(commit_validation_policy.get("compaction_budget", 0)),
    )


def _attach_fabric_handshake_subscriber(
    *,
    session: DetmSession,
    config: DETMConfig,
    seed: int,
    out_dir: Path,
    level_name: str,
    fabric_kwargs: Mapping[str, Any],
) -> None:
    if not bool(fabric_kwargs.get("fabric_handshake", False)):
        return

    fabric_acks_policy = _storage_policy(config=config, level_name=level_name, artifact="fabric_acks")
    fabric_ack_envelopes_policy = _storage_policy(
        config=config, level_name=level_name, artifact="fabric_ack_envelopes"
    )
    fabric_delivery_acks_policy = _storage_policy(config=config, level_name=level_name, artifact="fabric_delivery_acks")
    fabric_dead_letters_policy = _storage_policy(config=config, level_name=level_name, artifact="fabric_dead_letters")
    fabric_quorum_report_policy = _storage_policy(config=config, level_name=level_name, artifact="fabric_quorum_report")

    FabricHandshakeRecorder.attach(
        session.bus,
        out_dir,
        node_id=f"seed_{int(seed):04d}",
        mode_filter="realtime",
        required_proof_accepts=max(1, int(fabric_kwargs["fabric_required_proof_accepts"])),
        required_trust_accepts=max(1, int(fabric_kwargs["fabric_required_trust_accepts"])),
        required_unique_proof_validators=max(1, int(fabric_kwargs["fabric_required_unique_proof_validators"])),
        required_unique_trust_validators=max(1, int(fabric_kwargs["fabric_required_unique_trust_validators"])),
        required_validator_ids=[
            str(v).strip() for v in list(fabric_kwargs.get("fabric_required_validator_ids") or []) if str(v).strip()
        ],
        handshake_profile=str(fabric_kwargs["fabric_handshake_profile"]),
        enforce_required_validator_ids=bool(fabric_kwargs["fabric_enforce_required_validator_ids"]),
        enforce_active_validator_membership=bool(fabric_kwargs["fabric_enforce_active_validator_membership"]),
        enforce_ack_sender_validator_match=bool(fabric_kwargs["fabric_enforce_ack_sender_validator_match"]),
        enforce_ack_auth_key_id_binding=bool(fabric_kwargs["fabric_enforce_ack_auth_key_id_binding"]),
        validator_auth_key_ids=fabric_kwargs.get("fabric_validator_auth_key_ids"),
        enforce_ack_transport_identity_binding=bool(fabric_kwargs["fabric_enforce_ack_transport_identity_binding"]),
        validator_transport_identities=fabric_kwargs.get("fabric_validator_transport_identities"),
        reject_on_any_reject=bool(fabric_kwargs["fabric_reject_on_any_reject"]),
        publish_retry_attempts=max(1, int(fabric_kwargs["fabric_retry_attempts"])),
        pending_timeout_ms=(
            None
            if fabric_kwargs.get("fabric_pending_timeout_ms") is None
            else max(0, int(fabric_kwargs["fabric_pending_timeout_ms"]))
        ),
        transport=str(fabric_kwargs["fabric_transport"]),
        transport_host=str(fabric_kwargs["fabric_transport_host"]),
        transport_port=int(fabric_kwargs["fabric_transport_port"]),
        transport_connect=bool(fabric_kwargs["fabric_transport_connect"]),
        transport_keep_open=bool(fabric_kwargs["fabric_transport_keep_open"]),
        transport_backpressure_max_pending=(
            None
            if fabric_kwargs.get("fabric_transport_backpressure_max_pending") is None
            else max(1, int(fabric_kwargs["fabric_transport_backpressure_max_pending"]))
        ),
        transport_backpressure_policy=str(fabric_kwargs["fabric_transport_backpressure_policy"]),
        transport_backpressure_block_timeout_ms=max(0, int(fabric_kwargs["fabric_transport_backpressure_block_timeout_ms"])),
        transport_dedup_ingress_enabled=bool(fabric_kwargs["fabric_transport_dedup_ingress_enabled"]),
        transport_dedup_ttl_ms=max(1, int(fabric_kwargs["fabric_transport_dedup_ttl_ms"])),
        transport_dedup_max_entries=max(1, int(fabric_kwargs["fabric_transport_dedup_max_entries"])),
        transport_auth_enabled=bool(fabric_kwargs["fabric_transport_auth_enabled"]),
        transport_auth_key=(
            None
            if fabric_kwargs.get("fabric_transport_auth_key") is None
            or not str(fabric_kwargs.get("fabric_transport_auth_key")).strip()
            else str(fabric_kwargs["fabric_transport_auth_key"])
        ),
        transport_auth_key_id=(
            None
            if fabric_kwargs.get("fabric_transport_auth_key_id") is None
            or not str(fabric_kwargs.get("fabric_transport_auth_key_id")).strip()
            else str(fabric_kwargs["fabric_transport_auth_key_id"]).strip()
        ),
        transport_tls_enabled=bool(fabric_kwargs["fabric_transport_tls_enabled"]),
        transport_tls_server_hostname=(
            None
            if fabric_kwargs.get("fabric_transport_tls_server_hostname") is None
            or not str(fabric_kwargs.get("fabric_transport_tls_server_hostname")).strip()
            else str(fabric_kwargs["fabric_transport_tls_server_hostname"]).strip()
        ),
        transport_tls_ca_file=(
            None
            if fabric_kwargs.get("fabric_transport_tls_ca_file") is None
            or not str(fabric_kwargs.get("fabric_transport_tls_ca_file")).strip()
            else str(fabric_kwargs["fabric_transport_tls_ca_file"]).strip()
        ),
        transport_tls_cert_file=(
            None
            if fabric_kwargs.get("fabric_transport_tls_cert_file") is None
            or not str(fabric_kwargs.get("fabric_transport_tls_cert_file")).strip()
            else str(fabric_kwargs["fabric_transport_tls_cert_file"]).strip()
        ),
        transport_tls_key_file=(
            None
            if fabric_kwargs.get("fabric_transport_tls_key_file") is None
            or not str(fabric_kwargs.get("fabric_transport_tls_key_file")).strip()
            else str(fabric_kwargs["fabric_transport_tls_key_file"]).strip()
        ),
        transport_tls_require_client_cert=bool(fabric_kwargs["fabric_transport_tls_require_client_cert"]),
        transport_tls_client_ca_file=(
            None
            if fabric_kwargs.get("fabric_transport_tls_client_ca_file") is None
            or not str(fabric_kwargs.get("fabric_transport_tls_client_ca_file")).strip()
            else str(fabric_kwargs["fabric_transport_tls_client_ca_file"]).strip()
        ),
        transport_tls_insecure_skip_verify=bool(fabric_kwargs["fabric_transport_tls_insecure_skip_verify"]),
        transport_tls_identity_source=str(fabric_kwargs["fabric_transport_tls_identity_source"]),
        transport_tls_identity_fallback_to_fingerprint=bool(
            fabric_kwargs["fabric_transport_tls_identity_fallback_to_fingerprint"]
        ),
        artifact_store_dir=(
            None if fabric_kwargs.get("fabric_artifact_dir") is None else str(fabric_kwargs["fabric_artifact_dir"])
        ),
        publish_inline_payload=bool(fabric_kwargs["fabric_inline_bridge"]),
        replay_sample_stride=max(0, int(fabric_kwargs["fabric_replay_sample_stride"])),
        replay_policy_tier=str(fabric_kwargs["fabric_replay_policy_tier"]),
        replay_strict_window_size=max(1, int(fabric_kwargs["fabric_replay_strict_window_size"])),
        validator_coordination_state_path=(
            None
            if fabric_kwargs.get("fabric_validator_coordination_state_path") is None
            else str(fabric_kwargs["fabric_validator_coordination_state_path"])
        ),
        validator_coordination_replica_paths=[
            str(v).strip()
            for v in list(fabric_kwargs.get("fabric_validator_coordination_replica_state_paths") or [])
            if str(v).strip()
        ],
        validator_coordination_replica_read_quorum=(
            None
            if fabric_kwargs.get("fabric_validator_coordination_replica_read_quorum") is None
            else max(1, int(fabric_kwargs["fabric_validator_coordination_replica_read_quorum"]))
        ),
        validator_coordination_replica_write_quorum=(
            None
            if fabric_kwargs.get("fabric_validator_coordination_replica_write_quorum") is None
            else max(1, int(fabric_kwargs["fabric_validator_coordination_replica_write_quorum"]))
        ),
        epoch_state_path=None if fabric_kwargs.get("fabric_epoch_state_path") is None else str(fabric_kwargs["fabric_epoch_state_path"]),
        epoch_replica_state_paths=[
            str(v).strip() for v in list(fabric_kwargs.get("fabric_epoch_replica_state_paths") or []) if str(v).strip()
        ],
        epoch_replica_read_quorum=(
            None
            if fabric_kwargs.get("fabric_epoch_replica_read_quorum") is None
            else max(1, int(fabric_kwargs["fabric_epoch_replica_read_quorum"]))
        ),
        epoch_replica_write_quorum=(
            None
            if fabric_kwargs.get("fabric_epoch_replica_write_quorum") is None
            else max(1, int(fabric_kwargs["fabric_epoch_replica_write_quorum"]))
        ),
        epoch_lock_timeout_ms=max(1, int(fabric_kwargs["fabric_epoch_lock_timeout_ms"])),
        epoch_lock_poll_ms=max(1, int(fabric_kwargs["fabric_epoch_lock_poll_ms"])),
        epoch_lock_stale_ms=(
            None
            if fabric_kwargs.get("fabric_epoch_lock_stale_ms") is None
            else max(1, int(fabric_kwargs["fabric_epoch_lock_stale_ms"]))
        ),
        epoch_consensus_required_total_accepts=max(1, int(fabric_kwargs["fabric_epoch_consensus_required_total_accepts"])),
        epoch_consensus_timeout_ms=max(1, int(fabric_kwargs["fabric_epoch_consensus_timeout_ms"])),
        epoch_consensus_max_attempts=max(1, int(fabric_kwargs["fabric_epoch_consensus_max_attempts"])),
        epoch_consensus_reject_on_any_reject=bool(fabric_kwargs["fabric_epoch_consensus_reject_on_any_reject"]),
        epoch_consensus_channel=str(fabric_kwargs["fabric_epoch_consensus_channel"]),
        epoch_consensus_enabled=bool(fabric_kwargs["fabric_epoch_consensus_enabled"]),
        split_mode_channels=bool(fabric_kwargs["fabric_split_mode_channels"]),
        commit_publish_retry_attempts=max(1, int(fabric_kwargs["fabric_commit_retry_attempts"])),
        delivery_required_receipts=max(0, int(fabric_kwargs["fabric_delivery_required_receipts"])),
        delivery_guarantee_mode=str(fabric_kwargs["fabric_delivery_guarantee_mode"]),
        delivery_required_validator_ids=[
            str(v).strip()
            for v in list(fabric_kwargs.get("fabric_delivery_required_validator_ids") or [])
            if str(v).strip()
        ],
        delivery_enforce_required_validator_ids=bool(fabric_kwargs["fabric_delivery_enforce_required_validator_ids"]),
        delivery_reject_on_any_reject=bool(fabric_kwargs["fabric_delivery_reject_on_any_reject"]),
        delivery_retry_interval_ms=max(0, int(fabric_kwargs["fabric_delivery_retry_interval_ms"])),
        delivery_max_attempts=max(1, int(fabric_kwargs["fabric_delivery_max_attempts"])),
        delivery_timeout_ms=max(1, int(fabric_kwargs["fabric_delivery_timeout_ms"])),
        delivery_tracking_state_path=(
            None
            if fabric_kwargs.get("fabric_delivery_tracking_state_path") is None
            else str(fabric_kwargs["fabric_delivery_tracking_state_path"])
        ),
        delivery_ack_channel=str(fabric_kwargs["fabric_delivery_ack_channel"]),
        delivery_emit_ack=bool(fabric_kwargs["fabric_delivery_emit_ack"]),
        delivery_outbox_path=(
            None if fabric_kwargs.get("fabric_delivery_outbox_path") is None else str(fabric_kwargs["fabric_delivery_outbox_path"])
        ),
        delivery_outbox_max_entries=(
            None
            if fabric_kwargs.get("fabric_delivery_outbox_max_entries") is None
            else max(1, int(fabric_kwargs["fabric_delivery_outbox_max_entries"]))
        ),
        delivery_outbox_flush_limit=(
            None
            if fabric_kwargs.get("fabric_delivery_outbox_flush_limit") is None
            else max(1, int(fabric_kwargs["fabric_delivery_outbox_flush_limit"]))
        ),
        delivery_outbox_drop_policy=str(fabric_kwargs["fabric_delivery_outbox_drop_policy"]),
        fabric_acks_retention_window=int(fabric_acks_policy.get("retention_window", 0)),
        fabric_acks_compaction_budget=int(fabric_acks_policy.get("compaction_budget", 0)),
        fabric_ack_envelopes_retention_window=int(fabric_ack_envelopes_policy.get("retention_window", 0)),
        fabric_ack_envelopes_compaction_budget=int(fabric_ack_envelopes_policy.get("compaction_budget", 0)),
        fabric_delivery_acks_retention_window=int(fabric_delivery_acks_policy.get("retention_window", 0)),
        fabric_delivery_acks_compaction_budget=int(fabric_delivery_acks_policy.get("compaction_budget", 0)),
        fabric_dead_letters_retention_window=int(fabric_dead_letters_policy.get("retention_window", 0)),
        fabric_dead_letters_compaction_budget=int(fabric_dead_letters_policy.get("compaction_budget", 0)),
        fabric_quorum_report_retention_window=int(fabric_quorum_report_policy.get("retention_window", 0)),
        fabric_quorum_report_compaction_budget=int(fabric_quorum_report_policy.get("compaction_budget", 0)),
    )


def _attach_streaming_subscribers(
    *,
    session: DetmSession,
    out_dir: Path,
    viz_transport: Any,
    viz_every_steps: int,
    fields_npz: bool,
    fields_every_steps: int,
) -> None:
    if viz_transport is not None:
        VizStreamer.attach(session.bus, viz_transport, every_steps=viz_every_steps)
    if fields_npz:
        FieldHistoryRecorder.attach(
            session.bus,
            out_dir / "fields_hist.npz",
            every_steps=int(fields_every_steps),
            dtype="float32",
        )


def attach_headless_subscribers(
    *,
    session: DetmSession,
    config: DETMConfig,
    seed: int,
    out_dir: Path,
    level_name: str,
    invariant_streams: list[str] | None,
    viz_transport: Any,
    viz_every_steps: int,
    fields_npz: bool,
    fields_every_steps: int,
    fabric_kwargs: Mapping[str, Any],
) -> None:
    _attach_core_subscribers(
        session=session,
        config=config,
        seed=seed,
        out_dir=out_dir,
        level_name=level_name,
        invariant_streams=invariant_streams,
    )
    _attach_fabric_handshake_subscriber(
        session=session,
        config=config,
        seed=seed,
        out_dir=out_dir,
        level_name=level_name,
        fabric_kwargs=fabric_kwargs,
    )
    _attach_streaming_subscribers(
        session=session,
        out_dir=out_dir,
        viz_transport=viz_transport,
        viz_every_steps=viz_every_steps,
        fields_npz=fields_npz,
        fields_every_steps=fields_every_steps,
    )


__all__ = ["attach_headless_subscribers"]
