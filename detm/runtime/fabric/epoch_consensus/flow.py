"""Execution flow helpers for transport epoch consensus coordinator."""

from __future__ import annotations

import time
from typing import Any, Dict

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import EpochDecision, FabricEnvelope
from detm.runtime.fabric.epoch_consensus.state import PendingProposal


def ensure_started(rec: Any) -> None:
    if not rec._started:
        rec.start()


def evaluate_commit(rec: Any, packet: CommitPacket) -> EpochDecision:
    ensure_started(rec)

    local = rec.base_coordinator.evaluate_commit(packet)
    if not bool(local.accepted):
        with rec._lock:
            rec._stats["rejected"] = int(rec._stats.get("rejected", 0)) + 1
        return local
    if int(rec.required_total_accepts) <= 1:
        with rec._lock:
            rec._stats["accepted"] = int(rec._stats.get("accepted", 0)) + 1
        return local

    for attempt_index in range(int(rec.max_attempts)):
        proposal_id = _create_pending(rec, packet=packet, local=local)
        proposal_env = _build_proposal_envelope(rec, packet=packet, proposal_id=proposal_id)
        rec.transport.publish(proposal_env)
        decision = _await_or_timeout(rec, proposal_id=proposal_id, local=local, attempt_index=attempt_index)
        if decision is not None:
            return decision

    with rec._lock:
        rec._stats["rejected"] = int(rec._stats.get("rejected", 0)) + 1
    return EpochDecision(
        accepted=False,
        reason=f"epoch consensus retries exhausted: attempts={int(rec.max_attempts)}",
        epoch=int(local.epoch),
        watermark=int(local.watermark),
        tick=int(local.tick),
    )


def _create_pending(rec: Any, *, packet: CommitPacket, local: EpochDecision) -> str:
    with rec._condition:
        rec._seq += 1
        proposal_id = f"{rec.coordinator_id}:{int(packet.tick_ref.tick)}:{rec._seq}"
        pending = PendingProposal(
            proposal_id=proposal_id,
            commit_ref=str(packet.commit_id),
            tick=int(packet.tick_ref.tick),
            epoch=int(local.epoch),
            watermark=int(local.watermark),
            required_total_accepts=int(rec.required_total_accepts),
            reject_on_any_peer_reject=bool(rec.reject_on_any_peer_reject),
            accept_voters={str(rec.coordinator_id)},
            voter_outcomes={str(rec.coordinator_id): True},
        )
        rec._pending[proposal_id] = pending
        rec._stats["proposals_total"] = int(rec._stats.get("proposals_total", 0)) + 1
        return proposal_id


def _build_proposal_envelope(rec: Any, *, packet: CommitPacket, proposal_id: str) -> FabricEnvelope:
    return FabricEnvelope(
        message_type="epoch_proposal",
        channel=str(rec.channel),
        mode=str(packet.mode),
        sender=str(rec.coordinator_id),
        recipient=None,
        payload_ref=f"artifact://epoch/proposal/{proposal_id}",
        payload_inline={
            "proposal_id": proposal_id,
            "commit_ref": str(packet.commit_id),
            "packet": packet.to_dict(),
        },
        trace_ref=str(packet.trace_ref),
        commit_ref=str(packet.commit_id),
    )


def _await_or_timeout(
    rec: Any,
    *,
    proposal_id: str,
    local: EpochDecision,
    attempt_index: int,
) -> EpochDecision | None:
    deadline = time.monotonic() + (float(rec.timeout_ms) / 1000.0)
    with rec._condition:
        while True:
            current = rec._pending.get(proposal_id)
            if current is None:
                break
            if current.decided is not None:
                decision = current.decided
                rec._pending.pop(proposal_id, None)
                rec._stats["accepted" if bool(decision.accepted) else "rejected"] = (
                    int(rec._stats.get("accepted" if bool(decision.accepted) else "rejected", 0)) + 1
                )
                return decision
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            rec._condition.wait(timeout=remaining)

        current = rec._pending.pop(proposal_id, None)
        if current is None:
            if attempt_index + 1 < int(rec.max_attempts):
                rec._stats["retries_total"] = int(rec._stats.get("retries_total", 0)) + 1
                return None
            rec._stats["rejected"] = int(rec._stats.get("rejected", 0)) + 1
            return EpochDecision(
                accepted=False,
                reason="consensus pending state lost",
                epoch=int(local.epoch),
                watermark=int(local.watermark),
                tick=int(local.tick),
            )
        rec._stats["timeouts"] = int(rec._stats.get("timeouts", 0)) + 1
        if attempt_index + 1 < int(rec.max_attempts):
            rec._stats["retries_total"] = int(rec._stats.get("retries_total", 0)) + 1
            return None
        rec._stats["rejected"] = int(rec._stats.get("rejected", 0)) + 1
        return EpochDecision(
            accepted=False,
            reason=(
                f"epoch consensus timeout: accepts={len(current.accept_voters)}, "
                f"required={int(current.required_total_accepts)}, rejects={len(current.reject_reasons)}, "
                f"attempt={attempt_index + 1}/{int(rec.max_attempts)}"
            ),
            epoch=int(current.epoch),
            watermark=int(current.watermark),
            tick=int(current.tick),
        )


def on_epoch_envelope(rec: Any, envelope: FabricEnvelope) -> None:
    if envelope.message_type == "epoch_proposal":
        on_proposal(rec, envelope)
        return
    if envelope.message_type == "epoch_vote":
        on_vote(rec, envelope)


def on_proposal(rec: Any, envelope: FabricEnvelope) -> None:
    if str(envelope.sender) == str(rec.coordinator_id):
        return
    payload = envelope.payload_inline
    if not isinstance(payload, dict):
        return
    proposal_id = str(payload.get("proposal_id", "")).strip()
    packet_raw = payload.get("packet")
    if not proposal_id or not isinstance(packet_raw, dict):
        return
    try:
        packet = CommitPacket.from_dict(packet_raw)
    except Exception:
        return
    decision = rec.base_coordinator.evaluate_commit(packet)
    vote_env = FabricEnvelope(
        message_type="epoch_vote",
        channel=str(rec.channel),
        mode=str(envelope.mode),
        sender=str(rec.coordinator_id),
        recipient=str(envelope.sender),
        payload_ref=f"artifact://epoch/vote/{proposal_id}/{rec.coordinator_id}",
        payload_inline={
            "proposal_id": proposal_id,
            "voter_id": str(rec.coordinator_id),
            "accepted": bool(decision.accepted),
            "reason": None if decision.reason is None else str(decision.reason),
            "epoch": int(decision.epoch),
            "watermark": int(decision.watermark),
            "tick": int(decision.tick),
            "commit_ref": str(packet.commit_id),
        },
        trace_ref=str(packet.trace_ref),
        commit_ref=str(packet.commit_id),
    )
    rec.transport.publish(vote_env)


def on_vote(rec: Any, envelope: FabricEnvelope) -> None:
    payload = envelope.payload_inline
    if not isinstance(payload, dict):
        return
    recipient = None if envelope.recipient is None else str(envelope.recipient).strip()
    if recipient and recipient != str(rec.coordinator_id):
        return
    proposal_id = str(payload.get("proposal_id", "")).strip()
    voter_id = str(payload.get("voter_id", envelope.sender)).strip()
    if not proposal_id or not voter_id:
        return
    accepted = bool(payload.get("accepted", False))
    reason = None if payload.get("reason") is None else str(payload.get("reason"))

    with rec._condition:
        pending = rec._pending.get(proposal_id)
        if pending is None:
            return
        if voter_id in pending.voter_outcomes:
            previous = bool(pending.voter_outcomes.get(voter_id))
            if previous != bool(accepted):
                pending.reject_reasons[voter_id] = "conflicting vote from peer"
                rec._stats["conflicting_votes_total"] = int(rec._stats.get("conflicting_votes_total", 0)) + 1
            if pending.reject_on_any_peer_reject and pending.reject_reasons:
                details = ", ".join(f"{key}:{value}" for key, value in sorted(pending.reject_reasons.items()))
                pending.decided = EpochDecision(
                    accepted=False,
                    reason=f"peer rejected epoch proposal: {details}",
                    epoch=int(pending.epoch),
                    watermark=int(pending.watermark),
                    tick=int(pending.tick),
                )
            rec._condition.notify_all()
            return

        vote_payload_reason = _validate_vote_payload(pending=pending, payload=payload, accepted=accepted)
        if vote_payload_reason is not None:
            accepted = False
            reason = vote_payload_reason
            rec._stats["invalid_votes_total"] = int(rec._stats.get("invalid_votes_total", 0)) + 1

        pending.voter_outcomes[voter_id] = bool(accepted)
        if accepted:
            pending.accept_voters.add(voter_id)
        else:
            pending.reject_reasons[voter_id] = str(reason or "rejected")

        if pending.reject_on_any_peer_reject and pending.reject_reasons:
            details = ", ".join(f"{key}:{value}" for key, value in sorted(pending.reject_reasons.items()))
            pending.decided = EpochDecision(
                accepted=False,
                reason=f"peer rejected epoch proposal: {details}",
                epoch=int(pending.epoch),
                watermark=int(pending.watermark),
                tick=int(pending.tick),
            )
        elif len(pending.accept_voters) >= int(pending.required_total_accepts):
            pending.decided = EpochDecision(
                accepted=True,
                reason=None,
                epoch=int(pending.epoch),
                watermark=int(pending.watermark),
                tick=int(pending.tick),
            )

        rec._condition.notify_all()


def _validate_vote_payload(*, pending: PendingProposal, payload: dict[str, Any], accepted: bool) -> str | None:
    payload_commit_ref = str(payload.get("commit_ref", "")).strip()
    payload_epoch = payload.get("epoch")
    payload_watermark = payload.get("watermark")
    payload_tick = payload.get("tick")
    if payload_commit_ref and payload_commit_ref != str(pending.commit_ref):
        return f"vote commit_ref mismatch: got={payload_commit_ref}, expected={pending.commit_ref}"
    if not accepted:
        return None
    try:
        epoch_value = int(payload_epoch)
        watermark_value = int(payload_watermark)
        tick_value = int(payload_tick)
    except Exception:
        return "vote payload missing epoch/watermark/tick for accepted vote"
    if (
        int(epoch_value) != int(pending.epoch)
        or int(watermark_value) != int(pending.watermark)
        or int(tick_value) != int(pending.tick)
    ):
        return (
            "vote payload mismatch: "
            f"got=({epoch_value},{watermark_value},{tick_value}), "
            f"expected=({pending.epoch},{pending.watermark},{pending.tick})"
        )
    return None


def snapshot(rec: Any) -> Dict[str, Any]:
    base = rec.base_coordinator.snapshot()
    with rec._lock:
        return {
            "base": base,
            "consensus": {
                "mode": "transport_pre_consensus",
                "coordinator_id": str(rec.coordinator_id),
                "channel": str(rec.channel),
                "required_total_accepts": int(rec.required_total_accepts),
                "timeout_ms": int(rec.timeout_ms),
                "max_attempts": int(rec.max_attempts),
                "reject_on_any_peer_reject": bool(rec.reject_on_any_peer_reject),
                "pending_count": len(rec._pending),
                "stats": dict(rec._stats),
            },
        }


__all__ = ["evaluate_commit", "on_epoch_envelope", "on_proposal", "on_vote", "snapshot"]
