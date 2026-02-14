"""Core headless subscriber wiring."""

from __future__ import annotations

from pathlib import Path

from detm.runtime.config import DETMConfig
from detm_app.runner.headless.subscribers.policy import storage_policy
from detm_app.runtime.coarsening import InvariantCoarsener, parse_invariant_streams
from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import (
    ArtifactWriter,
    CommitJsonlWriter,
    CommitValidationReporter,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    TraceRecorder,
    WatchContractWriter,
    WatchTraceWriter,
)


def attach_core_subscribers(
    *,
    session: DetmSession,
    config: DETMConfig,
    seed: int,
    out_dir: Path,
    level_name: str,
    invariant_streams: list[str] | None,
) -> None:
    if invariant_streams:
        inv_policy = storage_policy(config=config, level_name=level_name, artifact="invariants")
        InvariantCoarsener.attach(session.bus, parse_invariant_streams(invariant_streams))
        InvariantTickJsonlWriter.attach(
            session.bus,
            out_dir / "invariants.jsonl",
            retention_window=int(inv_policy.get("retention_window", 0)),
            compaction_budget=int(inv_policy.get("compaction_budget", 0)),
        )

    history_policy = storage_policy(config=config, level_name=level_name, artifact="history")
    TraceRecorder.attach(
        session.bus,
        out_dir,
        retention_window=int(history_policy.get("retention_window", 0)),
        compaction_budget=int(history_policy.get("compaction_budget", 0)),
    )
    ArtifactWriter.attach(session.bus, out_dir)

    trace_policy = storage_policy(config=config, level_name=level_name, artifact="trace")
    JsonlTraceWriter.attach(
        session.bus,
        out_dir / "trace.jsonl",
        retention_window=int(trace_policy.get("retention_window", 0)),
        compaction_budget=int(trace_policy.get("compaction_budget", 0)),
    )

    if bool(config.watch_trace_enabled):
        watch_policy = storage_policy(config=config, level_name=level_name, artifact="watch_trace")
        watch_contract_policy = storage_policy(config=config, level_name=level_name, artifact="watch_contract")
        outerfields_policy = storage_policy(config=config, level_name=level_name, artifact="outerfields")
        WatchTraceWriter.attach(
            session.bus,
            out_dir / "watch_trace.jsonl",
            retention_window=int(watch_policy.get("retention_window", 0)),
            compaction_budget=int(watch_policy.get("compaction_budget", 0)),
        )
        WatchContractWriter.attach(
            session.bus,
            out_dir / "watch_contract.jsonl",
            outerfields_dir=out_dir / "outerfields",
            level_src=level_name,
            base_level="L0",
            retention_window=int(watch_contract_policy.get("retention_window", 0)),
            compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
            outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
            outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
        )

    commits_policy = storage_policy(config=config, level_name=level_name, artifact="commits")
    CommitJsonlWriter.attach(
        session.bus,
        out_dir / "commits.jsonl",
        node_id=f"seed_{int(seed):04d}",
        mode="realtime",
        retention_window=int(commits_policy.get("retention_window", 0)),
        compaction_budget=int(commits_policy.get("compaction_budget", 0)),
    )
    if bool(config.level_policy.audit_commit_enabled):
        commits_audit_policy = storage_policy(config=config, level_name=level_name, artifact="commits_audit")
        CommitJsonlWriter.attach(
            session.bus,
            out_dir / "commits_audit.jsonl",
            node_id=f"seed_{int(seed):04d}",
            commit_type="proof",
            mode="audit",
            retention_window=int(commits_audit_policy.get("retention_window", 0)),
            compaction_budget=int(commits_audit_policy.get("compaction_budget", 0)),
        )

    commit_validation_policy = storage_policy(config=config, level_name=level_name, artifact="commit_validation")
    CommitValidationReporter.attach(
        session.bus,
        out_dir,
        retention_window=int(commit_validation_policy.get("retention_window", 0)),
        compaction_budget=int(commit_validation_policy.get("compaction_budget", 0)),
    )


__all__ = ["attach_core_subscribers"]
