"""In-memory epoch/watermark coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric.epoch.contracts import EpochDecision
from detm.runtime.fabric.epoch.operations import commit_epoch, commit_watermark


@dataclass
class InMemoryEpochWatermarkCoordinator:
    """In-memory monotonic epoch/watermark coordinator (MVP)."""

    enforce_monotonic_tick: bool = True
    enforce_monotonic_epoch: bool = True
    enforce_monotonic_watermark: bool = True
    enforce_watermark_le_epoch: bool = True
    _node_state: Dict[str, Dict[str, int]] = field(default_factory=dict)
    _global_epoch: int | None = None
    _global_watermark: int | None = None

    def evaluate_commit(self, packet: CommitPacket) -> EpochDecision:
        node_id = str(packet.node_id)
        tick = int(packet.tick_ref.tick)
        epoch = int(commit_epoch(packet))
        watermark = int(commit_watermark(packet))
        if self.enforce_watermark_le_epoch and watermark > epoch:
            return EpochDecision(
                accepted=False,
                reason=f"watermark {watermark} cannot exceed epoch {epoch}",
                epoch=epoch,
                watermark=watermark,
                tick=tick,
            )

        prev = self._node_state.get(node_id)
        if prev is not None:
            prev_tick = int(prev.get("tick", -1))
            prev_epoch = int(prev.get("epoch", -1))
            prev_watermark = int(prev.get("watermark", -1))
            if self.enforce_monotonic_tick and tick <= prev_tick:
                return EpochDecision(
                    accepted=False,
                    reason=f"tick regression for {node_id}: prev={prev_tick}, got={tick}",
                    epoch=epoch,
                    watermark=watermark,
                    tick=tick,
                )
            if self.enforce_monotonic_epoch and epoch < prev_epoch:
                return EpochDecision(
                    accepted=False,
                    reason=f"epoch regression for {node_id}: prev={prev_epoch}, got={epoch}",
                    epoch=epoch,
                    watermark=watermark,
                    tick=tick,
                )
            if self.enforce_monotonic_watermark and watermark < prev_watermark:
                return EpochDecision(
                    accepted=False,
                    reason=f"watermark regression for {node_id}: prev={prev_watermark}, got={watermark}",
                    epoch=epoch,
                    watermark=watermark,
                    tick=tick,
                )

        self._node_state[node_id] = {"tick": tick, "epoch": epoch, "watermark": watermark}
        self._recompute_global_state()
        return EpochDecision(accepted=True, reason=None, epoch=epoch, watermark=watermark, tick=tick)

    def _recompute_global_state(self) -> None:
        if not self._node_state:
            self._global_epoch = None
            self._global_watermark = None
            return
        epochs = [int(row["epoch"]) for row in self._node_state.values()]
        watermarks = [int(row["watermark"]) for row in self._node_state.values()]
        self._global_epoch = max(epochs) if epochs else None
        self._global_watermark = min(watermarks) if watermarks else None

    def snapshot(self) -> Dict[str, Any]:
        nodes = {
            str(node_id): {
                "tick": int(row.get("tick", 0)),
                "epoch": int(row.get("epoch", 0)),
                "watermark": int(row.get("watermark", 0)),
            }
            for node_id, row in sorted(self._node_state.items())
        }
        return {
            "node_count": len(nodes),
            "global": {"epoch": self._global_epoch, "watermark": self._global_watermark},
            "nodes": nodes,
        }

    def load_snapshot(self, payload: Dict[str, Any]) -> None:
        raw_nodes = payload.get("nodes")
        nodes: Dict[str, Dict[str, int]] = {}
        if isinstance(raw_nodes, dict):
            for node_id, row in raw_nodes.items():
                if not isinstance(row, dict):
                    continue
                nodes[str(node_id)] = {
                    "tick": int(row.get("tick", 0)),
                    "epoch": int(row.get("epoch", 0)),
                    "watermark": int(row.get("watermark", 0)),
                }
        self._node_state = nodes
        self._recompute_global_state()


__all__ = ["InMemoryEpochWatermarkCoordinator"]

