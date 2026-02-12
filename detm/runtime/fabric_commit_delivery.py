"""Runtime commit-delivery wiring (publish/retry + delivery receipt subscriptions)."""

from __future__ import annotations

from dataclasses import dataclass, field

from detm.runtime.fabric_delivery import FabricEnvelopeOutbox
from detm.runtime.fabric_delivery_tracking import DeliveryTrackingCoordinator
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_transport import FabricTransportAdapter

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (commit delivery routing extracted into dedicated runtime service)
# - OOP_TECH_DEBT: distributed durable delivery queue and cross-node replicated receipt state


def _norm_mode(value: str | None) -> str | None:
    if value is None:
        return None
    mode = str(value).strip().lower()
    return mode or None


@dataclass
class FabricCommitDeliveryService:
    """Publishes commit envelopes and tracks acknowledged delivery lifecycle."""

    transport: FabricTransportAdapter
    tracker: DeliveryTrackingCoordinator | None = None
    outbox: FabricEnvelopeOutbox | None = None
    delivery_ack_channel: str = "fabric.delivery.ack"
    delivery_ack_channels_by_mode: dict[str, str] | None = None
    mode_filter: str | None = None
    outbox_flush_limit: int | None = None
    commit_publish_retry_attempts: int = 1
    dead_letters: list[dict[str, str]] = field(default_factory=list)
    delivery_ack_envelopes: list[FabricEnvelope] = field(default_factory=list)
    _subscriptions: list[tuple[str, str | None]] = field(default_factory=list)
    _delivery_ack_handler: object | None = None
    _started: bool = False

    @property
    def subscriptions(self) -> list[tuple[str, str | None]]:
        return list(self._subscriptions)

    def start(self) -> None:
        if self._started:
            return
        if self._delivery_ack_handler is None:
            self._delivery_ack_handler = self._on_delivery_ack_envelope
        handler = self._delivery_ack_handler
        self._subscriptions = self._build_delivery_ack_subscriptions()
        for channel, mode in list(self._subscriptions):
            self.transport.subscribe(channel, handler, mode=mode)  # type: ignore[arg-type]
        self.flush_outbox()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        handler = self._delivery_ack_handler
        for channel, mode in list(self._subscriptions):
            if handler is not None:
                self.transport.unsubscribe(channel, handler, mode=mode)  # type: ignore[arg-type]
        self._subscriptions = []
        self._started = False

    def _build_delivery_ack_subscriptions(self) -> list[tuple[str, str | None]]:
        mode_filter = _norm_mode(self.mode_filter)
        out: list[tuple[str, str | None]] = []
        if self.delivery_ack_channels_by_mode:
            seen: set[tuple[str, str | None]] = set()
            for raw_mode, raw_channel in sorted(self.delivery_ack_channels_by_mode.items()):
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
        return [(str(self.delivery_ack_channel), None)]

    def flush_outbox(self) -> dict[str, object]:
        if self.outbox is None:
            return {"enabled": False, "sent": 0, "failed": 0, "remaining": 0}
        max_items = None if self.outbox_flush_limit is None else max(1, int(self.outbox_flush_limit))
        report = self.outbox.flush(self.transport.publish, max_items=max_items)
        out: dict[str, object] = {"enabled": True}
        out.update({str(k): int(v) for k, v in dict(report).items()})
        return out

    def delivery_tracking_enabled(self) -> bool:
        return bool(self.tracker is not None and self.tracker.enabled())

    def register_delivery(self, envelope: FabricEnvelope) -> str | None:
        if self.tracker is None:
            return None
        return self.tracker.register_delivery(envelope)

    def publish_commit_envelope(self, envelope: FabricEnvelope, *, track_delivery: bool) -> bool:
        delivery_id: str | None = None
        if bool(track_delivery):
            delivery_id = str(self.register_delivery(envelope) or "").strip() or None
        self.flush_outbox()
        attempts = max(1, int(self.commit_publish_retry_attempts))
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                if delivery_id is not None and self.tracker is not None:
                    self.tracker.mark_publish_attempt(delivery_id)
                delivered = int(self.transport.publish(envelope))
                if delivered <= 0:
                    raise RuntimeError("transport publish returned 0 (dropped)")
                return True
            except Exception as exc:
                last_error = exc
        queued = False
        if self.outbox is not None:
            try:
                self.outbox.enqueue(
                    envelope,
                    error=str(last_error) if last_error is not None else "unknown publish error",
                )
                queued = True
            except Exception:
                queued = False
        self.dead_letters.append(
            {
                "channel": str(envelope.channel),
                "message_type": str(envelope.message_type),
                "commit_ref": str(envelope.commit_ref or ""),
                "error": str(last_error) if last_error is not None else "unknown publish error",
                "queued_to_outbox": str(bool(queued)).lower(),
            }
        )
        return False

    def _on_delivery_ack_envelope(self, envelope: FabricEnvelope) -> None:
        self.on_delivery_ack_envelope(envelope)

    def on_delivery_ack_envelope(self, envelope: FabricEnvelope) -> None:
        if envelope.message_type != "delivery_ack":
            return
        self.delivery_ack_envelopes.append(envelope)
        if self.tracker is not None:
            self.tracker.on_delivery_ack_envelope(envelope)

    def tick(self) -> dict[str, object]:
        if self.tracker is None:
            return {
                "accepted_count": 0,
                "rejected_count": 0,
                "pending_count": 0,
                "retries_total": 0,
                "pending": [],
            }
        self.tracker.tick(lambda env: self.publish_commit_envelope(env, track_delivery=False))
        return self.snapshot()

    def snapshot(self) -> dict[str, object]:
        if self.tracker is None:
            return {
                "accepted_count": 0,
                "rejected_count": 0,
                "pending_count": 0,
                "retries_total": 0,
                "pending": [],
            }
        raw = self.tracker.snapshot()
        out: dict[str, object] = {
            "accepted_count": int(raw.get("accepted_count", 0)),
            "rejected_count": int(raw.get("rejected_count", 0)),
            "pending_count": int(raw.get("pending_count", 0)),
            "retries_total": int(raw.get("retries_total", 0)),
            "pending": list(raw.get("pending", [])),
        }
        return out

    def clear(self) -> None:
        if self.tracker is not None:
            self.tracker.clear()


__all__ = ["FabricCommitDeliveryService"]
