"""CLI entrypoint for post-run analytics ingest/query."""

from __future__ import annotations

import argparse
import json
import sqlite3

from detm_app.storage.analytics_db import ingest_run, summarize_run


def _compact_report_payload(payload: dict) -> dict:
    issues = list(payload.get("issues", []))
    if len(issues) <= 20:
        return payload
    compact = dict(payload)
    compact["issue_count"] = len(issues)
    compact["issues_preview"] = issues[:20]
    compact.pop("issues", None)
    return compact


def _compact_summary_payload(payload: dict) -> dict:
    warnings = list(payload.get("warnings", []))
    if len(warnings) <= 20:
        return payload
    compact = dict(payload)
    compact["warning_count"] = len(warnings)
    compact["warnings_preview"] = warnings[:20]
    compact.pop("warnings", None)
    return compact


def build_analytics_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest a completed run into analytics.sqlite and structured exports")
    ingest.add_argument("--run-dir", required=True, help="Run directory containing DETM raw artifacts")

    summarize = sub.add_parser("summarize", help="Build structured analytics summary for a completed run")
    summarize.add_argument("--run-dir", required=True, help="Run directory containing DETM raw artifacts")

    query = sub.add_parser("query", help="Execute a debug/admin SQL query against analytics.sqlite")
    query.add_argument("--db", required=True, help="Path to analytics.sqlite")
    query.add_argument("--sql", required=True, help="SQL query to execute")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_analytics_parser().parse_args(argv)
    if args.command == "ingest":
        report = ingest_run(args.run_dir)
        print(json.dumps(_compact_report_payload(report.to_dict()), ensure_ascii=False))
        return 0
    if args.command == "summarize":
        summary = summarize_run(args.run_dir)
        print(json.dumps(_compact_summary_payload(summary.to_dict()), ensure_ascii=False))
        return 0
    if args.command == "query":
        conn = sqlite3.connect(args.db)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(args.sql)
            if cursor.description is None:
                conn.commit()
                print(json.dumps({"rows_affected": cursor.rowcount}, ensure_ascii=False))
            else:
                print(json.dumps([dict(row) for row in cursor.fetchall()], ensure_ascii=False))
        finally:
            conn.close()
        return 0
    raise SystemExit(f"Unsupported analytics command: {args.command!r}")


__all__ = ["build_analytics_parser", "main"]
