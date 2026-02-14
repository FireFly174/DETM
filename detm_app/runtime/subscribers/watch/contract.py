from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from detm.runtime import api
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.outerfields import compute_outerfields_v1
from detm.runtime.state import DETMState
from detm.runtime.watch_contract import WatchContractPacket

from detm_app.runtime.subscribers.common import _effective_storage_limit, _tail_limit, _to_numpy
from detm_app.runtime.subscribers.watch.flow import build_watch_contract_packet, resolve_policy_decision


@dataclass
class WatchContractWriter:
    """Writes `watch_contract.jsonl` + `outerfields/*.npz` projection artifacts."""

    path: Path
    outerfields_dir: Path
    level_src: str = "L0"
    base_level: str = "L0"
    retention_window: int = 0
    compaction_budget: int = 0
    outerfields_retention_window: int | None = None
    outerfields_compaction_budget: int | None = None
    _fh: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        outerfields_dir: Path | None = None,
        level_src: str = "L0",
        base_level: str = "L0",
        retention_window: int = 0,
        compaction_budget: int = 0,
        outerfields_retention_window: int | None = None,
        outerfields_compaction_budget: int | None = None,
    ) -> "WatchContractWriter":
        writer = cls(
            path=path,
            outerfields_dir=(
                Path(outerfields_dir)
                if outerfields_dir is not None
                else (Path(path).parent / "outerfields")
            ),
            level_src=str(level_src),
            base_level=str(base_level),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
            outerfields_retention_window=None
            if outerfields_retention_window is None
            else max(0, int(outerfields_retention_window)),
            outerfields_compaction_budget=None
            if outerfields_compaction_budget is None
            else max(0, int(outerfields_compaction_budget)),
        )
        writer._unsub_step = bus.add_event_listener_unsub("step", writer.on_step)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.outerfields_dir.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def _save_outerfields(self, *, tick: int, outerfields: Any) -> str:
        artifact_path = self.outerfields_dir / f"outerfields_{int(tick):09d}.npz"
        meta_json = json.dumps(dict(getattr(outerfields, "meta", {}) or {}), ensure_ascii=False)
        np.savez_compressed(
            artifact_path,
            dir_x=_to_numpy(outerfields.dir_x).astype(np.float32, copy=False),
            dir_y=_to_numpy(outerfields.dir_y).astype(np.float32, copy=False),
            strength=_to_numpy(outerfields.strength).astype(np.float32, copy=False),
            stability=_to_numpy(outerfields.stability).astype(np.float32, copy=False),
            instability=_to_numpy(outerfields.instability).astype(np.float32, copy=False),
            boundary_activity=_to_numpy(outerfields.boundary_activity).astype(np.float32, copy=False),
            capacity_violation_density=_to_numpy(outerfields.capacity_violation_density).astype(
                np.float32,
                copy=False,
            ),
            meta_json=np.asarray([meta_json]),
        )
        try:
            rel = artifact_path.relative_to(self.path.parent)
            return rel.as_posix()
        except Exception:
            return str(artifact_path)

    def _prune_outerfields(self, *, max_entries: int) -> None:
        limit = max(0, int(max_entries))
        if limit <= 0 or not self.outerfields_dir.exists():
            return
        rows = sorted(self.outerfields_dir.glob("outerfields_*.npz"), key=lambda p: p.name)
        excess = len(rows) - limit
        if excess <= 0:
            return
        for row in rows[:excess]:
            try:
                row.unlink(missing_ok=True)
            except Exception:
                continue

    def _apply_storage_limit(self) -> None:
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)
        outer_limit = _effective_storage_limit(
            retention_window=(
                int(self.retention_window)
                if self.outerfields_retention_window is None
                else int(self.outerfields_retention_window)
            ),
            compaction_budget=(
                int(self.compaction_budget)
                if self.outerfields_compaction_budget is None
                else int(self.outerfields_compaction_budget)
            ),
        )
        if outer_limit > 0:
            self._prune_outerfields(max_entries=outer_limit)

    def on_step(
        self,
        *,
        state: DETMState,
        n_ticks: int,
        requested_n_ticks: int = 0,
        observables: api.Observables,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
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

        tick = int(state.step_count)
        outerfields = compute_outerfields_v1(
            energy=state.field_state.energy,
            entropy=state.field_state.entropy,
            internal_time=state.field_state.internal_time,
        )

        self._ensure()
        uri = self._save_outerfields(tick=tick, outerfields=outerfields)
        packet: WatchContractPacket = build_watch_contract_packet(
            state=state,
            observables=observables,
            policy_decision=policy_decision,
            n_ticks=int(n_ticks),
            level_src=str(self.level_src),
            base_level=str(self.base_level),
            uri=str(uri),
            schema=str((outerfields.meta or {}).get("schema", "OUTERFIELDS_V1")),
        )

        assert self._fh is not None
        self._fh.write(json.dumps(packet.to_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()
        self._apply_storage_limit()

    def on_close(self, **_rest: Any) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        self._apply_storage_limit()
        self.detach()

    def detach(self) -> None:
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


__all__ = ["WatchContractWriter"]
