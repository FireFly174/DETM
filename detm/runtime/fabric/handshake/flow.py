"""Execution helpers for FabricHandshakeService."""

from __future__ import annotations

from typing import Any

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricEnvelope, ProofAck, TrustAck
from detm.runtime.fabric.handshake.common import norm_mode as _norm_mode


def build_commit_subscriptions(rec: Any) -> list[tuple[str, str | None]]:
    mode_filter = _norm_mode(rec.mode_filter)
    out: list[tuple[str, str | None]] = []
    if rec.commit_channels_by_mode:
        seen: set[tuple[str, str | None]] = set()
        for raw_mode, raw_channel in sorted(rec.commit_channels_by_mode.items()):
            channel = str(raw_channel).strip()
            mode = _norm_mode(raw_mode)
            if not channel or mode is None:
                continue
            if mode_filter is not None and mode != mode_filter:
                continue
            key = (channel, mode)
            if key in seen:
                continue
            out.append(key)
            seen.add(key)
    if out:
        return out
    return [(str(rec.commit_channel), mode_filter)]


def resolve_channel_for_mode(*, fallback: str, mapping: dict[str, str] | None, mode: str) -> str:
    if not mapping:
        return str(fallback)
    norm_mode = _norm_mode(mode)
    if norm_mode is None:
        return str(fallback)
    value = mapping.get(norm_mode)
    if value is None:
        return str(fallback)
    channel = str(value).strip()
    return channel or str(fallback)


def flush_outbox(rec: Any) -> dict[str, object]:
    if rec.delivery_outbox is None:
        return {"enabled": False, "sent": 0, "failed": 0, "remaining": 0}
    max_items = None if rec.outbox_flush_limit is None else max(1, int(rec.outbox_flush_limit))
    report = rec.delivery_outbox.flush(rec.transport.publish, max_items=max_items)
    out: dict[str, object] = {"enabled": True}
    out.update({str(k): int(v) for k, v in dict(report).items()})
    return out


def on_commit_envelope(rec: Any, envelope: FabricEnvelope) -> None:
    if envelope.message_type != "commit":
        return
    publish_delivery_ack(rec, envelope, status="received")
    packet = rec.commit_resolver(envelope.payload_ref)
    if packet is None and isinstance(envelope.payload_inline, dict):
        try:
            packet = CommitPacket.from_dict(envelope.payload_inline)
        except Exception:
            packet = None
    if packet is None:
        publish_missing_payload_ack(rec, envelope)
        return

    if rec.epoch_coordinator is not None:
        decision = rec.epoch_coordinator.evaluate_commit(packet)
        if not bool(decision.accepted):
            publish_epoch_reject_ack(rec, envelope, packet=packet, reason=str(decision.reason or "epoch rejection"))
            return
        proof_ack, trust_ack = rec.validator.validate_commit(
            packet,
            epoch=int(decision.epoch),
            watermark=int(decision.watermark),
            created_at_ms=int(packet.created_at_ms),
        )
    else:
        proof_ack, trust_ack = rec.validator.validate_commit(packet, created_at_ms=int(packet.created_at_ms))
    for ack in (proof_ack, trust_ack):
        ack_ref = rec.ack_writer(ack)
        ack_env = FabricEnvelope(
            message_type=str(ack.ack_type),
            channel=resolve_channel_for_mode(
                fallback=str(rec.ack_channel),
                mapping=rec.ack_channels_by_mode,
                mode=str(envelope.mode),
            ),
            mode=str(envelope.mode),
            sender=str(ack.validator_id),
            recipient=str(envelope.sender),
            payload_ref=str(ack_ref),
            payload_inline=ack.to_dict(),
            trace_ref=str(packet.trace_ref),
            commit_ref=str(packet.commit_id),
        )
        publish_envelope(rec, ack_env)


def publish_delivery_ack(rec: Any, envelope: FabricEnvelope, *, status: str) -> None:
    if not bool(rec.emit_delivery_ack):
        return
    validator_id = str(getattr(rec.validator, "validator_id", "validator.local"))
    delivery_id = str(envelope.delivery_id or "").strip()
    if not delivery_id:
        cref = str(envelope.commit_ref or envelope.payload_ref)
        delivery_id = f"{envelope.sender}:{cref}"
    ack_env = FabricEnvelope(
        message_type="delivery_ack",
        channel=resolve_channel_for_mode(
            fallback=str(rec.delivery_ack_channel),
            mapping=rec.delivery_ack_channels_by_mode,
            mode=str(envelope.mode),
        ),
        mode=str(envelope.mode),
        sender=str(validator_id),
        recipient=str(envelope.sender),
        payload_ref=f"artifact://delivery_ack/{delivery_id}",
        payload_inline={
            "delivery_id": delivery_id,
            "commit_ref": envelope.commit_ref,
            "status": str(status),
            "validator_id": validator_id,
        },
        trace_ref=envelope.trace_ref,
        commit_ref=envelope.commit_ref,
        delivery_id=delivery_id,
    )
    try:
        rec.transport.publish(ack_env)
    except Exception:
        pass


def publish_missing_payload_ack(rec: Any, envelope: FabricEnvelope) -> None:
    commit_ref = str(envelope.commit_ref or envelope.payload_ref)
    reason = "commit payload not found by payload_ref"
    validator_id = str(getattr(rec.validator, "validator_id", "validator.local"))
    proof = ProofAck(
        validator_id=validator_id,
        node_id=str(envelope.sender),
        commit_ref=commit_ref,
        status="rejected",
        reason=reason,
        signature=f"sig://{validator_id}/proof/{commit_ref}",
    )
    trust = TrustAck(
        validator_id=validator_id,
        node_id=str(envelope.sender),
        commit_ref=commit_ref,
        status="rejected",
        reason=reason,
        signature=f"sig://{validator_id}/trust/{commit_ref}",
    )
    for ack in (proof, trust):
        ack_ref = rec.ack_writer(ack)
        ack_env = FabricEnvelope(
            message_type=str(ack.ack_type),
            channel=resolve_channel_for_mode(
                fallback=str(rec.ack_channel),
                mapping=rec.ack_channels_by_mode,
                mode=str(envelope.mode),
            ),
            mode=str(envelope.mode),
            sender=str(ack.validator_id),
            recipient=str(envelope.sender),
            payload_ref=str(ack_ref),
            payload_inline=ack.to_dict(),
            trace_ref=envelope.trace_ref,
            commit_ref=commit_ref,
        )
        publish_envelope(rec, ack_env)


def publish_epoch_reject_ack(rec: Any, envelope: FabricEnvelope, *, packet: CommitPacket, reason: str) -> None:
    commit_ref = str(packet.commit_id)
    validator_id = str(getattr(rec.validator, "validator_id", "validator.local"))
    proof = ProofAck(
        validator_id=validator_id,
        node_id=str(packet.node_id),
        commit_ref=commit_ref,
        status="rejected",
        reason=str(reason),
        signature=f"sig://{validator_id}/proof/{commit_ref}",
        created_at_ms=int(packet.created_at_ms),
    )
    trust = TrustAck(
        validator_id=validator_id,
        node_id=str(packet.node_id),
        commit_ref=commit_ref,
        status="rejected",
        reason=str(reason),
        signature=f"sig://{validator_id}/trust/{commit_ref}",
        created_at_ms=int(packet.created_at_ms),
    )
    for ack in (proof, trust):
        ack_ref = rec.ack_writer(ack)
        ack_env = FabricEnvelope(
            message_type=str(ack.ack_type),
            channel=resolve_channel_for_mode(
                fallback=str(rec.ack_channel),
                mapping=rec.ack_channels_by_mode,
                mode=str(envelope.mode),
            ),
            mode=str(envelope.mode),
            sender=str(ack.validator_id),
            recipient=str(envelope.sender),
            payload_ref=str(ack_ref),
            payload_inline=ack.to_dict(),
            trace_ref=str(packet.trace_ref),
            commit_ref=commit_ref,
        )
        publish_envelope(rec, ack_env)


def publish_envelope(rec: Any, envelope: FabricEnvelope) -> bool:
    flush_outbox(rec)
    attempts = max(1, int(rec.retry_policy.max_attempts))
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            delivered = int(rec.transport.publish(envelope))
            if delivered <= 0:
                raise RuntimeError("transport publish returned 0 (dropped)")
            return True
        except Exception as exc:
            last_error = exc
    queued = False
    if rec.delivery_outbox is not None:
        try:
            rec.delivery_outbox.enqueue(
                envelope,
                error=str(last_error) if last_error is not None else "unknown publish error",
            )
            queued = True
        except Exception:
            queued = False
    rec._dead_letters.append(
        {
            "channel": str(envelope.channel),
            "message_type": str(envelope.message_type),
            "commit_ref": str(envelope.commit_ref or ""),
            "error": str(last_error) if last_error is not None else "unknown publish error",
            "queued_to_outbox": str(bool(queued)).lower(),
        }
    )
    return False


__all__ = [
    "build_commit_subscriptions",
    "flush_outbox",
    "on_commit_envelope",
    "publish_delivery_ack",
    "publish_envelope",
    "publish_epoch_reject_ack",
    "publish_missing_payload_ack",
    "resolve_channel_for_mode",
]
