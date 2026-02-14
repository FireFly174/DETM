"""Runtime adapter for commit/ack artifact storage and replay resolution."""

from __future__ import annotations

from dataclasses import dataclass, field

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FileFabricArtifactStore

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (artifact resolve/write/replay adapter extracted from subscriber logic)
# - OOP_TECH_DEBT: replicated artifact resolver and distributed replay witness checks


@dataclass
class FabricArtifactResolver:
    """Resolves and persists commit/ack artifacts with replay-check bookkeeping."""

    node_id: str
    artifact_store: FileFabricArtifactStore | None = None
    commit_store: dict[str, CommitPacket] = field(default_factory=dict)
    commit_ref_index: dict[str, str] = field(default_factory=dict)
    ack_store: dict[str, ProofAck | TrustAck] = field(default_factory=dict)
    replay_checks_total: int = 0
    replay_checks_failed: int = 0

    def remember_commit(self, packet: CommitPacket, payload_ref: str) -> str:
        pref = str(payload_ref)
        if self.artifact_store is not None:
            pref = self.artifact_store.write_commit(packet, artifact_ref=pref)
        self.commit_store[pref] = packet
        self.commit_ref_index[str(packet.commit_id)] = pref
        return pref

    def resolve_commit(self, payload_ref: str) -> CommitPacket | None:
        pref = str(payload_ref)
        packet = self.commit_store.get(pref)
        if packet is not None:
            return packet
        if self.artifact_store is not None:
            return self.artifact_store.read_commit(pref)
        return None

    def write_ack(self, ack: ProofAck | TrustAck) -> str:
        ref = f"artifact://ack/{self.node_id}/{len(self.ack_store) + 1}"
        if self.artifact_store is not None:
            ref = self.artifact_store.write_ack(ack, artifact_ref=ref)
        self.ack_store[ref] = ack
        return ref

    def resolve_ack(self, payload_ref: str) -> ProofAck | TrustAck | None:
        pref = str(payload_ref)
        ack = self.ack_store.get(pref)
        if ack is not None:
            return ack
        if self.artifact_store is not None:
            return self.artifact_store.read_ack(pref)
        return None

    def replay_check(self, packet: CommitPacket) -> tuple[bool, str | None]:
        self.replay_checks_total += 1
        commit_id = str(packet.commit_id)
        payload_ref = self.commit_ref_index.get(commit_id)
        if payload_ref is None:
            self.replay_checks_failed += 1
            return False, f"replay source not found for commit_id={commit_id}"
        restored = self.resolve_commit(payload_ref)
        if restored is None:
            self.replay_checks_failed += 1
            return False, f"replay payload missing for payload_ref={payload_ref}"
        if restored.to_dict() != packet.to_dict():
            self.replay_checks_failed += 1
            return False, "replay mismatch: restored payload differs from commit packet"
        return True, None

    def replay_snapshot(self) -> dict[str, int]:
        return {
            "checks_total": int(self.replay_checks_total),
            "checks_failed": int(self.replay_checks_failed),
        }


__all__ = ["FabricArtifactResolver"]


