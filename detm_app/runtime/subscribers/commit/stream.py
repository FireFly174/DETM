from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from detm.runtime import api
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.state import DETMState

from detm_app.runtime.subscribers.commit.flow import (
    build_commit_packet,
    publish_commit_packet_event,
    resolve_policy_decision,
    should_emit_commit,
)
from detm_app.runtime.subscribers.common import _effective_storage_limit, _tail_limit


@dataclass
class CommitJsonlWriter:
    """Writes streaming `commits.jsonl` packets linked to `trace_ref`."""

    path: Path
    node_id: str = "local"
    commit_type: str = "state"
    mode: str = "realtime"
    retention_window: int = 0
    compaction_budget: int = 0
    _fh: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None
    _last_commit_id: str | None = None
    _bus: Any | None = None

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        node_id: str = "local",
        commit_type: str = "state",
        mode: str = "realtime",
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "CommitJsonlWriter":
        writer = cls(
            path=path,
            node_id=str(node_id),
            commit_type=str(commit_type),
            mode=str(mode),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        writer._bus = bus
        writer._unsub_step = bus.add_event_listener_unsub("step", writer.on_step)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def on_step(
        self,
        *,
        state: DETMState,
        influence: DETMInfluence | None,
        n_ticks: int,
        requested_n_ticks: int = 0,
        step_requested_n_ticks: int = 0,
        step_effective_n_ticks: int = 0,
        observables: api.Observables,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
        get_state_blob: Any | None = None,
        **_rest: Any,
    ) -> None:
        policy_decision = resolve_policy_decision(
            state=state,
            n_ticks=int(n_ticks),
            requested_n_ticks=int(requested_n_ticks),
            level_policy=level_policy,
            policy_decision=policy_decision,
        )
        tick = int(state.step_count)
        if not should_emit_commit(mode=str(self.mode), tick=tick, policy_decision=policy_decision):
            return

        packet, trace_ref, commit_id = build_commit_packet(
            state=state,
            influence=influence,
            n_ticks=int(n_ticks),
            requested_n_ticks=int(requested_n_ticks),
            step_requested_n_ticks=int(step_requested_n_ticks),
            step_effective_n_ticks=int(step_effective_n_ticks),
            observables=observables,
            policy_decision=policy_decision,
            node_id=str(self.node_id),
            commit_type=str(self.commit_type),
            mode=str(self.mode),
            last_commit_id=self._last_commit_id,
            get_state_blob=get_state_blob,
        )

        self._ensure()
        assert self._fh is not None
        self._fh.write(json.dumps(packet.to_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)
        self._last_commit_id = commit_id
        if self._bus is not None:
            publish_commit_packet_event(
                bus=self._bus,
                packet=packet,
                node_id=str(self.node_id),
                commit_type=str(self.commit_type),
                mode=str(self.mode),
                trace_ref=trace_ref,
            )

    def on_close(self, **_rest: Any) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)
        self.detach()

    def detach(self) -> None:
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


__all__ = ["CommitJsonlWriter"]
