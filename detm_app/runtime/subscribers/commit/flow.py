"""Flow helpers for commit stream subscribers."""

from __future__ import annotations

from typing import Any, Dict

from detm.runtime import api
from detm.runtime.commit_packet import CommitPacket
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import PolicyDecision
from detm.runtime.schemas import DETM_COMMIT_PACKET_V1
from detm.runtime.state import DETMState

from detm_app.runtime.subscribers.common import _snapshot_digest, _trace_ref_for_tick
from detm_app.runtime.subscribers.watch.flow import resolve_policy_decision


def should_emit_commit(*, mode: str, tick: int, policy_decision: PolicyDecision) -> bool:
    is_commit_boundary = bool(policy_decision.commit_boundary_crossed)
    is_audit_due = bool(policy_decision.audit_commit_enabled) and (
        int(tick) % max(1, int(policy_decision.audit_commit_stride)) == 0
    )
    if str(mode) == "audit":
        return bool(is_commit_boundary and is_audit_due)
    return bool(is_commit_boundary)


def build_commit_packet(
    *,
    state: DETMState,
    influence: DETMInfluence | None,
    n_ticks: int,
    requested_n_ticks: int,
    step_requested_n_ticks: int,
    step_effective_n_ticks: int,
    observables: api.Observables,
    policy_decision: PolicyDecision,
    node_id: str,
    commit_type: str,
    mode: str,
    last_commit_id: str | None,
    get_state_blob: Any | None,
) -> tuple[CommitPacket, str, str]:
    tick = int(state.step_count)
    trace_ref = _trace_ref_for_tick(tick)
    commit_id = f"{node_id}:{tick}"
    summary: Dict[str, Any] = {
        "event_count": len(list(observables.events)),
        "requested_n_ticks": int(requested_n_ticks or n_ticks),
        "effective_n_ticks": int(n_ticks),
        "step_requested_n_ticks": int(step_requested_n_ticks or requested_n_ticks or n_ticks),
        "step_effective_n_ticks": int(step_effective_n_ticks or n_ticks),
        "commit_stride": int(policy_decision.commit_stride),
        "audit_commit_enabled": bool(policy_decision.audit_commit_enabled),
        "audit_commit_stride": int(policy_decision.audit_commit_stride),
        "epoch": int(tick),
        "watermark": int(tick),
    }
    if str(mode) == "audit":
        summary.update(_snapshot_digest(get_state_blob))
        summary["signature_vector"] = list(observables.signature.vector)

    packet = CommitPacket.from_dict(
        {
            "schema_version": DETM_COMMIT_PACKET_V1,
            "commit_type": str(commit_type),
            "mode": str(mode),
            "node_id": str(node_id),
            "commit_id": str(commit_id),
            "parent_ref": last_commit_id,
            "tick_ref": {"base_level": str(policy_decision.active_level), "tick": int(tick)},
            "inputs_ref": f"influence://{tick}" if influence is not None else None,
            "delta_ref": f"delta://L0/{tick}",
            "invariants_ref": f"invariants://L0/{tick}" if str(commit_type) == "proof" else None,
            "trace_ref": str(trace_ref),
            "summary": summary,
            "signature": f"sig://{node_id}/{tick}",
            "created_at_ms": int(tick),
        }
    )
    return packet, trace_ref, commit_id


def publish_commit_packet_event(
    *,
    bus: Any,
    packet: CommitPacket,
    node_id: str,
    commit_type: str,
    mode: str,
    trace_ref: str,
) -> None:
    commit_id = str(packet.commit_id)
    payload_ref = f"artifact://commit/{node_id}/{commit_id}"
    bus.publish(
        "commit_packet",
        packet=packet,
        payload_ref=payload_ref,
        node_id=node_id,
        commit_type=commit_type,
        mode=mode,
        trace_ref=trace_ref,
    )


__all__ = [
    "build_commit_packet",
    "publish_commit_packet_event",
    "resolve_policy_decision",
    "should_emit_commit",
]
