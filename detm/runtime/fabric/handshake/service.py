"""Handshake service wiring commit envelopes to validator acknowledgements."""

from __future__ import annotations

from dataclasses import dataclass, field

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric.handshake.common import norm_mode as _norm_mode
from detm.runtime.fabric.handshake.contracts import AckWriter, CommitResolver
from detm.runtime.fabric.handshake.policies import RetryPolicy
from detm.runtime.fabric import FabricEnvelopeOutbox
from detm.runtime.fabric import FabricEpochCoordinator
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import FabricTransportAdapter
from detm.runtime.fabric import FabricValidator

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 1 (transport persistence/retry abstraction still minimal)
# - OOP_TECH_DEBT: durable ack storage + timeout/retry policy + quorum coordinator

@dataclass
class FabricHandshakeService:
    """Consumes commit envelopes and publishes proof/trust ack envelopes."""

    transport: FabricTransportAdapter
    validator: FabricValidator
    commit_resolver: CommitResolver
    ack_writer: AckWriter
    commit_channel: str = "fabric.commit"
    ack_channel: str = "fabric.ack"
    delivery_ack_channel: str = "fabric.delivery.ack"
    emit_delivery_ack: bool = True
    commit_channels_by_mode: dict[str, str] | None = None
    ack_channels_by_mode: dict[str, str] | None = None
    delivery_ack_channels_by_mode: dict[str, str] | None = None
    mode_filter: str | None = None
    delivery_outbox: FabricEnvelopeOutbox | None = None
    outbox_flush_limit: int | None = None
    epoch_coordinator: FabricEpochCoordinator | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    _dead_letters: list[dict[str, str]] = field(default_factory=list)
    _subscriptions: list[tuple[str, str | None]] = field(default_factory=list)
    _commit_handler: object | None = None
    _started: bool = False

    @property
    def dead_letters(self) -> list[dict[str, str]]:
        return list(self._dead_letters)

    def start(self) -> None:
        if self._started:
            return
        if self._commit_handler is None:
            self._commit_handler = self.on_commit_envelope
        handler = self._commit_handler
        self._subscriptions = self._build_commit_subscriptions()
        for channel, mode in list(self._subscriptions):
            self.transport.subscribe(channel, handler, mode=mode)  # type: ignore[arg-type]
        self.flush_outbox()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        handler = self._commit_handler
        for channel, mode in list(self._subscriptions):
            if handler is not None:
                self.transport.unsubscribe(channel, handler, mode=mode)  # type: ignore[arg-type]
        self._subscriptions = []
        self._started = False

    def _build_commit_subscriptions(self) -> list[tuple[str, str | None]]:
        mode_filter = _norm_mode(self.mode_filter)
        out: list[tuple[str, str | None]] = []
        if self.commit_channels_by_mode:
            seen: set[tuple[str, str | None]] = set()
            for raw_mode, raw_channel in sorted(self.commit_channels_by_mode.items()):
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
        return [(str(self.commit_channel), mode_filter)]

    def _ack_channel_for_mode(self, mode: str) -> str:
        if not self.ack_channels_by_mode:
            return str(self.ack_channel)
        norm_mode = _norm_mode(mode)
        if norm_mode is None:
            return str(self.ack_channel)
        value = self.ack_channels_by_mode.get(norm_mode)
        if value is None:
            return str(self.ack_channel)
        channel = str(value).strip()
        return channel or str(self.ack_channel)

    def _delivery_ack_channel_for_mode(self, mode: str) -> str:
        if not self.delivery_ack_channels_by_mode:
            return str(self.delivery_ack_channel)
        norm_mode = _norm_mode(mode)
        if norm_mode is None:
            return str(self.delivery_ack_channel)
        value = self.delivery_ack_channels_by_mode.get(norm_mode)
        if value is None:
            return str(self.delivery_ack_channel)
        channel = str(value).strip()
        return channel or str(self.delivery_ack_channel)

    def flush_outbox(self) -> dict[str, object]:
        if self.delivery_outbox is None:
            return {"enabled": False, "sent": 0, "failed": 0, "remaining": 0}
        max_items = None if self.outbox_flush_limit is None else max(1, int(self.outbox_flush_limit))
        report = self.delivery_outbox.flush(self.transport.publish, max_items=max_items)
        out: dict[str, object] = {"enabled": True}
        out.update({str(k): int(v) for k, v in dict(report).items()})
        return out

    def on_commit_envelope(self, envelope: FabricEnvelope) -> None:
        if envelope.message_type != "commit":
            return
        self._publish_delivery_ack(envelope, status="received")
        packet = self.commit_resolver(envelope.payload_ref)
        if packet is None and isinstance(envelope.payload_inline, dict):
            try:
                packet = CommitPacket.from_dict(envelope.payload_inline)
            except Exception:
                packet = None
        if packet is None:
            self._publish_missing_payload_ack(envelope)
            return

        if self.epoch_coordinator is not None:
            decision = self.epoch_coordinator.evaluate_commit(packet)
            if not bool(decision.accepted):
                self._publish_epoch_reject_ack(envelope, packet=packet, reason=str(decision.reason or "epoch rejection"))
                return
            proof_ack, trust_ack = self.validator.validate_commit(
                packet,
                epoch=int(decision.epoch),
                watermark=int(decision.watermark),
                created_at_ms=int(packet.created_at_ms),
            )
        else:
            proof_ack, trust_ack = self.validator.validate_commit(packet, created_at_ms=int(packet.created_at_ms))
        for ack in (proof_ack, trust_ack):
            ack_ref = self.ack_writer(ack)
            ack_env = FabricEnvelope(
                message_type=str(ack.ack_type),
                channel=self._ack_channel_for_mode(str(envelope.mode)),
                mode=str(envelope.mode),
                sender=str(ack.validator_id),
                recipient=str(envelope.sender),
                payload_ref=str(ack_ref),
                payload_inline=ack.to_dict(),
                trace_ref=str(packet.trace_ref),
                commit_ref=str(packet.commit_id),
            )
            self._publish_envelope(ack_env)

    def _publish_delivery_ack(self, envelope: FabricEnvelope, *, status: str) -> None:
        if not bool(self.emit_delivery_ack):
            return
        validator_id = str(getattr(self.validator, "validator_id", "validator.local"))
        delivery_id = str(envelope.delivery_id or "").strip()
        if not delivery_id:
            # Legacy fallback: derive delivery id from sender/commit_ref to keep idempotent semantics.
            cref = str(envelope.commit_ref or envelope.payload_ref)
            delivery_id = f"{envelope.sender}:{cref}"
        ack_env = FabricEnvelope(
            message_type="delivery_ack",
            channel=self._delivery_ack_channel_for_mode(str(envelope.mode)),
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
            # Delivery receipts are best-effort transport metadata; absence of subscribers
            # on the receipt channel must not poison proof/trust handshake flow.
            self.transport.publish(ack_env)
        except Exception:
            pass

    def _publish_missing_payload_ack(self, envelope: FabricEnvelope) -> None:
        commit_ref = str(envelope.commit_ref or envelope.payload_ref)
        reason = "commit payload not found by payload_ref"
        validator_id = str(getattr(self.validator, "validator_id", "validator.local"))
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
            ack_ref = self.ack_writer(ack)
            ack_env = FabricEnvelope(
                message_type=str(ack.ack_type),
                channel=self._ack_channel_for_mode(str(envelope.mode)),
                mode=str(envelope.mode),
                sender=str(ack.validator_id),
                recipient=str(envelope.sender),
                payload_ref=str(ack_ref),
                payload_inline=ack.to_dict(),
                trace_ref=envelope.trace_ref,
                commit_ref=commit_ref,
            )
            self._publish_envelope(ack_env)

    def _publish_epoch_reject_ack(self, envelope: FabricEnvelope, *, packet: CommitPacket, reason: str) -> None:
        commit_ref = str(packet.commit_id)
        validator_id = str(getattr(self.validator, "validator_id", "validator.local"))
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
            ack_ref = self.ack_writer(ack)
            ack_env = FabricEnvelope(
                message_type=str(ack.ack_type),
                channel=self._ack_channel_for_mode(str(envelope.mode)),
                mode=str(envelope.mode),
                sender=str(ack.validator_id),
                recipient=str(envelope.sender),
                payload_ref=str(ack_ref),
                payload_inline=ack.to_dict(),
                trace_ref=str(packet.trace_ref),
                commit_ref=commit_ref,
            )
            self._publish_envelope(ack_env)

    def _publish_envelope(self, envelope: FabricEnvelope) -> bool:
        self.flush_outbox()
        attempts = max(1, int(self.retry_policy.max_attempts))
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                delivered = int(self.transport.publish(envelope))
                if delivered <= 0:
                    raise RuntimeError("transport publish returned 0 (dropped)")
                return True
            except Exception as exc:
                last_error = exc
        queued = False
        if self.delivery_outbox is not None:
            try:
                self.delivery_outbox.enqueue(
                    envelope,
                    error=str(last_error) if last_error is not None else "unknown publish error",
                )
                queued = True
            except Exception:
                queued = False
        self._dead_letters.append(
            {
                "channel": str(envelope.channel),
                "message_type": str(envelope.message_type),
                "commit_ref": str(envelope.commit_ref or ""),
                "error": str(last_error) if last_error is not None else "unknown publish error",
                "queued_to_outbox": str(bool(queued)).lower(),
            }
        )
        return False


__all__ = ["FabricHandshakeService"]



