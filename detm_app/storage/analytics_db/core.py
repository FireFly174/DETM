"""Post-run SQLite analytics ingest for DETM artifact-first runs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IngestIssue:
    severity: str
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "details": {} if self.details is None else dict(self.details),
        }


@dataclass(frozen=True)
class IngestReport:
    run_id: str
    db_path: Path
    status: str
    ticks_ingested: int
    events_ingested: int
    decisions_ingested: int
    outerfields_refs_ingested: int
    issues: list[IngestIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "db_path": str(self.db_path),
            "status": self.status,
            "ticks_ingested": int(self.ticks_ingested),
            "events_ingested": int(self.events_ingested),
            "decisions_ingested": int(self.decisions_ingested),
            "outerfields_refs_ingested": int(self.outerfields_refs_ingested),
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    run_dir: Path
    status: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


def _row_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def open_run_db(run_dir: Path) -> sqlite3.Connection:
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(run_path / "analytics.sqlite")
    conn.row_factory = sqlite3.Row
    return conn


def ingest_run(run_dir: Path) -> IngestReport:
    run_path = Path(run_dir)
    analytics_dir = run_path / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)

    issues: list[IngestIssue] = []
    config_path = run_path / "config.json"
    config_payload = _read_json(config_path, issues=issues, required=True, code="missing_config")
    if config_payload is None:
        run_id = _derive_run_id(run_path, None, None)
        report = IngestReport(
            run_id=run_id,
            db_path=run_path / "analytics.sqlite",
            status="broken",
            ticks_ingested=0,
            events_ingested=0,
            decisions_ingested=0,
            outerfields_refs_ingested=0,
            issues=issues,
        )
        with open_run_db(run_path) as conn:
            _ensure_schema(conn)
            _replace_run_rows(
                conn=conn,
                run_id=run_id,
                status="broken",
                run_path=run_path,
                config_payload={},
                digest_payload=None,
                counts={"tick_count": 0, "eventful_tick_count": 0, "decision_tick_count": 0, "outerfields_file_count": 0},
                created_at_ms=None,
                completed_at_ms=None,
                issues=issues,
            )
        return report

    digest_payload = _read_json(run_path / "digest.json", issues=issues, required=False, code="missing_digest")
    trace_rows = _read_jsonl(run_path / "trace.jsonl", issues=issues, required=False, code="missing_trace")
    commits_rows = _read_jsonl(run_path / "commits.jsonl", issues=issues, required=False, code="missing_commits")
    commit_validation_payload = _read_json(
        run_path / "commit_validation.json", issues=issues, required=False, code="missing_commit_validation"
    )
    watch_trace_enabled = bool(config_payload.get("watch_trace_enabled", False))
    watch_rows = _read_jsonl(
        run_path / "watch_trace.jsonl",
        issues=issues,
        required=watch_trace_enabled,
        code="missing_watch_trace",
    )
    contract_rows = _read_jsonl(
        run_path / "watch_contract.jsonl",
        issues=issues,
        required=watch_trace_enabled,
        code="missing_watch_contract",
    )
    decision_rows = _read_jsonl(
        run_path / "operator_decisions.jsonl",
        issues=issues,
        required=watch_trace_enabled,
        code="missing_operator_decisions",
    )
    multiscale_candidates_rows = _read_jsonl(
        run_path / "multiscale_candidates.jsonl",
        issues=issues,
        required=False,
        code="missing_multiscale_candidates",
    )
    bridge_record_sources_rows = _read_jsonl(
        run_path / "bridge_record_sources.jsonl",
        issues=issues,
        required=False,
        code="missing_bridge_record_sources",
    )
    scale_tension_rows = _read_jsonl(
        run_path / "scale_tension.jsonl",
        issues=issues,
        required=False,
        code="missing_scale_tension",
    )
    operator_catalog_hits_rows = _read_jsonl(
        run_path / "operator_catalog_hits.jsonl",
        issues=issues,
        required=False,
        code="missing_operator_catalog_hits",
    )

    run_id = _derive_run_id(run_path, config_payload, commits_rows)
    ticks_data = _build_tick_rows(
        trace_rows=trace_rows,
        watch_rows=watch_rows,
        contract_rows=contract_rows,
        decision_rows=decision_rows,
        commits_rows=commits_rows,
    )
    ticks = sorted(ticks_data.keys())
    created_at_ms, completed_at_ms = _commit_time_bounds(commits_rows)
    if not ticks:
        issues.append(
            IngestIssue(
                severity="error",
                code="no_ticks_found",
                message="Run does not contain any tick-level artifacts suitable for analytics ingest",
                details={"run_dir": str(run_path)},
            )
        )

    outerfields_rows, outerfields_total_bytes = _build_outerfields_rows(
        run_path=run_path,
        contract_rows=contract_rows,
        issues=issues,
    )
    artifact_rows = _build_artifact_rows(
        run_path=run_path,
        config_payload=config_payload,
        digest_payload=digest_payload,
        trace_rows=trace_rows,
        watch_rows=watch_rows,
        contract_rows=contract_rows,
        decision_rows=decision_rows,
        commits_rows=commits_rows,
        commit_validation_payload=commit_validation_payload,
        outerfields_rows=outerfields_rows,
        multiscale_candidates_rows=multiscale_candidates_rows,
        bridge_record_sources_rows=bridge_record_sources_rows,
        scale_tension_rows=scale_tension_rows,
        operator_catalog_hits_rows=operator_catalog_hits_rows,
    )
    operator_rows = _build_operator_rows(decision_rows)

    counts = {
        "tick_count": len(ticks),
        "eventful_tick_count": sum(1 for row in ticks_data.values() if int(row["event_count"]) > 0),
        "decision_tick_count": len(operator_rows),
        "outerfields_file_count": len(outerfields_rows),
    }
    if counts["outerfields_file_count"] >= counts["tick_count"] and counts["tick_count"] >= 50:
        issues.append(
            IngestIssue(
                severity="warning",
                code="outerfields_density_high",
                message="Per-tick outerfields artifact density is high for this run",
                details={
                    "outerfields_file_count": counts["outerfields_file_count"],
                    "tick_count": counts["tick_count"],
                },
            )
        )

    status = _status_from_issues(issues)
    summary_payload = _build_run_summary_payload(
        run_id=run_id,
        run_path=run_path,
        status=status,
        config_payload=config_payload,
        digest_payload=digest_payload,
        commit_validation_payload=commit_validation_payload,
        ticks_data=ticks_data,
        operator_rows=operator_rows,
        outerfields_rows=outerfields_rows,
        outerfields_total_bytes=outerfields_total_bytes,
        multiscale_candidates_rows=multiscale_candidates_rows,
        bridge_record_sources_rows=bridge_record_sources_rows,
        scale_tension_rows=scale_tension_rows,
        operator_catalog_hits_rows=operator_catalog_hits_rows,
        created_at_ms=created_at_ms,
        completed_at_ms=completed_at_ms,
        issues=issues,
    )

    with open_run_db(run_path) as conn:
        _ensure_schema(conn)
        _purge_run(conn, run_id)
        _insert_run_row(
            conn=conn,
            run_id=run_id,
            run_path=run_path,
            config_payload=config_payload,
            digest_payload=digest_payload,
            created_at_ms=created_at_ms,
            completed_at_ms=completed_at_ms,
            counts=counts,
            status=status,
        )
        _insert_tick_rows(conn, run_id, ticks_data)
        _insert_operator_rows(conn, run_id, operator_rows)
        _insert_artifact_rows(conn, run_id, artifact_rows)
        _insert_issues(conn, run_id, issues)
        conn.commit()

    _write_json(analytics_dir / "run_summary.json", summary_payload)
    _write_jsonl(
        analytics_dir / "event_windows.jsonl",
        [
            _build_event_window_row(row)
            for row in sorted(ticks_data.values(), key=lambda item: int(item["tick"]))
            if int(row["event_count"]) > 0
        ],
    )
    _write_jsonl(
        analytics_dir / "decision_windows.jsonl",
        [
            _build_decision_window_row(row)
            for row in sorted(operator_rows, key=lambda item: int(item["tick"]))
            if int(row["decision_count"]) > 0
        ],
    )
    _write_jsonl(analytics_dir / "outerfields_index.jsonl", outerfields_rows)

    return IngestReport(
        run_id=run_id,
        db_path=run_path / "analytics.sqlite",
        status=status,
        ticks_ingested=counts["tick_count"],
        events_ingested=sum(int(row["event_count"]) for row in ticks_data.values()),
        decisions_ingested=sum(int(row["decision_count"]) for row in operator_rows),
        outerfields_refs_ingested=len(outerfields_rows),
        issues=issues,
    )


def summarize_run(run_dir: Path) -> RunSummary:
    report = ingest_run(run_dir)
    analytics_dir = Path(run_dir) / "analytics"
    payload = json.loads((analytics_dir / "run_summary.json").read_text(encoding="utf-8"))
    return RunSummary(
        run_id=report.run_id,
        run_dir=Path(run_dir),
        status=report.status,
        payload=payload,
    )


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            run_dir TEXT NOT NULL,
            created_at_ms INTEGER,
            completed_at_ms INTEGER,
            config_json TEXT NOT NULL,
            digest_json TEXT,
            backend TEXT,
            device TEXT,
            shape_json TEXT,
            watch_trace_enabled INTEGER NOT NULL,
            record_fields INTEGER NOT NULL,
            tick_count INTEGER NOT NULL,
            eventful_tick_count INTEGER NOT NULL,
            decision_tick_count INTEGER NOT NULL,
            outerfields_file_count INTEGER NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tick_summary (
            run_id TEXT NOT NULL,
            tick INTEGER NOT NULL,
            trace_ref TEXT,
            event_count INTEGER,
            event_types_json TEXT,
            refinement_count INTEGER,
            influence_count INTEGER,
            operator_decision_count INTEGER,
            operator_reuse_rate REAL,
            cpu_time_ms REAL,
            step_ops_estimate REAL,
            memory_bytes_estimate REAL,
            energy_mean REAL,
            energy_var REAL,
            entropy_mean REAL,
            internal_time_mean REAL,
            oscillation_score REAL,
            saturation_score REAL,
            runtime_adaptive_window_active INTEGER,
            runtime_adaptive_profile TEXT,
            anti_goodhart_flag INTEGER,
            anti_goodhart_degraded_signal_count INTEGER,
            exploration_horizon_ticks INTEGER,
            horizon_break_reason TEXT,
            outerfields_uri TEXT,
            PRIMARY KEY (run_id, tick)
        );
        CREATE TABLE IF NOT EXISTS operator_panel (
            run_id TEXT NOT NULL,
            tick INTEGER NOT NULL,
            decision_count INTEGER,
            reuse_count INTEGER,
            search_count INTEGER,
            hold_rate REAL,
            operator_reuse REAL,
            transferability REAL,
            torsion_flag_rate REAL,
            torsion_health REAL,
            acceptance_passed INTEGER,
            failed_signals_json TEXT,
            goodhart_flag INTEGER,
            goodhart_target_signal TEXT,
            goodhart_target_delta REAL,
            goodhart_degraded_signals_json TEXT,
            policy_reaction_apply INTEGER,
            policy_reaction_actions_json TEXT,
            PRIMARY KEY (run_id, tick)
        );
        CREATE TABLE IF NOT EXISTS artifact_refs (
            run_id TEXT NOT NULL,
            artifact_kind TEXT NOT NULL,
            tick INTEGER NOT NULL,
            path TEXT NOT NULL,
            trace_ref TEXT,
            schema TEXT,
            size_bytes INTEGER,
            sha256 TEXT,
            meta_json TEXT,
            PRIMARY KEY (run_id, artifact_kind, tick)
        );
        CREATE TABLE IF NOT EXISTS run_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            severity TEXT,
            code TEXT,
            message TEXT,
            details_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tick_summary_run_tick ON tick_summary(run_id, tick);
        CREATE INDEX IF NOT EXISTS idx_tick_summary_run_event_count_tick ON tick_summary(run_id, event_count, tick);
        CREATE INDEX IF NOT EXISTS idx_tick_summary_run_goodhart_tick ON tick_summary(run_id, anti_goodhart_flag, tick);
        CREATE INDEX IF NOT EXISTS idx_tick_summary_run_runtime_window_tick
            ON tick_summary(run_id, runtime_adaptive_window_active, tick);
        CREATE INDEX IF NOT EXISTS idx_operator_panel_run_acceptance_tick
            ON operator_panel(run_id, acceptance_passed, tick);
        CREATE INDEX IF NOT EXISTS idx_artifact_refs_run_kind_tick ON artifact_refs(run_id, artifact_kind, tick);
        """
    )


def _purge_run(conn: sqlite3.Connection, run_id: str) -> None:
    for table in ("tick_summary", "operator_panel", "artifact_refs", "run_issues", "runs"):
        conn.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))


def _insert_run_row(
    *,
    conn: sqlite3.Connection,
    run_id: str,
    run_path: Path,
    config_payload: dict[str, Any],
    digest_payload: dict[str, Any] | None,
    created_at_ms: int | None,
    completed_at_ms: int | None,
    counts: dict[str, int],
    status: str,
) -> None:
    shape = config_payload.get("shape")
    if shape is None and config_payload.get("width") is not None and config_payload.get("height") is not None:
        shape = [config_payload.get("height"), config_payload.get("width")]
    conn.execute(
        """
        INSERT INTO runs (
            run_id, run_dir, created_at_ms, completed_at_ms, config_json, digest_json, backend, device, shape_json,
            watch_trace_enabled, record_fields, tick_count, eventful_tick_count, decision_tick_count,
            outerfields_file_count, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            str(run_path),
            created_at_ms,
            completed_at_ms,
            json.dumps(config_payload, ensure_ascii=False, sort_keys=True),
            None if digest_payload is None else json.dumps(digest_payload, ensure_ascii=False, sort_keys=True),
            config_payload.get("backend"),
            config_payload.get("device"),
            json.dumps(shape, ensure_ascii=False),
            int(bool(config_payload.get("watch_trace_enabled", False))),
            int((run_path / "fields_hist.npz").exists()),
            int(counts["tick_count"]),
            int(counts["eventful_tick_count"]),
            int(counts["decision_tick_count"]),
            int(counts["outerfields_file_count"]),
            status,
        ),
    )


def _replace_run_rows(
    *,
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    run_path: Path,
    config_payload: dict[str, Any],
    digest_payload: dict[str, Any] | None,
    counts: dict[str, int],
    created_at_ms: int | None,
    completed_at_ms: int | None,
    issues: list[IngestIssue],
) -> None:
    _purge_run(conn, run_id)
    _insert_run_row(
        conn=conn,
        run_id=run_id,
        run_path=run_path,
        config_payload=config_payload,
        digest_payload=digest_payload,
        created_at_ms=created_at_ms,
        completed_at_ms=completed_at_ms,
        counts=counts,
        status=status,
    )
    _insert_issues(conn, run_id, issues)
    conn.commit()


def _insert_tick_rows(conn: sqlite3.Connection, run_id: str, tick_rows: dict[int, dict[str, Any]]) -> None:
    rows = []
    for tick, row in sorted(tick_rows.items()):
        rows.append(
            (
                run_id,
                int(tick),
                row["trace_ref"],
                int(row["event_count"]),
                json.dumps(row["event_types"], ensure_ascii=False),
                row["refinement_count"],
                row["influence_count"],
                row["operator_decision_count"],
                row["operator_reuse_rate"],
                row["cpu_time_ms"],
                row["step_ops_estimate"],
                row["memory_bytes_estimate"],
                row["energy_mean"],
                row["energy_var"],
                row["entropy_mean"],
                row["internal_time_mean"],
                row["oscillation_score"],
                row["saturation_score"],
                int(bool(row["runtime_adaptive_window_active"])),
                row["runtime_adaptive_profile"],
                int(bool(row["anti_goodhart_flag"])),
                row["anti_goodhart_degraded_signal_count"],
                row["exploration_horizon_ticks"],
                row["horizon_break_reason"],
                row["outerfields_uri"],
            )
        )
    conn.executemany(
        """
        INSERT INTO tick_summary (
            run_id, tick, trace_ref, event_count, event_types_json, refinement_count, influence_count,
            operator_decision_count, operator_reuse_rate, cpu_time_ms, step_ops_estimate, memory_bytes_estimate,
            energy_mean, energy_var, entropy_mean, internal_time_mean, oscillation_score, saturation_score,
            runtime_adaptive_window_active, runtime_adaptive_profile, anti_goodhart_flag,
            anti_goodhart_degraded_signal_count, exploration_horizon_ticks, horizon_break_reason, outerfields_uri
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_operator_rows(conn: sqlite3.Connection, run_id: str, operator_rows: list[dict[str, Any]]) -> None:
    conn.executemany(
        """
        INSERT INTO operator_panel (
            run_id, tick, decision_count, reuse_count, search_count, hold_rate, operator_reuse, transferability,
            torsion_flag_rate, torsion_health, acceptance_passed, failed_signals_json, goodhart_flag,
            goodhart_target_signal, goodhart_target_delta, goodhart_degraded_signals_json, policy_reaction_apply,
            policy_reaction_actions_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                int(row["tick"]),
                int(row["decision_count"]),
                int(row["reuse_count"]),
                int(row["search_count"]),
                row["hold_rate"],
                row["operator_reuse"],
                row["transferability"],
                row["torsion_flag_rate"],
                row["torsion_health"],
                int(bool(row["acceptance_passed"])),
                json.dumps(row["failed_signals"], ensure_ascii=False),
                int(bool(row["goodhart_flag"])),
                row["goodhart_target_signal"],
                row["goodhart_target_delta"],
                json.dumps(row["goodhart_degraded_signals"], ensure_ascii=False),
                int(bool(row["policy_reaction_apply"])),
                json.dumps(row["policy_reaction_actions"], ensure_ascii=False),
            )
            for row in operator_rows
        ],
    )


def _insert_artifact_rows(conn: sqlite3.Connection, run_id: str, artifact_rows: list[dict[str, Any]]) -> None:
    conn.executemany(
        """
        INSERT INTO artifact_refs (
            run_id, artifact_kind, tick, path, trace_ref, schema, size_bytes, sha256, meta_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                str(row["artifact_kind"]),
                int(row["tick"]),
                str(row["path"]),
                row.get("trace_ref"),
                row.get("schema"),
                row.get("size_bytes"),
                row.get("sha256"),
                json.dumps(row.get("meta", {}), ensure_ascii=False),
            )
            for row in artifact_rows
        ],
    )


def _insert_issues(conn: sqlite3.Connection, run_id: str, issues: list[IngestIssue]) -> None:
    conn.executemany(
        """
        INSERT INTO run_issues (run_id, severity, code, message, details_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                issue.severity,
                issue.code,
                issue.message,
                json.dumps(issue.details or {}, ensure_ascii=False),
            )
            for issue in issues
        ],
    )


def _read_json(
    path: Path,
    *,
    issues: list[IngestIssue],
    required: bool,
    code: str,
) -> dict[str, Any] | None:
    if not path.exists():
        if required:
            issues.append(
                IngestIssue(
                    severity="error",
                    code=code,
                    message=f"Required artifact is missing: {path.name}",
                    details={"path": str(path)},
                )
            )
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(
            IngestIssue(
                severity="error" if required else "warning",
                code=f"{code}_parse_error",
                message=f"Failed to parse {path.name}",
                details={"path": str(path), "error": str(exc)},
            )
        )
        return None


def _read_jsonl(
    path: Path,
    *,
    issues: list[IngestIssue],
    required: bool,
    code: str,
) -> list[dict[str, Any]]:
    if not path.exists():
        if required:
            issues.append(
                IngestIssue(
                    severity="warning",
                    code=code,
                    message=f"Expected artifact is missing: {path.name}",
                    details={"path": str(path)},
                )
            )
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    except Exception as exc:
        issues.append(
            IngestIssue(
                severity="warning",
                code=f"{code}_parse_error",
                message=f"Failed to parse JSONL artifact {path.name}",
                details={"path": str(path), "error": str(exc)},
            )
        )
        return []
    return rows


def _derive_run_id(
    run_path: Path,
    config_payload: dict[str, Any] | None,
    commits_rows: list[dict[str, Any]] | None,
) -> str:
    created_at_ms, _ = _commit_time_bounds(commits_rows or [])
    config_json = "" if config_payload is None else json.dumps(config_payload, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(f"{run_path.resolve()}|{config_json}|{created_at_ms}".encode("utf-8")).hexdigest()
    return f"run_{digest[:16]}"


def _commit_time_bounds(commits_rows: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    created = [row.get("created_at_ms") for row in commits_rows if row.get("created_at_ms") is not None]
    if not created:
        return None, None
    ints = [int(value) for value in created]
    return min(ints), max(ints)


def _tick_from_commit(row: dict[str, Any]) -> int | None:
    tick_ref = dict(row.get("tick_ref", {}))
    tick = tick_ref.get("tick")
    return None if tick is None else int(tick)


def _build_tick_rows(
    *,
    trace_rows: list[dict[str, Any]],
    watch_rows: list[dict[str, Any]],
    contract_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
    commits_rows: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    trace_map = {int(row["tick"]): row for row in trace_rows if row.get("tick") is not None}
    watch_map = {int(row["tick"]): row for row in watch_rows if row.get("tick") is not None}
    contract_map = {int(row["tick"]): row for row in contract_rows if row.get("tick") is not None}
    decision_map = {int(row["tick"]): row for row in decision_rows if row.get("tick") is not None}
    commit_map = {}
    for row in commits_rows:
        tick = _tick_from_commit(row)
        if tick is not None:
            commit_map[tick] = row

    ticks = sorted(set(trace_map) | set(watch_map) | set(contract_map) | set(decision_map) | set(commit_map))
    tick_rows: dict[int, dict[str, Any]] = {}
    for tick in ticks:
        trace_row = trace_map.get(tick, {})
        watch_row = watch_map.get(tick, {})
        contract_row = contract_map.get(tick, {})
        decision_row = decision_map.get(tick, {})
        commit_row = commit_map.get(tick, {})

        watchpoints = _coerce_dict(_nested_get(watch_row, "watchpoints"))
        if not watchpoints:
            watchpoints = _coerce_dict(_nested_get(contract_row, "metrics", "watchpoints"))
        trace_policy = _coerce_dict(_nested_get(trace_row, "policy"))
        policy = _coerce_dict(_nested_get(watch_row, "policy")) or _coerce_dict(_nested_get(contract_row, "policy")) or trace_policy
        trace_guard = _coerce_dict(_nested_get(trace_policy, "runtime_adaptive_guard"))
        anti_goodhart = (
            _coerce_dict(_nested_get(watchpoints, "anti_goodhart"))
            or _coerce_dict(_nested_get(policy, "anti_goodhart"))
            or _coerce_dict(_nested_get(trace_guard, "anti_goodhart"))
        )
        exploration = (
            _coerce_dict(_nested_get(watchpoints, "exploration_horizon"))
            or _coerce_dict(_nested_get(policy, "exploration_horizon"))
            or _coerce_dict(_nested_get(trace_guard, "exploration_horizon"))
        )
        signature_summary = _coerce_dict(_nested_get(trace_row, "signature", "summary")) or _coerce_dict(
            _nested_get(contract_row, "signature", "summary")
        )
        field_summaries = _coerce_dict(_nested_get(trace_row, "field_summaries"))
        cost = _coerce_dict(_nested_get(trace_row, "cost")) or _coerce_dict(
            _nested_get(contract_row, "metrics", "cost")
        ) or _coerce_dict(_nested_get(trace_row, "metrics", "builtin", "cost"))
        quality = _coerce_dict(_nested_get(trace_row, "quality")) or _coerce_dict(
            _nested_get(contract_row, "metrics", "quality")
        ) or _coerce_dict(_nested_get(trace_row, "metrics", "builtin", "quality"))
        trace_events = list(trace_row.get("events", [])) if isinstance(trace_row.get("events"), list) else []
        event_types = list(watch_row.get("event_types", [])) or list(trace_row.get("event_types", [])) or list(
            contract_row.get("event_types", [])
        )
        event_count = _first_not_none(
            watch_row.get("event_count"),
            trace_row.get("event_count"),
            contract_row.get("event_count"),
            _nested_get(commit_row, "summary", "event_count"),
            0,
        )
        refinement_count = _first_not_none(
            watchpoints.get("refinement_count"),
            sum(1 for event in trace_events if str(event.get("type")) == "refinement"),
            0,
        )
        influence_count = _first_not_none(
            watchpoints.get("influence_count"),
            sum(1 for event in trace_events if str(event.get("type")) == "influence"),
            0,
        )
        operator_decision_count = _first_not_none(
            watchpoints.get("operator_decision_count"),
            decision_row.get("decision_count"),
            0,
        )
        operator_reuse_rate = _first_not_none(
            watchpoints.get("operator_reuse_rate"),
            _nested_get(decision_row, "summary", "reuse_rate"),
        )
        contract_outerfields = _coerce_dict(_nested_get(contract_row, "outerfields_ref"))
        tick_rows[tick] = {
            "tick": int(tick),
            "trace_ref": _first_not_none(
                watch_row.get("trace_ref"),
                trace_row.get("trace_ref"),
                contract_row.get("trace_ref"),
                decision_row.get("trace_ref"),
                commit_row.get("trace_ref"),
            ),
            "event_count": int(event_count or 0),
            "event_types": [str(value) for value in event_types],
            "refinement_count": None if refinement_count is None else int(refinement_count),
            "influence_count": None if influence_count is None else int(influence_count),
            "operator_decision_count": None if operator_decision_count is None else int(operator_decision_count),
            "operator_reuse_rate": None if operator_reuse_rate is None else float(operator_reuse_rate),
            "cpu_time_ms": _coerce_float(cost.get("cpu_time_ms")),
            "step_ops_estimate": _coerce_float(cost.get("step_ops_estimate")),
            "memory_bytes_estimate": _coerce_float(cost.get("memory_bytes_estimate")),
            "energy_mean": _coerce_float(_first_not_none(signature_summary.get("energy_mean"), _nested_get(field_summaries, "energy", "mean"))),
            "energy_var": _coerce_float(_first_not_none(signature_summary.get("energy_var"), _nested_get(field_summaries, "energy", "variance"))),
            "entropy_mean": _coerce_float(_first_not_none(signature_summary.get("entropy_mean"), _nested_get(field_summaries, "entropy", "mean"))),
            "internal_time_mean": _coerce_float(
                _first_not_none(signature_summary.get("internal_time_mean"), _nested_get(field_summaries, "internal_time", "mean"))
            ),
            "oscillation_score": _coerce_float(quality.get("oscillation_score")),
            "saturation_score": _coerce_float(quality.get("saturation_score")),
            "runtime_adaptive_window_active": bool(
                _first_not_none(
                    watchpoints.get("runtime_adaptive_window_active"),
                    policy.get("runtime_adaptive_window_active"),
                    trace_policy.get("runtime_adaptive_window_active"),
                    False,
                )
            ),
            "runtime_adaptive_profile": _first_not_none(
                watchpoints.get("runtime_adaptive_profile"),
                policy.get("runtime_adaptive_profile"),
                trace_policy.get("runtime_adaptive_profile"),
            ),
            "anti_goodhart_flag": bool(
                _first_not_none(
                    watchpoints.get("anti_goodhart_flag"),
                    anti_goodhart.get("goodhart_flag"),
                    False,
                )
            ),
            "anti_goodhart_degraded_signal_count": _coerce_int(
                _first_not_none(
                    watchpoints.get("anti_goodhart_degraded_signal_count"),
                    anti_goodhart.get("degraded_signal_count"),
                    0,
                )
            ),
            "exploration_horizon_ticks": _coerce_int(
                _first_not_none(
                    watchpoints.get("exploration_horizon_ticks"),
                    exploration.get("exploration_horizon_ticks"),
                    0,
                )
            ),
            "horizon_break_reason": str(
                _first_not_none(
                    watchpoints.get("horizon_break_reason"),
                    exploration.get("horizon_break_reason"),
                    "",
                )
            ),
            "outerfields_uri": contract_outerfields.get("uri"),
        }
    return tick_rows


def _build_operator_rows(decision_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in decision_rows:
        tick = entry.get("tick")
        if tick is None:
            continue
        decision_count = int(entry.get("decision_count", 0))
        if decision_count <= 0:
            continue
        summary = _coerce_dict(entry.get("summary"))
        panel = _coerce_dict(summary.get("portability_panel"))
        acceptance = _coerce_dict(panel.get("acceptance"))
        anti_goodhart = _coerce_dict(panel.get("anti_goodhart"))
        reaction = _coerce_dict(anti_goodhart.get("policy_reaction"))
        rows.append(
            {
                "tick": int(tick),
                "trace_ref": entry.get("trace_ref"),
                "decision_count": decision_count,
                "reuse_count": int(summary.get("reuse_count", 0)),
                "search_count": int(summary.get("search_count", 0)),
                "hold_rate": _coerce_float(panel.get("hold_rate")),
                "operator_reuse": _coerce_float(panel.get("operator_reuse")),
                "transferability": _coerce_float(panel.get("transferability")),
                "torsion_flag_rate": _coerce_float(panel.get("torsion_flag_rate")),
                "torsion_health": _coerce_float(panel.get("torsion_health")),
                "acceptance_passed": bool(acceptance.get("passed", False)),
                "failed_signals": [str(value) for value in list(acceptance.get("failed_signals", []))],
                "goodhart_flag": bool(anti_goodhart.get("goodhart_flag", False)),
                "goodhart_target_signal": anti_goodhart.get("target_signal"),
                "goodhart_target_delta": _coerce_float(anti_goodhart.get("target_delta")),
                "goodhart_degraded_signals": [str(value) for value in list(anti_goodhart.get("degraded_signals", []))],
                "policy_reaction_apply": bool(reaction.get("apply", False)),
                "policy_reaction_actions": [str(value) for value in list(reaction.get("actions", []))],
                "portability_panel": panel,
                "anti_goodhart": anti_goodhart,
            }
        )
    return rows


def _build_outerfields_rows(
    *,
    run_path: Path,
    contract_rows: list[dict[str, Any]],
    issues: list[IngestIssue],
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    total_bytes = 0
    for entry in contract_rows:
        tick = entry.get("tick")
        if tick is None:
            continue
        outerfields_ref = _coerce_dict(entry.get("outerfields_ref"))
        uri = outerfields_ref.get("uri")
        if uri is None:
            continue
        artifact_path = run_path / str(uri)
        size_bytes = artifact_path.stat().st_size if artifact_path.exists() else None
        if artifact_path.exists():
            total_bytes += int(size_bytes or 0)
        else:
            issues.append(
                IngestIssue(
                    severity="warning",
                    code="missing_outerfields_artifact",
                    message=f"Outerfields artifact referenced by watch_contract is missing for tick {tick}",
                    details={"tick": int(tick), "path": str(artifact_path)},
                )
            )
        rows.append(
            {
                "tick": int(tick),
                "trace_ref": entry.get("trace_ref"),
                "outerfields_uri": str(uri),
                "schema": outerfields_ref.get("schema"),
                "size_bytes": size_bytes,
                "projection_meta": _coerce_dict(entry.get("projection")),
            }
        )
    return rows, total_bytes


def _build_artifact_rows(
    *,
    run_path: Path,
    config_payload: dict[str, Any],
    digest_payload: dict[str, Any] | None,
    trace_rows: list[dict[str, Any]],
    watch_rows: list[dict[str, Any]],
    contract_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
    commits_rows: list[dict[str, Any]],
    commit_validation_payload: dict[str, Any] | None,
    outerfields_rows: list[dict[str, Any]],
    multiscale_candidates_rows: list[dict[str, Any]],
    bridge_record_sources_rows: list[dict[str, Any]],
    scale_tension_rows: list[dict[str, Any]],
    operator_catalog_hits_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    run_level_files = [
        ("config", run_path / "config.json", config_payload.get("config_version")),
        ("digest", run_path / "digest.json", digest_payload.get("version") if digest_payload else None),
        ("state", run_path / "state.msgpack", None),
        ("trace", run_path / "trace.jsonl", _nested_get(trace_rows[0], "signature", "version") if trace_rows else None),
        ("watch_trace", run_path / "watch_trace.jsonl", None),
        ("watch_contract", run_path / "watch_contract.jsonl", contract_rows[0].get("schema") if contract_rows else None),
        ("operator_decisions", run_path / "operator_decisions.jsonl", None),
        ("multiscale_candidates_file", run_path / "multiscale_candidates.jsonl", None),
        ("bridge_record_sources_file", run_path / "bridge_record_sources.jsonl", None),
        ("scale_tension_file", run_path / "scale_tension.jsonl", None),
        ("operator_catalog_hits_file", run_path / "operator_catalog_hits.jsonl", None),
        ("commits", run_path / "commits.jsonl", commits_rows[0].get("schema_version") if commits_rows else None),
        ("commit_validation", run_path / "commit_validation.json", commit_validation_payload.get("status") if commit_validation_payload else None),
        ("commit_validation_history", run_path / "commit_validation_history.jsonl", None),
        ("fields_hist", run_path / "fields_hist.npz", None),
    ]
    for artifact_kind, path, schema in run_level_files:
        if not path.exists():
            continue
        rows.append(
            {
                "artifact_kind": artifact_kind,
                "tick": -1,
                "path": path.relative_to(run_path).as_posix(),
                "trace_ref": None,
                "schema": schema,
                "size_bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
                "meta": {"kind": "run_level"},
            }
        )

    contract_by_tick = {int(row["tick"]): row for row in contract_rows if row.get("tick") is not None}
    for row in outerfields_rows:
        tick = int(row["tick"])
        relative_path = Path(str(row["outerfields_uri"]))
        artifact_path = run_path / relative_path
        contract_row = contract_by_tick.get(tick, {})
        rows.append(
            {
                "artifact_kind": "outerfields",
                "tick": tick,
                "path": relative_path.as_posix(),
                "trace_ref": row.get("trace_ref"),
                "schema": row.get("schema"),
                "size_bytes": artifact_path.stat().st_size if artifact_path.exists() else None,
                "sha256": _file_sha256(artifact_path) if artifact_path.exists() else None,
                "meta": {
                    "kind": "outerfields",
                    "projection": _coerce_dict(contract_row.get("projection")),
                    "base_level": _nested_get(contract_row, "outerfields_ref", "base_level"),
                    "level_src": _nested_get(contract_row, "outerfields_ref", "level_src"),
                },
            }
        )
    path_lookup = {
        "multiscale_candidates": run_path / "multiscale_candidates.jsonl",
        "bridge_record_sources": run_path / "bridge_record_sources.jsonl",
        "scale_tension": run_path / "scale_tension.jsonl",
        "operator_catalog_hits": run_path / "operator_catalog_hits.jsonl",
    }
    for artifact_kind, source_rows in (
        ("multiscale_candidates", multiscale_candidates_rows),
        ("bridge_record_sources", bridge_record_sources_rows),
        ("scale_tension", scale_tension_rows),
        ("operator_catalog_hits", operator_catalog_hits_rows),
    ):
        path = path_lookup[artifact_kind]
        for row_index, row in enumerate(source_rows, start=1):
            tick = row.get("tick")
            if tick is None:
                continue
            meta = dict(row)
            meta.update(
                {
                    "kind": "logical_row",
                    "row_index": int(row_index),
                    "row_sha256": _row_sha256(row),
                    "source_artifact_kind": f"{artifact_kind}_file",
                }
            )
            rows.append(
                {
                    "artifact_kind": artifact_kind,
                    "tick": int(tick),
                    "path": path.relative_to(run_path).as_posix(),
                    "trace_ref": row.get("trace_ref"),
                    "schema": row.get("mode"),
                    "size_bytes": None,
                    "sha256": None,
                    "meta": meta,
                }
            )
    return rows


def _build_run_summary_payload(
    *,
    run_id: str,
    run_path: Path,
    status: str,
    config_payload: dict[str, Any],
    digest_payload: dict[str, Any] | None,
    commit_validation_payload: dict[str, Any] | None,
    ticks_data: dict[int, dict[str, Any]],
    operator_rows: list[dict[str, Any]],
    outerfields_rows: list[dict[str, Any]],
    outerfields_total_bytes: int,
    multiscale_candidates_rows: list[dict[str, Any]],
    bridge_record_sources_rows: list[dict[str, Any]],
    scale_tension_rows: list[dict[str, Any]],
    operator_catalog_hits_rows: list[dict[str, Any]],
    created_at_ms: int | None,
    completed_at_ms: int | None,
    issues: list[IngestIssue],
) -> dict[str, Any]:
    tick_rows = [ticks_data[tick] for tick in sorted(ticks_data)]
    tick_count = len(tick_rows)
    eventful_tick_count = sum(1 for row in tick_rows if int(row["event_count"]) > 0)
    decision_tick_count = len(operator_rows)
    final_operator = operator_rows[-1] if operator_rows else None
    final_anti_goodhart = None
    final_exploration = None
    if tick_rows:
        last = tick_rows[-1]
        final_anti_goodhart = {
            "goodhart_flag": bool(last["anti_goodhart_flag"]),
            "degraded_signal_count": int(last["anti_goodhart_degraded_signal_count"] or 0),
        }
        final_exploration = {
            "exploration_horizon_ticks": int(last["exploration_horizon_ticks"] or 0),
            "horizon_break_reason": str(last["horizon_break_reason"] or ""),
        }

    warning_messages, warning_summary = _summarize_issues(issues)
    warnings = list(warning_messages)
    trace_chain_validation_ok = bool(_nested_get(commit_validation_payload or {}, "status") == "ok")
    learning_contour_confirmed = bool(final_operator and final_operator["acceptance_passed"])
    if trace_chain_validation_ok and not learning_contour_confirmed:
        warnings.append("Run is suitable for chain/trace validation but does not confirm a successful learning contour")

    return {
        "run_id": run_id,
        "run_dir": str(run_path),
        "status": status,
        "created_at_ms": created_at_ms,
        "completed_at_ms": completed_at_ms,
        "config": {
            "backend": config_payload.get("backend"),
            "device": config_payload.get("device"),
            "shape": config_payload.get("shape"),
            "watch_trace_enabled": bool(config_payload.get("watch_trace_enabled", False)),
            "record_fields": bool((run_path / "fields_hist.npz").exists()),
        },
        "digest": None if digest_payload is None else dict(digest_payload),
        "commit_validation": None if commit_validation_payload is None else dict(commit_validation_payload),
        "counts": {
            "tick_count": tick_count,
            "eventful_tick_count": eventful_tick_count,
            "decision_tick_count": decision_tick_count,
        },
        "final_portability_panel": None if final_operator is None else final_operator["portability_panel"],
        "final_anti_goodhart": final_anti_goodhart,
        "final_exploration_horizon": final_exploration,
        "artifact_inventory": {
            "outerfields_file_count": len(outerfields_rows),
            "outerfields_total_bytes": int(outerfields_total_bytes),
            "outerfields_density_per_100_ticks": 0.0 if tick_count == 0 else (len(outerfields_rows) * 100.0) / tick_count,
            "multiscale_candidates_file_count": int((run_path / "multiscale_candidates.jsonl").exists()),
            "bridge_record_sources_file_count": int((run_path / "bridge_record_sources.jsonl").exists()),
            "scale_tension_file_count": int((run_path / "scale_tension.jsonl").exists()),
            "operator_catalog_hits_file_count": int((run_path / "operator_catalog_hits.jsonl").exists()),
        },
        "applicability": {
            "trace_chain_validation_ok": trace_chain_validation_ok,
            "learning_contour_confirmed": learning_contour_confirmed,
        },
        "warning_summary": warning_summary,
        "warnings": warnings,
    }


def _build_event_window_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "tick": int(row["tick"]),
        "trace_ref": row["trace_ref"],
        "event_count": int(row["event_count"]),
        "event_types": list(row["event_types"]),
        "cost": {
            "cpu_time_ms": row["cpu_time_ms"],
            "step_ops_estimate": row["step_ops_estimate"],
            "memory_bytes_estimate": row["memory_bytes_estimate"],
        },
        "quality": {
            "energy_mean": row["energy_mean"],
            "energy_var": row["energy_var"],
            "entropy_mean": row["entropy_mean"],
            "internal_time_mean": row["internal_time_mean"],
            "oscillation_score": row["oscillation_score"],
            "saturation_score": row["saturation_score"],
        },
        "watchpoints": {
            "refinement_count": row["refinement_count"],
            "influence_count": row["influence_count"],
            "operator_decision_count": row["operator_decision_count"],
            "operator_reuse_rate": row["operator_reuse_rate"],
            "runtime_adaptive_window_active": bool(row["runtime_adaptive_window_active"]),
            "anti_goodhart_flag": bool(row["anti_goodhart_flag"]),
            "anti_goodhart_degraded_signal_count": row["anti_goodhart_degraded_signal_count"],
            "exploration_horizon_ticks": row["exploration_horizon_ticks"],
            "horizon_break_reason": row["horizon_break_reason"],
        },
        "outerfields_uri": row["outerfields_uri"],
    }


def _build_decision_window_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "tick": int(row["tick"]),
        "trace_ref": row["trace_ref"],
        "decision_count": int(row["decision_count"]),
        "reuse_count": int(row["reuse_count"]),
        "search_count": int(row["search_count"]),
        "reuse_rate": 0.0
        if int(row["decision_count"]) == 0
        else float(row["reuse_count"]) / max(int(row["decision_count"]), 1),
        "portability_panel": row["portability_panel"],
        "anti_goodhart": row["anti_goodhart"],
    }


def _status_from_issues(issues: list[IngestIssue]) -> str:
    if any(issue.severity == "error" for issue in issues):
        return "broken"
    if issues:
        return "partial"
    return "ok"


def _summarize_issues(issues: list[IngestIssue]) -> tuple[list[str], dict[str, Any]]:
    warnings = [issue for issue in issues if issue.severity != "error"]
    grouped: dict[str, list[IngestIssue]] = {}
    for issue in warnings:
        grouped.setdefault(issue.code, []).append(issue)

    messages: list[str] = []
    summary: dict[str, Any] = {}
    for code, code_issues in grouped.items():
        if code == "missing_outerfields_artifact":
            ticks = sorted(
                int(issue.details["tick"])
                for issue in code_issues
                if isinstance(issue.details, dict) and issue.details.get("tick") is not None
            )
            paths = sorted(
                {
                    str(issue.details["path"])
                    for issue in code_issues
                    if isinstance(issue.details, dict) and issue.details.get("path")
                }
            )
            message = (
                "Outerfields artifacts referenced by watch_contract are missing "
                f"for {len(code_issues)} ticks"
            )
            if ticks:
                message += f" ({ticks[0]}..{ticks[-1]})"
            messages.append(message)
            summary[code] = {
                "count": len(code_issues),
                "sample_ticks": ticks[:10],
                "first_tick": ticks[0] if ticks else None,
                "last_tick": ticks[-1] if ticks else None,
                "sample_paths": paths[:5],
            }
            continue

        message_counter = Counter(issue.message for issue in code_issues)
        top_message, top_count = message_counter.most_common(1)[0]
        if top_count > 1:
            messages.append(f"{top_message} (x{top_count})")
        else:
            messages.append(top_message)
        summary[code] = {
            "count": len(code_issues),
            "messages": list(message_counter.keys())[:5],
        }
    return messages, summary


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    if text:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nested_get(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _coerce_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


__all__ = [
    "IngestIssue",
    "IngestReport",
    "RunSummary",
    "ingest_run",
    "open_run_db",
    "summarize_run",
]
