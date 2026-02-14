"""Runtime ingress service for proof/trust ack envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import FabricTransportAdapter

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (ack subscription/ingress routing extracted as dedicated runtime service)
# - OOP_TECH_DEBT: distributed replay-safe ack ingestion and durable ack event log replication


def _norm_mode(value: str | None) -> str | None:
    if value is None:
        return None
    mode = str(value).strip().lower()
    return mode or None


class AckEnvelopeConsumer(Protocol):
    """Minimal protocol for consumers that ingest ack envelopes."""

    def on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        ...


@dataclass
class FabricAckIngressService:
    """Subscribes to ack channels and forwards envelopes to quorum/coordinators."""

    transport: FabricTransportAdapter
    ack_channel: str = "fabric.ack"
    ack_channels_by_mode: dict[str, str] | None = None
    mode_filter: str | None = None
    consumer: AckEnvelopeConsumer | None = None
    ack_envelopes: list[FabricEnvelope] = field(default_factory=list)
    _subscriptions: list[tuple[str, str | None]] = field(default_factory=list)
    _ack_handler: object | None = None
    _started: bool = False

    @property
    def subscriptions(self) -> list[tuple[str, str | None]]:
        return list(self._subscriptions)

    def start(self) -> None:
        if self._started:
            return
        if self._ack_handler is None:
            self._ack_handler = self._on_ack_envelope
        handler = self._ack_handler
        self._subscriptions = self._build_ack_subscriptions()
        for channel, mode in list(self._subscriptions):
            self.transport.subscribe(channel, handler, mode=mode)  # type: ignore[arg-type]
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        handler = self._ack_handler
        for channel, mode in list(self._subscriptions):
            if handler is not None:
                self.transport.unsubscribe(channel, handler, mode=mode)  # type: ignore[arg-type]
        self._subscriptions = []
        self._started = False

    def _build_ack_subscriptions(self) -> list[tuple[str, str | None]]:
        mode_filter = _norm_mode(self.mode_filter)
        out: list[tuple[str, str | None]] = []
        if self.ack_channels_by_mode:
            seen: set[tuple[str, str | None]] = set()
            for raw_mode, raw_channel in sorted(self.ack_channels_by_mode.items()):
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
        return [(str(self.ack_channel), None)]

    def _on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        self.on_ack_envelope(envelope)

    def on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        self.ack_envelopes.append(envelope)
        if self.consumer is not None:
            self.consumer.on_ack_envelope(envelope)


__all__ = ["AckEnvelopeConsumer", "FabricAckIngressService"]


