"""Runtime commit-ingress wiring (commit_packet -> envelope publish)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricArtifactResolver
from detm.runtime.fabric import FabricCommitDeliveryService
from detm.runtime.fabric import FabricEnvelope

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (commit ingress routing extracted from subscriber orchestration)
# - OOP_TECH_DEBT: distributed ingest ordering and durable ingress buffering


@dataclass
class FabricCommitIngressService:
    """Converts commit packets into transport envelopes via artifact references."""

    artifact_resolver: FabricArtifactResolver
    delivery_runtime: FabricCommitDeliveryService
    commit_channel: str = "fabric.commit"
    commit_channels_by_mode: dict[str, str] | None = None
    delivery_required_receipts: int = 0
    publish_inline_payload: bool = True
    quorum_runtime: Any | None = None
    delivery_counter: int = 0

    def _channel_for_mode(self, mode: str) -> str:
        mapping = dict(self.commit_channels_by_mode or {})
        channel = mapping.get(str(mode).strip().lower())
        if channel is None:
            return str(self.commit_channel)
        text = str(channel).strip()
        return text or str(self.commit_channel)

    def on_commit_packet(
        self,
        *,
        packet: CommitPacket,
        payload_ref: str,
        mode: str,
        trace_ref: str | None = None,
    ) -> bool:
        if not isinstance(packet, CommitPacket):
            return False
        pref = self.artifact_resolver.remember_commit(packet, str(payload_ref))
        if self.quorum_runtime is not None and hasattr(self.quorum_runtime, "register_commit"):
            self.quorum_runtime.register_commit(str(packet.commit_id))

        delivery_id = None
        if int(self.delivery_required_receipts) > 0:
            self.delivery_counter += 1
            delivery_id = f"{packet.node_id}:{packet.commit_id}:{self.delivery_counter}"

        envelope = FabricEnvelope(
            message_type="commit",
            channel=self._channel_for_mode(str(mode)),
            mode=str(mode),
            sender=str(packet.node_id),
            recipient=None,
            payload_ref=pref,
            payload_inline=packet.to_dict() if bool(self.publish_inline_payload) else None,
            trace_ref=str(trace_ref) if trace_ref is not None else str(packet.trace_ref),
            commit_ref=str(packet.commit_id),
            delivery_id=delivery_id,
        )
        return bool(self.delivery_runtime.publish_commit_envelope(envelope, track_delivery=True))


__all__ = ["FabricCommitIngressService"]


