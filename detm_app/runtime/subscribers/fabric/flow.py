"""Runtime flow helpers for FabricHandshakeRecorder."""

from __future__ import annotations

from typing import Any, Dict

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricEnvelope, ProofAck, TrustAck
from detm.runtime.fabric import mode_channels, start_runtime_bundle
from detm_app.runtime.subscribers.fabric.lifecycle import clear_runtime_links


def mode_channels_for_recorder(rec: Any, base_channel: str) -> Dict[str, str] | None:
    return mode_channels(bool(rec.split_mode_channels), str(base_channel))


def start_bundle_for_recorder(rec: Any) -> None:
    ack_subs, delivery_subs = start_runtime_bundle(rec._runtime_bundle)
    rec._ack_subscriptions = list(ack_subs)
    rec._delivery_ack_subscriptions = list(delivery_subs)


def on_commit_packet(
    rec: Any,
    *,
    packet: CommitPacket,
    payload_ref: str,
    mode: str,
    trace_ref: str | None,
) -> None:
    if not isinstance(packet, CommitPacket):
        return
    if rec._transport is None:
        return
    tick_delivery_pending(rec)
    if rec._commit_ingress is None:
        return
    rec._commit_ingress.on_commit_packet(
        packet=packet,
        payload_ref=str(payload_ref),
        mode=str(mode),
        trace_ref=trace_ref,
    )
    rec._delivery_counter = int(rec._commit_ingress.delivery_counter)
    publish_runtime_snapshot(rec)


def tick_delivery_pending(rec: Any) -> None:
    if rec._delivery_runtime is None:
        return
    snap = rec._delivery_runtime.tick()
    rec._delivery_accepted_count = int(snap.get("accepted_count", 0))
    rec._delivery_rejected_count = int(snap.get("rejected_count", 0))
    rec._delivery_retries_total = int(snap.get("retries_total", 0))


def runtime_snapshot(rec: Any) -> Dict[str, Any]:
    delivery = (
        rec._delivery_runtime.snapshot()
        if rec._delivery_runtime is not None
        else {
            "accepted_count": int(rec._delivery_accepted_count),
            "rejected_count": int(rec._delivery_rejected_count),
            "pending_count": int(len(rec._delivery_pending or {})),
            "retries_total": int(rec._delivery_retries_total),
        }
    )
    quorum = rec._quorum_runtime.snapshot() if rec._quorum_runtime is not None else {}
    return {
        "enabled": True,
        "commit_count": int(len(rec._commit_store or {})),
        "ack_count": int(len(rec._ack_store or {})),
        "ack_envelope_count": int(len(rec._ack_envelopes or [])),
        "delivery_ack_count": int(len(rec._delivery_ack_envelopes or [])),
        "dead_letter_count": int(len(rec._commit_dead_letters or [])),
        "delivery": {
            "accepted_count": int(delivery.get("accepted_count", 0)),
            "rejected_count": int(delivery.get("rejected_count", 0)),
            "pending_count": int(delivery.get("pending_count", 0)),
            "retries_total": int(delivery.get("retries_total", 0)),
        },
        "quorum": {
            "commit_count": int(quorum.get("commit_count", 0)),
            "accepted_count": int(quorum.get("accepted_count", 0)),
            "pending_count": int(quorum.get("pending_count", 0)),
            "rejected_count": int(quorum.get("rejected_count", 0)),
        },
        "replay": {
            "checks_total": int(rec._replay_checks_total),
            "checks_failed": int(rec._replay_checks_failed),
        },
    }


def publish_runtime_snapshot(rec: Any) -> None:
    if rec._bus is None:
        return
    rec._bus.publish("fabric_runtime_snapshot", snapshot=runtime_snapshot(rec))


def resolve_commit(rec: Any, payload_ref: str) -> CommitPacket | None:
    if rec._artifact_resolver is None:
        return None
    return rec._artifact_resolver.resolve_commit(payload_ref)


def replay_check(rec: Any, packet: CommitPacket) -> tuple[bool, str | None]:
    if rec._artifact_resolver is None:
        return False, "artifact resolver is not configured"
    ok, reason = rec._artifact_resolver.replay_check(packet)
    snap = rec._artifact_resolver.replay_snapshot()
    rec._replay_checks_total = int(snap.get("checks_total", 0))
    rec._replay_checks_failed = int(snap.get("checks_failed", 0))
    return ok, reason


def write_ack(rec: Any, ack: ProofAck | TrustAck) -> str:
    if rec._artifact_resolver is None:
        raise RuntimeError("artifact resolver is not configured")
    return rec._artifact_resolver.write_ack(ack)


def resolve_ack(rec: Any, payload_ref: str) -> ProofAck | TrustAck | None:
    if rec._artifact_resolver is None:
        return None
    return rec._artifact_resolver.resolve_ack(payload_ref)


def on_ack_envelope(rec: Any, envelope: FabricEnvelope) -> None:
    if rec._ack_runtime is not None:
        rec._ack_runtime.on_ack_envelope(envelope)


def on_delivery_ack_envelope(rec: Any, envelope: FabricEnvelope) -> None:
    if rec._delivery_runtime is not None:
        rec._delivery_runtime.on_delivery_ack_envelope(envelope)


def on_close(rec: Any) -> None:
    tick_delivery_pending(rec)
    if rec._artifact_resolver is not None:
        replay = rec._artifact_resolver.replay_snapshot()
        rec._replay_checks_total = int(replay.get("checks_total", 0))
        rec._replay_checks_failed = int(replay.get("checks_failed", 0))
    publish_runtime_snapshot(rec)
    if rec._fabric_report_writer is not None:
        rec._fabric_report_writer.write_all(
            replay_sample_stride=int(rec.replay_sample_stride),
            replay_checks_total=int(rec._replay_checks_total),
            replay_checks_failed=int(rec._replay_checks_failed),
        )
    detach(rec)


def detach(rec: Any) -> None:
    if rec._runtime_bundle is not None:
        rec._runtime_bundle.stop()
        rec._ack_subscriptions = []
        rec._delivery_ack_subscriptions = []
        rec._runtime_bundle = None
    elif rec._transport is not None:
        rec._transport.close()
    clear_runtime_links(rec)
    if rec._unsub_commit is not None:
        rec._unsub_commit()
        rec._unsub_commit = None
    if rec._unsub_close is not None:
        rec._unsub_close()
        rec._unsub_close = None


__all__ = [
    "detach",
    "mode_channels_for_recorder",
    "on_ack_envelope",
    "on_close",
    "on_commit_packet",
    "on_delivery_ack_envelope",
    "publish_runtime_snapshot",
    "replay_check",
    "resolve_ack",
    "resolve_commit",
    "runtime_snapshot",
    "start_bundle_for_recorder",
    "tick_delivery_pending",
    "write_ack",
]
