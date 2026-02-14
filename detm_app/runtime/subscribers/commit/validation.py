from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from detm.runtime.fabric import validate_commit_paths

from detm_app.runtime.subscribers.common import _effective_storage_limit, _tail_limit


@dataclass
class CommitValidationReporter:
    """Writes local validator report with chain/proof and watermark checks."""

    out_dir: Path
    report_name: str = "commit_validation.json"
    history_name: str = "commit_validation_history.jsonl"
    realtime_name: str = "commits.jsonl"
    audit_name: str = "commits_audit.jsonl"
    retention_window: int = 0
    compaction_budget: int = 0
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        out_dir: Path,
        *,
        report_name: str = "commit_validation.json",
        history_name: str = "commit_validation_history.jsonl",
        realtime_name: str = "commits.jsonl",
        audit_name: str = "commits_audit.jsonl",
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "CommitValidationReporter":
        reporter = cls(
            out_dir=out_dir,
            report_name=str(report_name),
            history_name=str(history_name),
            realtime_name=str(realtime_name),
            audit_name=str(audit_name),
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        reporter._unsub_close = bus.add_event_listener_unsub("close", reporter.on_close)
        return reporter

    def on_close(self, **_rest: Any) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        realtime_path = self.out_dir / self.realtime_name
        audit_path = self.out_dir / self.audit_name
        report = validate_commit_paths(realtime_path=realtime_path, audit_path=audit_path)
        report["files"] = {
            "realtime_path": str(realtime_path),
            "audit_path": str(audit_path),
            "realtime_exists": bool(realtime_path.exists()),
            "audit_exists": bool(audit_path.exists()),
        }
        (self.out_dir / self.report_name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        history_path = self.out_dir / self.history_name
        with history_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False) + "\n")
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(history_path, max_entries=limit)
        self.detach()

    def detach(self) -> None:
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


__all__ = ["CommitValidationReporter"]
