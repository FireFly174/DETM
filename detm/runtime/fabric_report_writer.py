"""Runtime writer for fabric handshake artifacts and reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from detm.runtime.fabric_ack import ProofAck, TrustAck
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_quorum_report import FabricQuorumReportBuilder

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (artifact/report writing extracted from subscriber orchestration)
# - OOP_TECH_DEBT: distributed append-only writer and atomic multi-file checkpoints


class DeadLetterSource(Protocol):
    @property
    def dead_letters(self) -> list[dict[str, str]]:
        ...


def _effective_storage_limit(*, retention_window: int, compaction_budget: int) -> int:
    retention = max(0, int(retention_window))
    budget = max(0, int(compaction_budget))
    if retention > 0 and budget > 0:
        return min(retention, budget)
    return max(retention, budget)


@dataclass
class FabricRuntimeReportWriter:
    """Writes fabric ack/envelope/dead-letter artifacts and quorum report."""

    out_dir: Path
    ack_store: Mapping[str, ProofAck | TrustAck] | None = None
    ack_envelopes: Sequence[FabricEnvelope] | None = None
    delivery_ack_envelopes: Sequence[FabricEnvelope] | None = None
    quorum_report_builder: FabricQuorumReportBuilder | None = None
    service: DeadLetterSource | None = None
    commit_dead_letters: Sequence[dict[str, str]] | None = None
    acks_retention_window: int = 0
    acks_compaction_budget: int = 0
    ack_envelopes_retention_window: int = 0
    ack_envelopes_compaction_budget: int = 0
    delivery_acks_retention_window: int = 0
    delivery_acks_compaction_budget: int = 0
    dead_letters_retention_window: int = 0
    dead_letters_compaction_budget: int = 0
    quorum_report_retention_window: int = 0
    quorum_report_compaction_budget: int = 0
    quorum_report_history_name: str = "fabric_quorum_report_history.jsonl"

    def _limit_rows(
        self,
        rows: Sequence[dict[str, object]] | Sequence[dict[str, str]],
        *,
        retention_window: int,
        compaction_budget: int,
    ) -> list[dict[str, object]]:
        out = [dict(row) for row in list(rows)]
        limit = _effective_storage_limit(
            retention_window=int(retention_window),
            compaction_budget=int(compaction_budget),
        )
        if limit > 0 and len(out) > limit:
            return out[-limit:]
        return out

    def _write_jsonl_rows(self, path: Path, rows: Sequence[dict[str, object]]) -> None:
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in list(rows)),
            encoding="utf-8",
        )

    def _append_jsonl_row(
        self,
        path: Path,
        row: dict[str, object],
        *,
        retention_window: int,
        compaction_budget: int,
    ) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
        limit = _effective_storage_limit(
            retention_window=int(retention_window),
            compaction_budget=int(compaction_budget),
        )
        if limit <= 0:
            return
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(lines) <= limit:
            return
        path.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")

    def write_ack_artifacts(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        ack_rows = self._limit_rows(
            [ack.to_dict() for ack in list((self.ack_store or {}).values())],
            retention_window=int(self.acks_retention_window),
            compaction_budget=int(self.acks_compaction_budget),
        )
        env_rows = self._limit_rows(
            [env.to_dict() for env in list(self.ack_envelopes or [])],
            retention_window=int(self.ack_envelopes_retention_window),
            compaction_budget=int(self.ack_envelopes_compaction_budget),
        )
        delivery_ack_rows = self._limit_rows(
            [env.to_dict() for env in list(self.delivery_ack_envelopes or [])],
            retention_window=int(self.delivery_acks_retention_window),
            compaction_budget=int(self.delivery_acks_compaction_budget),
        )
        self._write_jsonl_rows(self.out_dir / "fabric_acks.jsonl", ack_rows)
        self._write_jsonl_rows(self.out_dir / "fabric_ack_envelopes.jsonl", env_rows)
        self._write_jsonl_rows(self.out_dir / "fabric_delivery_acks.jsonl", delivery_ack_rows)

    def build_quorum_report(
        self,
        *,
        replay_sample_stride: int,
        replay_checks_total: int,
        replay_checks_failed: int,
    ) -> dict[str, object]:
        if self.quorum_report_builder is None:
            return {}
        return self.quorum_report_builder.build(
            replay_sample_stride=int(replay_sample_stride),
            replay_checks_total=int(replay_checks_total),
            replay_checks_failed=int(replay_checks_failed),
        )

    def write_quorum_report(
        self,
        *,
        replay_sample_stride: int,
        replay_checks_total: int,
        replay_checks_failed: int,
    ) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        report = self.build_quorum_report(
            replay_sample_stride=int(replay_sample_stride),
            replay_checks_total=int(replay_checks_total),
            replay_checks_failed=int(replay_checks_failed),
        )
        (self.out_dir / "fabric_quorum_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._append_jsonl_row(
            self.out_dir / str(self.quorum_report_history_name),
            report,
            retention_window=int(self.quorum_report_retention_window),
            compaction_budget=int(self.quorum_report_compaction_budget),
        )

    def collect_dead_letters(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        if self.service is not None:
            out.extend(list(self.service.dead_letters))
        out.extend(list(self.commit_dead_letters or []))
        return out

    def write_dead_letters(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        dead_letters = self._limit_rows(
            self.collect_dead_letters(),
            retention_window=int(self.dead_letters_retention_window),
            compaction_budget=int(self.dead_letters_compaction_budget),
        )
        (self.out_dir / "fabric_dead_letters.json").write_text(
            json.dumps(dead_letters, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def write_all(
        self,
        *,
        replay_sample_stride: int,
        replay_checks_total: int,
        replay_checks_failed: int,
    ) -> None:
        self.write_ack_artifacts()
        self.write_quorum_report(
            replay_sample_stride=int(replay_sample_stride),
            replay_checks_total=int(replay_checks_total),
            replay_checks_failed=int(replay_checks_failed),
        )
        self.write_dead_letters()


__all__ = ["DeadLetterSource", "FabricRuntimeReportWriter"]
