"""Recording/invariant wiring helpers for DetmUiRunner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detm_app.runtime.subscribers import (
    ArtifactWriter,
    CommitJsonlWriter,
    CommitValidationReporter,
    FieldHistoryRecorder,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    OperatorDecisionWriter,
    WatchContractWriter,
    WatchTraceWriter,
)


def _attach_recording_stack(
    runner: Any,
    *,
    record_dir: Path,
    trace_policy: dict[str, int],
    watch_policy: dict[str, int],
    watch_contract_policy: dict[str, int],
    operator_decisions_policy: dict[str, int],
    outerfields_policy: dict[str, int],
    commits_policy: dict[str, int],
    commits_audit_policy: dict[str, int],
    commit_validation_policy: dict[str, int],
) -> None:
    runner._trace_writer = JsonlTraceWriter.attach(
        runner._session.bus,
        record_dir / "trace.jsonl",
        retention_window=int(trace_policy.get("retention_window", 0)),
        compaction_budget=int(trace_policy.get("compaction_budget", 0)),
    )
    if bool(runner.settings.config.watch_trace_enabled):
        runner._watch_trace_writer = WatchTraceWriter.attach(
            runner._session.bus,
            record_dir / "watch_trace.jsonl",
            retention_window=int(watch_policy.get("retention_window", 0)),
            compaction_budget=int(watch_policy.get("compaction_budget", 0)),
        )
        runner._watch_contract_writer = WatchContractWriter.attach(
            runner._session.bus,
            record_dir / "watch_contract.jsonl",
            outerfields_dir=record_dir / "outerfields",
            level_src=str(runner.settings.config.level_policy.active_level or "L0"),
            base_level="L0",
            retention_window=int(watch_contract_policy.get("retention_window", 0)),
            compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
            outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
            outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
        )
        runner._operator_decision_writer = OperatorDecisionWriter.attach(
            runner._session.bus,
            record_dir / "operator_decisions.jsonl",
            retention_window=int(operator_decisions_policy.get("retention_window", 0)),
            compaction_budget=int(operator_decisions_policy.get("compaction_budget", 0)),
        )
    runner._commit_writer = CommitJsonlWriter.attach(
        runner._session.bus,
        record_dir / "commits.jsonl",
        node_id=f"ui_seed_{int(runner.settings.seed):04d}",
        mode="realtime",
        retention_window=int(commits_policy.get("retention_window", 0)),
        compaction_budget=int(commits_policy.get("compaction_budget", 0)),
    )
    if bool(runner.settings.config.level_policy.audit_commit_enabled):
        runner._audit_commit_writer = CommitJsonlWriter.attach(
            runner._session.bus,
            record_dir / "commits_audit.jsonl",
            node_id=f"ui_seed_{int(runner.settings.seed):04d}",
            commit_type="proof",
            mode="audit",
            retention_window=int(commits_audit_policy.get("retention_window", 0)),
            compaction_budget=int(commits_audit_policy.get("compaction_budget", 0)),
        )
    runner._commit_validation_reporter = CommitValidationReporter.attach(
        runner._session.bus,
        record_dir,
        retention_window=int(commit_validation_policy.get("retention_window", 0)),
        compaction_budget=int(commit_validation_policy.get("compaction_budget", 0)),
    )
    configure_invariant_recording(runner)
    runner._artifact_writer = ArtifactWriter.attach(runner._session.bus, record_dir)
    if bool(runner.settings.record_fields):
        runner._fields_recorder = FieldHistoryRecorder.attach(runner._session.bus, record_dir / "fields_hist.npz")


def configure_invariant_recording(runner: Any) -> None:
    record_dir = runner.settings.record_dir
    invariant_key = (runner.settings.invariant_streams or "").strip()
    if record_dir is None or not invariant_key:
        if runner._invariant_writer is not None:
            runner._invariant_writer.on_close()
            runner._invariant_writer = None
        return

    record_dir = Path(record_dir)
    desired_path = record_dir / "invariants.jsonl"
    inv_policy = runner._storage_policy("invariants")
    if runner._invariant_writer is None:
        runner._invariant_writer = InvariantTickJsonlWriter.attach(
            runner._session.bus,
            desired_path,
            retention_window=int(inv_policy.get("retention_window", 0)),
            compaction_budget=int(inv_policy.get("compaction_budget", 0)),
        )
        return
    if runner._invariant_writer.path.resolve() != desired_path.resolve():
        runner._invariant_writer.on_close()
        runner._invariant_writer = InvariantTickJsonlWriter.attach(
            runner._session.bus,
            desired_path,
            retention_window=int(inv_policy.get("retention_window", 0)),
            compaction_budget=int(inv_policy.get("compaction_budget", 0)),
        )


def configure_recording(runner: Any) -> None:
    record_dir = runner.settings.record_dir
    if record_dir is None:
        runner._disable_recording()
        return

    record_dir = Path(record_dir)
    trace_policy = runner._storage_policy("trace")
    watch_policy = runner._storage_policy("watch_trace")
    watch_contract_policy = runner._storage_policy("watch_contract")
    operator_decisions_policy = runner._storage_policy("operator_decisions")
    outerfields_policy = runner._storage_policy("outerfields")
    commits_policy = runner._storage_policy("commits")
    commits_audit_policy = runner._storage_policy("commits_audit")
    commit_validation_policy = runner._storage_policy("commit_validation")

    if runner._trace_writer is None:
        _attach_recording_stack(
            runner,
            record_dir=record_dir,
            trace_policy=trace_policy,
            watch_policy=watch_policy,
            watch_contract_policy=watch_contract_policy,
            operator_decisions_policy=operator_decisions_policy,
            outerfields_policy=outerfields_policy,
            commits_policy=commits_policy,
            commits_audit_policy=commits_audit_policy,
            commit_validation_policy=commit_validation_policy,
        )
        return

    if runner._trace_writer.path.resolve() != (record_dir / "trace.jsonl").resolve():
        runner._disable_recording()
        _attach_recording_stack(
            runner,
            record_dir=record_dir,
            trace_policy=trace_policy,
            watch_policy=watch_policy,
            watch_contract_policy=watch_contract_policy,
            operator_decisions_policy=operator_decisions_policy,
            outerfields_policy=outerfields_policy,
            commits_policy=commits_policy,
            commits_audit_policy=commits_audit_policy,
            commit_validation_policy=commit_validation_policy,
        )
        return

    watch_enabled = bool(runner.settings.config.watch_trace_enabled)
    if watch_enabled and runner._watch_trace_writer is None:
        runner._watch_trace_writer = WatchTraceWriter.attach(
            runner._session.bus,
            record_dir / "watch_trace.jsonl",
            retention_window=int(watch_policy.get("retention_window", 0)),
            compaction_budget=int(watch_policy.get("compaction_budget", 0)),
        )
    if watch_enabled and runner._watch_contract_writer is None:
        runner._watch_contract_writer = WatchContractWriter.attach(
            runner._session.bus,
            record_dir / "watch_contract.jsonl",
            outerfields_dir=record_dir / "outerfields",
            level_src=str(runner.settings.config.level_policy.active_level or "L0"),
            base_level="L0",
            retention_window=int(watch_contract_policy.get("retention_window", 0)),
            compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
            outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
            outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
        )
    if watch_enabled and runner._operator_decision_writer is None:
        runner._operator_decision_writer = OperatorDecisionWriter.attach(
            runner._session.bus,
            record_dir / "operator_decisions.jsonl",
            retention_window=int(operator_decisions_policy.get("retention_window", 0)),
            compaction_budget=int(operator_decisions_policy.get("compaction_budget", 0)),
        )
    if (not watch_enabled) and runner._watch_trace_writer is not None:
        runner._watch_trace_writer.on_close()
        runner._watch_trace_writer = None
    if (not watch_enabled) and runner._watch_contract_writer is not None:
        runner._watch_contract_writer.on_close()
        runner._watch_contract_writer = None
    if (not watch_enabled) and runner._operator_decision_writer is not None:
        runner._operator_decision_writer.on_close()
        runner._operator_decision_writer = None
    # Toggle field recorder without changing directory.
    if bool(runner.settings.record_fields) and runner._fields_recorder is None:
        runner._fields_recorder = FieldHistoryRecorder.attach(runner._session.bus, record_dir / "fields_hist.npz")
    if (not bool(runner.settings.record_fields)) and runner._fields_recorder is not None:
        runner._fields_recorder.detach()
        runner._fields_recorder = None
    configure_invariant_recording(runner)


__all__ = ["configure_invariant_recording", "configure_recording"]
