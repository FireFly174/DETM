from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from detm.runtime import api
from detm.runtime.influence import DETMInfluence
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.state import DETMState
from detm.metrics.base import MetricPlugin
from detm.metrics.builtin import default_metric_plugins

from detm_app.runtime.subscribers.common import _effective_storage_limit, _tail_limit
from detm_app.runtime.subscribers.trace.flow import (
    build_trace_entry,
    compute_plugin_metrics,
    filter_events,
    resolve_policy_decision,
)


@dataclass
class JsonlTraceWriter:
    """Writes canonical `System Trace` (`trace.jsonl`) from `step` events."""

    path: Path
    metric_plugins: Sequence[MetricPlugin]
    retention_window: int = 0
    compaction_budget: int = 0
    _fh: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        metric_plugins: Sequence[MetricPlugin] | None = None,
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "JsonlTraceWriter":
        writer = cls(
            path=path,
            metric_plugins=list(metric_plugins or default_metric_plugins()),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
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
        if not bool(policy_decision.commit_boundary_crossed):
            return

        self._ensure()
        detail_mode = policy_decision.observability_profile.normalized_detail_mode()
        filtered_events = filter_events(observables=observables, policy_decision=policy_decision)
        metrics = compute_plugin_metrics(
            metric_plugins=self.metric_plugins,
            state=state,
            observables=observables,
            filtered_events=filtered_events,
            influence=influence,
            n_ticks=int(n_ticks),
            get_state_blob=get_state_blob,
            detail_mode=detail_mode,
        )
        entry = build_trace_entry(
            state=state,
            influence=influence,
            n_ticks=int(n_ticks),
            requested_n_ticks=int(requested_n_ticks),
            step_requested_n_ticks=int(step_requested_n_ticks),
            step_effective_n_ticks=int(step_effective_n_ticks),
            observables=observables,
            filtered_events=filtered_events,
            metrics=metrics,
            detail_mode=detail_mode,
            policy_decision=policy_decision,
        )
        assert self._fh is not None
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)

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


SystemTraceWriter = JsonlTraceWriter

__all__ = ["JsonlTraceWriter", "SystemTraceWriter"]
