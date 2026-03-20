from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm_app.runner.headless import main as headless_main
from detm_app.runner.headless.subscribers.core import attach_core_subscribers
from detm_app.runtime.session import DetmSession
from detm_app.storage.analytics_db import ingest_run, open_run_db, summarize_run


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_overflow_hotspot(session: DetmSession) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.zeros((h, w), dtype=float)
    energy[h // 2, w // 2] = 3.0
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(energy, session.config.dynamics, boundary=state.lattice.boundary)


def _make_eventful_run(tmp_path: Path, *, watch_trace_enabled: bool = True) -> Path:
    run_dir = tmp_path / "run_eventful"
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=11,
        height=11,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        watch_trace_enabled=watch_trace_enabled,
        level_policy=LevelPolicy(
            active_level="L0",
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=False,
        ),
    )
    session = DetmSession.create(cfg, seed=17)
    attach_core_subscribers(
        session=session,
        config=cfg,
        seed=17,
        out_dir=run_dir,
        level_name="L0",
        invariant_streams=None,
    )
    for _ in range(4):
        _seed_overflow_hotspot(session)
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()
    return run_dir


def _make_zero_event_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run_zero_event"
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.0,
        watch_trace_enabled=True,
        level_policy=LevelPolicy(
            active_level="L0",
            commit_stride=1,
            microsteps_per_global_tick=1,
            allow_refinement=False,
            audit_commit_enabled=False,
        ),
    )
    session = DetmSession.create(cfg, seed=101)
    attach_core_subscribers(
        session=session,
        config=cfg,
        seed=101,
        out_dir=run_dir,
        level_name="L0",
        invariant_streams=None,
    )
    for _ in range(3):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()
    trace_rows = _read_jsonl(run_dir / "trace.jsonl")
    assert all(int(row.get("event_count", 0)) == 0 for row in trace_rows)
    return run_dir


def test_ingest_run_builds_sqlite_and_structured_exports(tmp_path):
    run_dir = _make_eventful_run(tmp_path)

    report = ingest_run(run_dir)

    assert report.status == "ok"
    assert report.db_path == run_dir / "analytics.sqlite"
    assert report.ticks_ingested == 4
    assert report.events_ingested > 0
    assert report.decisions_ingested > 0
    assert report.outerfields_refs_ingested > 0

    analytics_dir = run_dir / "analytics"
    assert (analytics_dir / "run_summary.json").exists()
    assert (analytics_dir / "event_windows.jsonl").exists()
    assert (analytics_dir / "decision_windows.jsonl").exists()
    assert (analytics_dir / "outerfields_index.jsonl").exists()

    with open_run_db(run_dir) as conn:
        runs = conn.execute(
            "SELECT tick_count, eventful_tick_count, decision_tick_count, outerfields_file_count, status FROM runs"
        ).fetchone()
        assert runs is not None
        assert int(runs["tick_count"]) == 4
        assert int(runs["eventful_tick_count"]) > 0
        assert int(runs["decision_tick_count"]) > 0
        assert int(runs["outerfields_file_count"]) > 0
        assert str(runs["status"]) == "ok"

        tick_count = conn.execute("SELECT COUNT(*) AS n FROM tick_summary").fetchone()["n"]
        decision_count = conn.execute("SELECT COUNT(*) AS n FROM operator_panel").fetchone()["n"]
        outerfields_count = conn.execute(
            "SELECT COUNT(*) AS n FROM artifact_refs WHERE artifact_kind = 'outerfields'"
        ).fetchone()["n"]
        assert int(tick_count) == 4
        assert int(decision_count) > 0
        assert int(outerfields_count) > 0

    summary = json.loads((analytics_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["run_id"] == report.run_id
    assert int(summary["counts"]["tick_count"]) == 4
    assert int(summary["artifact_inventory"]["outerfields_file_count"]) > 0

    event_windows = _read_jsonl(analytics_dir / "event_windows.jsonl")
    decision_windows = _read_jsonl(analytics_dir / "decision_windows.jsonl")
    outerfields_index = _read_jsonl(analytics_dir / "outerfields_index.jsonl")
    assert len(event_windows) > 0
    assert len(decision_windows) > 0
    assert len(outerfields_index) > 0
    assert all("trace_ref" in row for row in event_windows)
    assert all("portability_panel" in row for row in decision_windows)
    assert all("projection_meta" in row for row in outerfields_index)


def test_ingest_run_is_idempotent_for_same_run_dir(tmp_path):
    run_dir = _make_eventful_run(tmp_path)

    first = ingest_run(run_dir)
    second = ingest_run(run_dir)

    assert second.run_id == first.run_id
    assert second.ticks_ingested == first.ticks_ingested
    assert second.events_ingested == first.events_ingested
    assert second.decisions_ingested == first.decisions_ingested

    with open_run_db(run_dir) as conn:
        tick_count = conn.execute("SELECT COUNT(*) AS n FROM tick_summary").fetchone()["n"]
        artifact_count = conn.execute("SELECT COUNT(*) AS n FROM artifact_refs").fetchone()["n"]
        assert int(tick_count) == 4
        assert int(artifact_count) > 0


def test_ingest_run_marks_partial_when_optional_artifact_missing(tmp_path):
    run_dir = _make_eventful_run(tmp_path)
    (run_dir / "operator_decisions.jsonl").unlink()

    report = ingest_run(run_dir)

    assert report.status == "partial"
    assert any(issue.code == "missing_operator_decisions" for issue in report.issues)
    with open_run_db(run_dir) as conn:
        runs = conn.execute("SELECT status FROM runs").fetchone()
        assert str(runs["status"]) == "partial"


def test_run_summary_aggregates_missing_outerfields_warnings(tmp_path):
    run_dir = _make_eventful_run(tmp_path)
    for path in (run_dir / "outerfields").glob("*.npz"):
        path.unlink()

    summary = summarize_run(run_dir)

    assert summary.status == "partial"
    warning_summary = summary.payload["warning_summary"]
    assert int(warning_summary["missing_outerfields_artifact"]["count"]) == 4
    assert len(summary.payload["warnings"]) < 10
    assert any("missing for 4 ticks" in message for message in summary.payload["warnings"])


def test_ingest_run_degrades_without_watch_trace_when_config_disables_it(tmp_path):
    run_dir = _make_eventful_run(tmp_path, watch_trace_enabled=False)

    report = ingest_run(run_dir)

    assert report.status == "ok"
    with open_run_db(run_dir) as conn:
        tick_count = conn.execute("SELECT COUNT(*) AS n FROM tick_summary").fetchone()["n"]
        assert int(tick_count) == 4
        decision_count = conn.execute("SELECT COUNT(*) AS n FROM operator_panel").fetchone()["n"]
        assert int(decision_count) == 0


def test_summarize_run_handles_zero_event_run_and_keeps_db_blob_free(tmp_path):
    run_dir = _make_zero_event_run(tmp_path)

    summary = summarize_run(run_dir)

    assert summary.status == "ok"
    assert int(summary.payload["counts"]["tick_count"]) == 3
    assert int(summary.payload["counts"]["eventful_tick_count"]) == 0

    with sqlite3.connect(run_dir / "analytics.sqlite") as conn:
        cols = conn.execute("PRAGMA table_info(artifact_refs)").fetchall()
        declared_types = {str(col[1]): str(col[2]).upper() for col in cols}
        assert declared_types["meta_json"] == "TEXT"
        assert all(dtype != "BLOB" for dtype in declared_types.values())


def test_headless_analytics_cli_ingest_summarize_and_query(tmp_path, capsys):
    run_dir = _make_eventful_run(tmp_path)

    assert headless_main(["analytics", "ingest", "--run-dir", str(run_dir)]) == 0
    ingest_out = json.loads(capsys.readouterr().out)
    assert ingest_out["status"] == "ok"

    assert headless_main(["analytics", "summarize", "--run-dir", str(run_dir)]) == 0
    summary_out = json.loads(capsys.readouterr().out)
    assert int(summary_out["counts"]["tick_count"]) == 4

    assert (
        headless_main(
            [
                "analytics",
                "query",
                "--db",
                str(run_dir / "analytics.sqlite"),
                "--sql",
                "SELECT tick_count FROM runs",
            ]
        )
        == 0
    )
    rows = json.loads(capsys.readouterr().out)
    assert rows == [{"tick_count": 4}]
