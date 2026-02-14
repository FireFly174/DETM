"""Reporting/runtime bundle builders for fabric runtime composition."""

from __future__ import annotations

from typing import Any, Callable

from detm.runtime.fabric import (
    FabricHandshakeRuntimeBundle,
    FabricQuorumReportBuilder,
    FabricRuntimeReportWriter,
)


def build_reporting_components(
    *,
    rec: Any,
    mode_channels: Callable[[str], dict[str, str] | None],
    quorum_runtime: Any,
    artifact_store: Any,
    transport: Any,
    delivery_outbox: Any,
    delivery_runtime: Any,
    epoch_coordinator: Any,
    epoch_consensus: Any,
    service: Any,
    ack_runtime: Any,
    ack_store: dict[str, Any],
    ack_envelopes: list[Any],
    delivery_ack_envelopes: list[Any],
    commit_dead_letters: list[dict[str, str]],
) -> tuple[FabricQuorumReportBuilder, FabricRuntimeReportWriter, FabricHandshakeRuntimeBundle]:
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
    return quorum_report_builder, fabric_report_writer, runtime_bundle


__all__ = ["build_reporting_components"]
