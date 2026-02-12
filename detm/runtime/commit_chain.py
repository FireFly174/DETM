"""Stateful commit chain manager for node/fabric sequencing."""

from __future__ import annotations

from dataclasses import replace

from detm.runtime.commit_packet import CommitPacket

# ARCH-MARKERS:
# - LAYER_BAND: L4-L5
# - ABSTRACT_DISTANCE: 0 (single-node chain lifecycle class complete for MVP)
# - OOP_TECH_DEBT: multi-parent/reorg strategy for distributed conflict resolution


class CommitChainManager:
    """Maintains ordered commit lineage (`tail -> parent_ref`) for one node."""

    def __init__(self, *, node_id: str | None = None) -> None:
        self._node_id = node_id
        self._tail_ref: str | None = None
        self._last_tick: int | None = None
        self._seen_commit_ids: set[str] = set()

    @property
    def node_id(self) -> str | None:
        return self._node_id

    @property
    def tail_ref(self) -> str | None:
        return self._tail_ref

    @property
    def last_tick(self) -> int | None:
        return self._last_tick

    def sequence(self, packet: CommitPacket, *, parent_ref: str | None = None) -> CommitPacket:
        """Attach canonical parent link and accept packet into the chain."""

        expected_parent = self._tail_ref if parent_ref is None else parent_ref
        sequenced = replace(packet, parent_ref=expected_parent)
        self.accept(sequenced)
        return sequenced

    def verify(self, packet: CommitPacket) -> tuple[bool, str | None]:
        if self._node_id is not None and packet.node_id != self._node_id:
            return False, f"node mismatch: expected {self._node_id}, got {packet.node_id}"
        if packet.commit_id in self._seen_commit_ids:
            return False, f"duplicate commit_id: {packet.commit_id}"
        if self._tail_ref is None:
            if packet.parent_ref is not None:
                return False, "first packet parent_ref must be null"
        elif packet.parent_ref != self._tail_ref:
            return False, f"parent mismatch: expected {self._tail_ref}, got {packet.parent_ref}"
        if self._last_tick is not None and packet.tick_ref.tick < self._last_tick:
            return False, f"tick must be monotonic: {packet.tick_ref.tick} < {self._last_tick}"
        return True, None

    def accept(self, packet: CommitPacket) -> None:
        is_valid, reason = self.verify(packet)
        if not is_valid:
            raise ValueError(reason or "invalid commit packet")
        if self._node_id is None:
            self._node_id = packet.node_id
        self._tail_ref = packet.commit_id
        self._last_tick = packet.tick_ref.tick
        self._seen_commit_ids.add(packet.commit_id)


__all__ = ["CommitChainManager"]
