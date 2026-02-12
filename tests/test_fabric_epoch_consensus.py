from __future__ import annotations

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric_epoch import InMemoryEpochWatermarkCoordinator
from detm.runtime.fabric_epoch_consensus import TransportEpochConsensusCoordinator
from detm.runtime.fabric_transport import InMemoryFabricBus


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
