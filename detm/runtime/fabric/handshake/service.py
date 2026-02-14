"""Handshake service wiring commit envelopes to validator acknowledgements."""

from __future__ import annotations

from dataclasses import dataclass, field

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric.handshake.contracts import AckWriter, CommitResolver
from detm.runtime.fabric.handshake.flow import (
    build_commit_subscriptions,
    flush_outbox as flush_outbox_flow,
    on_commit_envelope as on_commit_envelope_flow,
    publish_delivery_ack as publish_delivery_ack_flow,
    publish_envelope as publish_envelope_flow,
    publish_epoch_reject_ack as publish_epoch_reject_ack_flow,
    publish_missing_payload_ack as publish_missing_payload_ack_flow,
    resolve_channel_for_mode,
)
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
        return build_commit_subscriptions(self)

    def _ack_channel_for_mode(self, mode: str) -> str:
        return resolve_channel_for_mode(
            fallback=str(self.ack_channel),
            mapping=self.ack_channels_by_mode,
            mode=str(mode),
        )

    def _delivery_ack_channel_for_mode(self, mode: str) -> str:
        return resolve_channel_for_mode(
            fallback=str(self.delivery_ack_channel),
            mapping=self.delivery_ack_channels_by_mode,
            mode=str(mode),
        )

    def flush_outbox(self) -> dict[str, object]:
        return flush_outbox_flow(self)

    def on_commit_envelope(self, envelope: FabricEnvelope) -> None:
        on_commit_envelope_flow(self, envelope)

    def _publish_delivery_ack(self, envelope: FabricEnvelope, *, status: str) -> None:
        publish_delivery_ack_flow(self, envelope, status=status)

    def _publish_missing_payload_ack(self, envelope: FabricEnvelope) -> None:
        publish_missing_payload_ack_flow(self, envelope)

    def _publish_epoch_reject_ack(self, envelope: FabricEnvelope, *, packet: CommitPacket, reason: str) -> None:
        publish_epoch_reject_ack_flow(self, envelope, packet=packet, reason=reason)

    def _publish_envelope(self, envelope: FabricEnvelope) -> bool:
        return publish_envelope_flow(self, envelope)


__all__ = ["FabricHandshakeService"]



