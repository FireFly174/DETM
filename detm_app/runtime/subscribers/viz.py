from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Callable

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.state import DETMState
from detm_app.transport import VizTransport

@dataclass
class VizStreamer:
    """Streams state updates to a VizTransport.

    For now we stream serialized state blobs; transports can choose how they
    deliver frames (tcp/shared memory/etc.).
    """

    transport: VizTransport
    every_steps: int = 1
    _last_sent_step: int = -1
    _commit_packets_total: int = 0
    _commit_packets_by_mode: Dict[str, int] = None  # type: ignore[assignment]
    _fabric_snapshot: Dict[str, Any] | None = None
    _unsub_reset: Callable[[], None] | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_commit: Callable[[], None] | None = None
    _unsub_fabric_snapshot: Callable[[], None] | None = None

    @classmethod
    def attach(cls, bus, transport: VizTransport, *, every_steps: int = 1) -> "VizStreamer":
        inst = cls(transport=transport, every_steps=max(1, int(every_steps)))
        inst._commit_packets_by_mode = {}
        inst._unsub_reset = bus.add_event_listener_unsub("reset", inst.on_reset)
        inst._unsub_step = bus.add_event_listener_unsub("step", inst.on_step)
        inst._unsub_commit = bus.add_event_listener_unsub("commit_packet", inst.on_commit_packet)
        inst._unsub_fabric_snapshot = bus.add_event_listener_unsub(
            "fabric_runtime_snapshot", inst.on_fabric_runtime_snapshot
        )
        return inst

    @staticmethod
    def _resolve_active_level(
        *,
        config: DETMConfig | None = None,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
    ) -> str | None:
        if policy_decision is not None:
            value = str(policy_decision.active_level or "").strip()
            if value:
                return value
        if level_policy is not None:
            value = str(level_policy.active_level or "").strip()
            if value:
                return value
        if config is not None:
            value = str(config.level_policy.active_level or "").strip()
            if value:
                return value
        return None

    def _maybe_send(
        self,
        state: DETMState,
        signature: api.DETMSignature,
        get_state_blob: Any | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> None:
        step_count = int(state.step_count)
        if self._last_sent_step >= 0 and (step_count - self._last_sent_step) < self.every_steps:
            return
        self._last_sent_step = step_count
        blob = get_state_blob() if callable(get_state_blob) else api.serialize(state)
        payload_meta = dict(meta) if meta else None
        try:
            self.transport.send_state(state_blob=blob, tick=step_count, signature=signature.vector, meta=payload_meta)
        except Exception:
            # Viz is best-effort: if a transport drops (daemon closed, socket error),
            # keep the simulation running and stop streaming further.
            self.detach()

    def on_reset(
        self,
        *,
        state: DETMState,
        config: DETMConfig | None = None,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
        get_state_blob: Any | None = None,
        **_rest: Any,
    ) -> None:
        self._last_sent_step = -1
        self._commit_packets_total = 0
        self._commit_packets_by_mode = {}
        self._fabric_snapshot = None
        active_level = self._resolve_active_level(
            config=config,
            level_policy=level_policy,
            policy_decision=policy_decision,
        )
        meta: dict[str, Any] = {}
        if active_level:
            meta["active_level"] = str(active_level)
        meta["commit_packets_total"] = int(self._commit_packets_total)
        meta["commit_packets_by_mode"] = dict(self._commit_packets_by_mode)
        self._maybe_send(
            state,
            api.digest(state),
            get_state_blob,
            meta=meta if meta else None,
        )

    def on_commit_packet(self, *, mode: str | None = None, **_rest: Any) -> None:
        self._commit_packets_total = int(self._commit_packets_total) + 1
        key = str(mode or "unknown").strip().lower() or "unknown"
        current = int(dict(self._commit_packets_by_mode or {}).get(key, 0))
        self._commit_packets_by_mode[key] = int(current + 1)

    def on_fabric_runtime_snapshot(self, *, snapshot: Dict[str, Any] | None = None, **_rest: Any) -> None:
        if isinstance(snapshot, dict):
            self._fabric_snapshot = dict(snapshot)

    def on_step(
        self,
        *,
        state: DETMState,
        observables: api.Observables,
        n_ticks: int = 0,
        requested_n_ticks: int = 0,
        step_requested_n_ticks: int = 0,
        step_effective_n_ticks: int = 0,
        config: DETMConfig | None = None,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
        get_state_blob: Any | None = None,
        **_rest: Any,
    ) -> None:
        active_level = self._resolve_active_level(
            config=config,
            level_policy=level_policy,
            policy_decision=policy_decision,
        )
        meta: dict[str, Any] = {}
        if active_level:
            meta["active_level"] = str(active_level)
        meta["chunk_n_ticks"] = int(n_ticks)
        meta["requested_n_ticks"] = int(requested_n_ticks or n_ticks)
        meta["step_requested_n_ticks"] = int(step_requested_n_ticks or requested_n_ticks or n_ticks)
        meta["step_effective_n_ticks"] = int(step_effective_n_ticks or n_ticks)
        meta["commit_packets_total"] = int(self._commit_packets_total)
        meta["commit_packets_by_mode"] = {str(k): int(v) for k, v in dict(self._commit_packets_by_mode).items()}
        if self._fabric_snapshot is not None:
            meta["fabric"] = dict(self._fabric_snapshot)
        self._maybe_send(
            state,
            observables.signature,
            get_state_blob,
            meta=meta,
        )

    def detach(self) -> None:
        if self._unsub_reset is not None:
            self._unsub_reset()
            self._unsub_reset = None
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_commit is not None:
            self._unsub_commit()
            self._unsub_commit = None
        if self._unsub_fabric_snapshot is not None:
            self._unsub_fabric_snapshot()
            self._unsub_fabric_snapshot = None

