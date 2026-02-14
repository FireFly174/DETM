"""Service stack builders for fabric runtime composition."""

from __future__ import annotations

from typing import Any, Callable

from detm.runtime.fabric import (
    FabricAckIngressService,
    FabricCommitDeliveryService,
    FabricCommitIngressService,
    FabricHandshakeService,
    RetryPolicy,
)


def build_service_stack(
    *,
    rec: Any,
    mode_channels: Callable[[str], dict[str, str] | None],
    transport: Any,
    validator: Any,
    artifact_resolver: Any,
    delivery_outbox: Any,
    epoch_coordinator: Any,
    quorum_runtime: Any,
    delivery_tracker: Any,
    ack_envelopes: list[Any],
    delivery_ack_envelopes: list[Any],
    commit_dead_letters: list[dict[str, str]],
) -> tuple[FabricHandshakeService, FabricAckIngressService, FabricCommitDeliveryService, FabricCommitIngressService]:
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
    return service, ack_runtime, delivery_runtime, commit_ingress


__all__ = ["build_service_stack"]
