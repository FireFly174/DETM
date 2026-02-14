from __future__ import annotations

import time

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import InMemoryEpochWatermarkCoordinator
from detm.runtime.fabric import InMemoryFabricBus
from detm.runtime.fabric import TransportEpochConsensusCoordinator


def _make_commit(commit_id: str, tick: int, *, node_id: str = "node-A", epoch: int | None = None) -> CommitPacket:
    summary = {}
    if epoch is not None:
        summary["epoch"] = int(epoch)
        summary["watermark"] = int(epoch)
    return CommitPacket.from_dict(
        {
            "commit_type": "state",
            "mode": "realtime",
            "node_id": node_id,
            "commit_id": commit_id,
            "tick_ref": {"base_level": "L0", "tick": tick},
            "delta_ref": f"artifact://delta/{tick}",
            "trace_ref": f"trace://run/{tick}",
            "summary": summary,
            "signature": f"sig://{node_id}/{tick}",
        }
    )


def test_transport_epoch_consensus_rejects_on_timeout_without_peers():
    bus = InMemoryFabricBus()
    coordinator = TransportEpochConsensusCoordinator(
        coordinator_id="coordinator-1",
        transport=bus,
        base_coordinator=InMemoryEpochWatermarkCoordinator(),
        required_total_accepts=2,
        timeout_ms=20,
    )
    coordinator.start()
    decision = coordinator.evaluate_commit(_make_commit("node-A:1", tick=1))
    assert decision.accepted is False
    assert "consensus timeout" in str(decision.reason)


def test_transport_epoch_consensus_accepts_with_peer_vote():
    bus = InMemoryFabricBus()
    local = TransportEpochConsensusCoordinator(
        coordinator_id="coordinator-1",
        transport=bus,
        base_coordinator=InMemoryEpochWatermarkCoordinator(),
        required_total_accepts=2,
        timeout_ms=100,
    )
    peer = TransportEpochConsensusCoordinator(
        coordinator_id="coordinator-2",
        transport=bus,
        base_coordinator=InMemoryEpochWatermarkCoordinator(),
        required_total_accepts=2,
        timeout_ms=100,
    )
    local.start()
    peer.start()
    decision = local.evaluate_commit(_make_commit("node-A:1", tick=1))
    assert decision.accepted is True
    snap = local.snapshot()
    assert int(snap["consensus"]["stats"]["accepted"]) >= 1


def test_transport_epoch_consensus_rejects_when_peer_rejects_and_flag_enabled():
    bus = InMemoryFabricBus()
    peer_base = InMemoryEpochWatermarkCoordinator()
    assert peer_base.evaluate_commit(_make_commit("node-A:bootstrap", tick=1, epoch=5)).accepted
    local = TransportEpochConsensusCoordinator(
        coordinator_id="coordinator-1",
        transport=bus,
        base_coordinator=InMemoryEpochWatermarkCoordinator(),
        required_total_accepts=2,
        timeout_ms=100,
        reject_on_any_peer_reject=True,
    )
    peer = TransportEpochConsensusCoordinator(
        coordinator_id="coordinator-2",
        transport=bus,
        base_coordinator=peer_base,
        required_total_accepts=2,
        timeout_ms=100,
    )
    local.start()
    peer.start()

    decision = local.evaluate_commit(_make_commit("node-A:2", tick=2, epoch=1))
    assert decision.accepted is False
    assert "peer rejected epoch proposal" in str(decision.reason)


def test_transport_epoch_consensus_retries_before_timeout_reject():
    bus = InMemoryFabricBus()
    coordinator = TransportEpochConsensusCoordinator(
        coordinator_id="coordinator-1",
        transport=bus,
        base_coordinator=InMemoryEpochWatermarkCoordinator(),
        required_total_accepts=2,
        timeout_ms=20,
        max_attempts=3,
    )
    coordinator.start()
    decision = coordinator.evaluate_commit(_make_commit("node-A:1", tick=1))
    assert decision.accepted is False
    assert "attempt=3/3" in str(decision.reason)
    snap = coordinator.snapshot()
    stats = dict(snap["consensus"]["stats"])
    assert int(stats["proposals_total"]) == 3
    assert int(stats["timeouts"]) == 3
    assert int(stats["retries_total"]) == 2


def test_transport_epoch_consensus_rejects_mismatched_peer_vote_payload():
    bus = InMemoryFabricBus()
    local = TransportEpochConsensusCoordinator(
        coordinator_id="coordinator-1",
        transport=bus,
        base_coordinator=InMemoryEpochWatermarkCoordinator(),
        required_total_accepts=2,
        timeout_ms=100,
        reject_on_any_peer_reject=True,
    )
    local.start()

    def _malicious_peer(envelope: FabricEnvelope) -> None:
        if str(envelope.message_type) != "epoch_proposal":
            return
        payload = envelope.payload_inline if isinstance(envelope.payload_inline, dict) else {}
        proposal_id = str(payload.get("proposal_id", "")).strip()
        commit_ref = str(payload.get("commit_ref", "")).strip()
        if not proposal_id:
            return
        vote = FabricEnvelope(
            message_type="epoch_vote",
            channel=str(envelope.channel),
            mode=str(envelope.mode),
            sender="coordinator-malicious",
            recipient="coordinator-1",
            payload_ref=f"artifact://epoch/vote/{proposal_id}/coordinator-malicious",
            payload_inline={
                "proposal_id": proposal_id,
                "voter_id": "coordinator-malicious",
                "accepted": True,
                "reason": None,
                "epoch": 999,
                "watermark": 999,
                "tick": 999,
                "commit_ref": commit_ref,
            },
            trace_ref=str(envelope.trace_ref),
            commit_ref=commit_ref,
        )
        # Defer publish to avoid recursive publish-on-publish in the same call stack.
        time.sleep(0.001)
        bus.publish(vote)

    bus.subscribe("fabric.epoch", _malicious_peer, mode="realtime")
    decision = local.evaluate_commit(_make_commit("node-A:3", tick=3, epoch=3))
    assert decision.accepted is False
    assert "peer rejected epoch proposal" in str(decision.reason)
    assert "vote payload mismatch" in str(decision.reason)
    snap = local.snapshot()
    stats = dict(snap["consensus"]["stats"])
    assert int(stats["invalid_votes_total"]) >= 1

