from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from detm.runtime import api

from detm_app.runtime.subscribers.common import _effective_storage_limit


@dataclass
class TraceRecorder:
    """Collects step history and writes `history.jsonl` on close/finish."""

    out_dir: Path
    history: List[Dict[str, Any]]
    retention_window: int = 0
    compaction_budget: int = 0

    @classmethod
    def attach(
        cls,
        bus,
        out_dir: Path,
        *,
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "TraceRecorder":
        rec = cls(
            out_dir=out_dir,
            history=[],
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        bus.add_event_listener("step", rec.on_step)
        bus.add_event_listener("close", rec.on_close)
        return rec

    def on_step(
        self,
        *,
        observables: api.Observables,
        **_rest: Any,
    ) -> None:
        self.history.append(
            {
                "signature": observables.signature.as_dict(),
                "events": list(observables.events),
                "cost": dict(observables.cost),
                "quality": dict(observables.quality),
            }
        )

    def on_close(self, **_rest: Any) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / "history.jsonl"
        rows = list(self.history)
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            rows = rows[-limit:]
        path.write_text("\n".join(json.dumps(entry) for entry in rows), encoding="utf-8")


__all__ = ["TraceRecorder"]
