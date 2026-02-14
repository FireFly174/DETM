from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict

from detm_app.runtime.subscribers.common import _effective_storage_limit, _tail_limit


@dataclass
class InvariantTickJsonlWriter:
    """Writes `invariants.jsonl` from `invariant_tick` events."""

    path: Path
    include_signature: bool = False
    retention_window: int = 0
    compaction_budget: int = 0
    _fh: Any | None = None
    _unsub_inv: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        include_signature: bool = False,
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "InvariantTickJsonlWriter":
        writer = cls(
            path=path,
            include_signature=bool(include_signature),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        writer._unsub_inv = bus.add_event_listener_unsub("invariant_tick", writer.on_invariant_tick)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def on_invariant_tick(self, **payload: Any) -> None:
        self._ensure()
        entry: Dict[str, Any] = {
            "type": "invariant_tick",
            "stream_id": payload.get("stream_id"),
            "l0_tick": payload.get("l0_tick"),
            "delta_l0_ticks": payload.get("delta_l0_ticks"),
            "dt_num": payload.get("dt_num"),
            "dt_den": payload.get("dt_den"),
            "time_num": payload.get("time_num"),
            "invariant_index": payload.get("invariant_index"),
            "phase_num": payload.get("phase_num"),
            "boundary_crossed": payload.get("boundary_crossed"),
        }

        if self.include_signature:
            obs = payload.get("observables")
            sig = getattr(obs, "signature", None) if obs is not None else None
            if sig is not None and hasattr(sig, "as_dict"):
                entry["signature"] = sig.as_dict()

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
        if self._unsub_inv is not None:
            self._unsub_inv()
            self._unsub_inv = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


__all__ = ["InvariantTickJsonlWriter"]
