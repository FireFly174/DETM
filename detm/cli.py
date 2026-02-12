#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""DETM headless CLI runner (package entrypoint).

Examples:
  python detm.py
  python main.py --seed 1 --steps 4 --symbols pulse ring
  python main.py --batch 10 --seed0 0 --out runs/out/my_batch
  python main.py --viz   # start viz daemon and stream state

Config unification:
- `--preset` loads `detm/presets/<preset>.json`
- `--config` can point to a JSON override that may include:
  - DETM runtime config keys (backend/device/width/height/dynamics/...)
  - optional `runner` section with defaults for headless runs
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from detm.app_settings import build_runtime_config, load_merged_payload
from detm_app.coarsening import InvariantCoarsener, parse_invariant_streams
from detm_app.session import DetmSession
from detm_app.subscribers import (
    ArtifactWriter,
    CommitJsonlWriter,
    CommitValidationReporter,
    FabricHandshakeRecorder,
    FieldHistoryRecorder,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    TraceRecorder,
    VizStreamer,
    WatchContractWriter,
    WatchTraceWriter,
)
from detm.presets import preset_names
from detm.runtime.config import DETMConfig
from detm.runtime.schemas import get_schema_versions
from detm.runtime.symbols import list_symbols, make_symbol
from detm.viz.transport import open_viz_transport


def _default_out_dir(out: str | None) -> Path:
    if out is not None:
        return Path(out)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("runs/out") / f"run_{stamp}"


def _resolve_symbols(symbols: list[str] | None) -> list[str]:
    if symbols is None:
        return list_symbols()
    out: List[str] = []
    known = set(list_symbols())
    for sid in symbols:
        if sid in known:
            out.append(sid)
        else:
            raise SystemExit(f"Unknown symbol_id: {sid}. Known: {sorted(known)}")
    return out


def _runner_defaults(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw = payload.get("runner", {})
    return raw if isinstance(raw, dict) else {}


def _as_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        # allow comma-separated in config
        chunks = [c.strip() for c in value.split(",") if c.strip()]
        return chunks
    return None


def _flatten_list_args(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    out: list[str] = []
    for raw in list(values):
        chunks = _as_list(raw)
        if chunks:
            out.extend(chunks)
    return out


def run_headless(
    config: DETMConfig,
    seed: int,
    symbol_ids: list[str],
    steps: int,
    out_dir: Path,
    viz_transport,
    *,
    viz_every_steps: int = 1,
    fields_npz: bool = False,
    fields_every_steps: int = 1,
    invariant_streams: list[str] | None = None,
    fabric_handshake: bool = False,
    fabric_required_proof_accepts: int = 1,
    fabric_required_trust_accepts: int = 1,
    fabric_required_unique_proof_validators: int = 1,
    fabric_required_unique_trust_validators: int = 1,
    fabric_required_validator_ids: list[str] | None = None,
    fabric_enforce_required_validator_ids: bool = False,
    fabric_reject_on_any_reject: bool = False,
    fabric_retry_attempts: int = 2,
    fabric_pending_timeout_ms: int | None = None,
    fabric_transport: str = "memory",
    fabric_transport_host: str = "127.0.0.1",
    fabric_transport_port: int = 0,
    fabric_transport_connect: bool = False,
    fabric_transport_keep_open: bool = False,
    fabric_transport_backpressure_max_pending: int | None = None,
    fabric_transport_backpressure_policy: str = "block",
    fabric_transport_backpressure_block_timeout_ms: int = 200,
    fabric_artifact_dir: str | None = None,
    fabric_inline_bridge: bool = True,
    fabric_replay_sample_stride: int = 0,
    fabric_epoch_state_path: str | None = None,
    fabric_epoch_replica_state_paths: list[str] | None = None,
    fabric_epoch_replica_read_quorum: int | None = None,
    fabric_epoch_replica_write_quorum: int | None = None,
    fabric_epoch_lock_timeout_ms: int = 5000,
    fabric_epoch_lock_poll_ms: int = 10,
    fabric_epoch_lock_stale_ms: int | None = 30000,
    fabric_epoch_consensus_required_total_accepts: int = 1,
    fabric_epoch_consensus_timeout_ms: int = 200,
    fabric_epoch_consensus_reject_on_any_reject: bool = False,
    fabric_epoch_consensus_channel: str = "fabric.epoch",
    fabric_epoch_consensus_enabled: bool = False,
    fabric_split_mode_channels: bool = False,
    fabric_commit_retry_attempts: int = 2,
    fabric_delivery_required_receipts: int = 0,
    fabric_delivery_required_validator_ids: list[str] | None = None,
    fabric_delivery_enforce_required_validator_ids: bool = False,
    fabric_delivery_reject_on_any_reject: bool = False,
    fabric_delivery_retry_interval_ms: int = 100,
    fabric_delivery_max_attempts: int = 3,
    fabric_delivery_timeout_ms: int = 500,
    fabric_delivery_ack_channel: str = "fabric.delivery.ack",
    fabric_delivery_emit_ack: bool = True,
    fabric_delivery_outbox_path: str | None = None,
    fabric_delivery_outbox_max_entries: int | None = None,
    fabric_delivery_outbox_flush_limit: int | None = None,
    fabric_delivery_outbox_drop_policy: str = "audit_first",
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    level_name = str(config.level_policy.active_level or "L0")

    def _storage_policy(artifact: str) -> Dict[str, int]:
        return config.resolve_artifact_storage_policy(artifact=str(artifact), level=level_name)

    session = DetmSession.create(config, seed)
    if invariant_streams:
        inv_policy = _storage_policy("invariants")
        InvariantCoarsener.attach(session.bus, parse_invariant_streams(invariant_streams))
        InvariantTickJsonlWriter.attach(
            session.bus,
            out_dir / "invariants.jsonl",
            retention_window=int(inv_policy.get("retention_window", 0)),
            compaction_budget=int(inv_policy.get("compaction_budget", 0)),
        )
    history_policy = _storage_policy("history")
    TraceRecorder.attach(
        session.bus,
        out_dir,
        retention_window=int(history_policy.get("retention_window", 0)),
        compaction_budget=int(history_policy.get("compaction_budget", 0)),
    )
    ArtifactWriter.attach(session.bus, out_dir)
    trace_policy = _storage_policy("trace")
    JsonlTraceWriter.attach(
        session.bus,
        out_dir / "trace.jsonl",
        retention_window=int(trace_policy.get("retention_window", 0)),
        compaction_budget=int(trace_policy.get("compaction_budget", 0)),
    )
    if bool(config.watch_trace_enabled):
        watch_policy = _storage_policy("watch_trace")
        watch_contract_policy = _storage_policy("watch_contract")
        outerfields_policy = _storage_policy("outerfields")
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
    commits_policy = _storage_policy("commits")
    CommitJsonlWriter.attach(
        session.bus,
        out_dir / "commits.jsonl",
        node_id=f"seed_{int(seed):04d}",
        mode="realtime",
        retention_window=int(commits_policy.get("retention_window", 0)),
        compaction_budget=int(commits_policy.get("compaction_budget", 0)),
    )
    if bool(config.level_policy.audit_commit_enabled):
        commits_audit_policy = _storage_policy("commits_audit")
        CommitJsonlWriter.attach(
            session.bus,
            out_dir / "commits_audit.jsonl",
            node_id=f"seed_{int(seed):04d}",
            commit_type="proof",
            mode="audit",
            retention_window=int(commits_audit_policy.get("retention_window", 0)),
            compaction_budget=int(commits_audit_policy.get("compaction_budget", 0)),
        )
    commit_validation_policy = _storage_policy("commit_validation")
    CommitValidationReporter.attach(
        session.bus,
        out_dir,
        retention_window=int(commit_validation_policy.get("retention_window", 0)),
        compaction_budget=int(commit_validation_policy.get("compaction_budget", 0)),
    )
    if bool(fabric_handshake):
        fabric_acks_policy = _storage_policy("fabric_acks")
        fabric_ack_envelopes_policy = _storage_policy("fabric_ack_envelopes")
        fabric_delivery_acks_policy = _storage_policy("fabric_delivery_acks")
        fabric_dead_letters_policy = _storage_policy("fabric_dead_letters")
        fabric_quorum_report_policy = _storage_policy("fabric_quorum_report")
        FabricHandshakeRecorder.attach(
            session.bus,
            out_dir,
            node_id=f"seed_{int(seed):04d}",
            mode_filter="realtime",
            required_proof_accepts=max(1, int(fabric_required_proof_accepts)),
            required_trust_accepts=max(1, int(fabric_required_trust_accepts)),
            required_unique_proof_validators=max(1, int(fabric_required_unique_proof_validators)),
            required_unique_trust_validators=max(1, int(fabric_required_unique_trust_validators)),
            required_validator_ids=[str(v).strip() for v in list(fabric_required_validator_ids or []) if str(v).strip()],
            enforce_required_validator_ids=bool(fabric_enforce_required_validator_ids),
            reject_on_any_reject=bool(fabric_reject_on_any_reject),
            publish_retry_attempts=max(1, int(fabric_retry_attempts)),
            pending_timeout_ms=None if fabric_pending_timeout_ms is None else max(0, int(fabric_pending_timeout_ms)),
            transport=str(fabric_transport),
            transport_host=str(fabric_transport_host),
            transport_port=int(fabric_transport_port),
            transport_connect=bool(fabric_transport_connect),
            transport_keep_open=bool(fabric_transport_keep_open),
            transport_backpressure_max_pending=None
            if fabric_transport_backpressure_max_pending is None
            else max(1, int(fabric_transport_backpressure_max_pending)),
            transport_backpressure_policy=str(fabric_transport_backpressure_policy),
            transport_backpressure_block_timeout_ms=max(0, int(fabric_transport_backpressure_block_timeout_ms)),
            artifact_store_dir=None if fabric_artifact_dir is None else str(fabric_artifact_dir),
            publish_inline_payload=bool(fabric_inline_bridge),
            replay_sample_stride=max(0, int(fabric_replay_sample_stride)),
            epoch_state_path=None if fabric_epoch_state_path is None else str(fabric_epoch_state_path),
            epoch_replica_state_paths=[str(v).strip() for v in list(fabric_epoch_replica_state_paths or []) if str(v).strip()],
            epoch_replica_read_quorum=None
            if fabric_epoch_replica_read_quorum is None
            else max(1, int(fabric_epoch_replica_read_quorum)),
            epoch_replica_write_quorum=None
            if fabric_epoch_replica_write_quorum is None
            else max(1, int(fabric_epoch_replica_write_quorum)),
            epoch_lock_timeout_ms=max(1, int(fabric_epoch_lock_timeout_ms)),
            epoch_lock_poll_ms=max(1, int(fabric_epoch_lock_poll_ms)),
            epoch_lock_stale_ms=None
            if fabric_epoch_lock_stale_ms is None
            else max(1, int(fabric_epoch_lock_stale_ms)),
            epoch_consensus_required_total_accepts=max(1, int(fabric_epoch_consensus_required_total_accepts)),
            epoch_consensus_timeout_ms=max(1, int(fabric_epoch_consensus_timeout_ms)),
            epoch_consensus_reject_on_any_reject=bool(fabric_epoch_consensus_reject_on_any_reject),
            epoch_consensus_channel=str(fabric_epoch_consensus_channel),
            epoch_consensus_enabled=bool(fabric_epoch_consensus_enabled),
            split_mode_channels=bool(fabric_split_mode_channels),
            commit_publish_retry_attempts=max(1, int(fabric_commit_retry_attempts)),
            delivery_required_receipts=max(0, int(fabric_delivery_required_receipts)),
            delivery_required_validator_ids=[
                str(v).strip() for v in list(fabric_delivery_required_validator_ids or []) if str(v).strip()
            ],
            delivery_enforce_required_validator_ids=bool(fabric_delivery_enforce_required_validator_ids),
            delivery_reject_on_any_reject=bool(fabric_delivery_reject_on_any_reject),
            delivery_retry_interval_ms=max(0, int(fabric_delivery_retry_interval_ms)),
            delivery_max_attempts=max(1, int(fabric_delivery_max_attempts)),
            delivery_timeout_ms=max(1, int(fabric_delivery_timeout_ms)),
            delivery_ack_channel=str(fabric_delivery_ack_channel),
            delivery_emit_ack=bool(fabric_delivery_emit_ack),
            delivery_outbox_path=None if fabric_delivery_outbox_path is None else str(fabric_delivery_outbox_path),
            delivery_outbox_max_entries=None
            if fabric_delivery_outbox_max_entries is None
            else max(1, int(fabric_delivery_outbox_max_entries)),
            delivery_outbox_flush_limit=None
            if fabric_delivery_outbox_flush_limit is None
            else max(1, int(fabric_delivery_outbox_flush_limit)),
            delivery_outbox_drop_policy=str(fabric_delivery_outbox_drop_policy),
            fabric_acks_retention_window=int(fabric_acks_policy.get("retention_window", 0)),
            fabric_acks_compaction_budget=int(fabric_acks_policy.get("compaction_budget", 0)),
            fabric_ack_envelopes_retention_window=int(fabric_ack_envelopes_policy.get("retention_window", 0)),
            fabric_ack_envelopes_compaction_budget=int(fabric_ack_envelopes_policy.get("compaction_budget", 0)),
            fabric_delivery_acks_retention_window=int(fabric_delivery_acks_policy.get("retention_window", 0)),
            fabric_delivery_acks_compaction_budget=int(fabric_delivery_acks_policy.get("compaction_budget", 0)),
            fabric_dead_letters_retention_window=int(fabric_dead_letters_policy.get("retention_window", 0)),
            fabric_dead_letters_compaction_budget=int(fabric_dead_letters_policy.get("compaction_budget", 0)),
            fabric_quorum_report_retention_window=int(fabric_quorum_report_policy.get("retention_window", 0)),
            fabric_quorum_report_compaction_budget=int(fabric_quorum_report_policy.get("compaction_budget", 0)),
        )
    if viz_transport is not None:
        VizStreamer.attach(session.bus, viz_transport, every_steps=viz_every_steps)
    if fields_npz:
        FieldHistoryRecorder.attach(
            session.bus,
            out_dir / "fields_hist.npz",
            every_steps=int(fields_every_steps),
            dtype="float32",
        )

    for sid in symbol_ids:
        influence = make_symbol(sid)
        session.step(influence, steps)

    digest = session.digest()
    session.close()
    return {"seed": int(seed), "digest": digest.as_dict(), "dir": str(out_dir)}


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preset", default="default", choices=sorted(set(preset_names())), help="Packaged preset name")
    ap.add_argument("--config", default=None, help="Path to override config (.json or .py; may include `runner` defaults)")

    ap.add_argument("--backend", default=None, choices=["torch", "numpy"], help="Override backend")
    ap.add_argument("--device", default=None, help="Override device (e.g. cuda/cpu)")
    ap.add_argument("--width", type=int, default=None, help="Override lattice width")
    ap.add_argument("--height", type=int, default=None, help="Override lattice height")
    ap.add_argument("--boundary", default=None, choices=["periodic", "open"], help="Override boundary condition")

    ap.add_argument("--seed", type=int, default=None, help="Seed")
    ap.add_argument("--seed0", type=int, default=None, help="Seed start for --batch")
    ap.add_argument("--batch", type=int, default=None, help="Run N episodes with seeds seed0..seed0+N-1")

    ap.add_argument("--steps", type=int, default=None, help="Ticks per influence")
    ap.add_argument("--symbols", nargs="*", default=None, help="Symbol IDs to apply (default: all)")
    ap.add_argument("--out", default=None, help="Output directory root (default: runs/out/run_<timestamp>)")

    ap.add_argument(
        "--viz",
        dest="viz",
        action="store_true",
        default=None,
        help="Start a local viz daemon and stream state updates",
    )
    ap.add_argument(
        "--no-viz",
        dest="viz",
        action="store_false",
        help="Disable viz streaming (overrides config)",
    )
    ap.add_argument("--viz-transport", default=None, choices=["tcp", "none"], help="Visualization transport")
    ap.add_argument(
        "--viz-connect",
        dest="viz_connect",
        action="store_true",
        default=None,
        help="Connect to an existing viz daemon (requires --viz-host/--viz-port)",
    )
    ap.add_argument("--viz-host", default=None, help="Viz daemon host (default: localhost)")
    ap.add_argument("--viz-port", type=int, default=None, help="Viz daemon port (0 = auto when starting locally)")
    ap.add_argument(
        "--viz-keep-open",
        dest="viz_keep_open",
        action="store_true",
        default=None,
        help="Do not terminate the locally started viz daemon after the run finishes",
    )
    ap.add_argument("--viz-every-steps", type=int, default=None, help="Send viz updates every N step_count increments")

    ap.add_argument(
        "--record-fields",
        dest="record_fields",
        action="store_true",
        default=None,
        help="Write `fields_hist.npz` with E/S/tau (+J approx) history",
    )
    ap.add_argument("--no-record-fields", dest="record_fields", action="store_false", help="Disable fields recording")
    ap.add_argument("--fields-every-steps", type=int, default=None, help="Record fields every N step_count increments")

    ap.add_argument(
        "--invariant-stream",
        action="append",
        default=None,
        help="Add invariant stream spec (e.g. inv0=1/10). Repeatable; comma-separated also accepted.",
    )
    ap.add_argument(
        "--fabric-handshake",
        dest="fabric_handshake",
        action="store_true",
        default=None,
        help="Enable local fabric handshake artifacts (`fabric_acks.jsonl` + envelopes)",
    )
    ap.add_argument(
        "--no-fabric-handshake",
        dest="fabric_handshake",
        action="store_false",
        help="Disable local fabric handshake artifacts",
    )
    ap.add_argument(
        "--fabric-proof-quorum",
        type=int,
        default=None,
        help="Required number of accepted proof_ack for quorum (default: 1)",
    )
    ap.add_argument(
        "--fabric-trust-quorum",
        type=int,
        default=None,
        help="Required number of accepted trust_ack for quorum (default: 1)",
    )
    ap.add_argument(
        "--fabric-unique-proof-validators",
        type=int,
        default=None,
        help="Required number of unique validators in accepted proof_ack set (default: 1)",
    )
    ap.add_argument(
        "--fabric-unique-trust-validators",
        type=int,
        default=None,
        help="Required number of unique validators in accepted trust_ack set (default: 1)",
    )
    ap.add_argument(
        "--fabric-validator-set",
        default=None,
        help="Comma-separated required validator ids (used when enforce flag is enabled)",
    )
    ap.add_argument(
        "--fabric-enforce-validator-set",
        dest="fabric_enforce_validator_set",
        action="store_true",
        default=None,
        help="Enforce presence of validator ids from --fabric-validator-set in proof and trust ack sets",
    )
    ap.add_argument(
        "--fabric-reject-on-any-reject",
        dest="fabric_reject_on_any_reject",
        action="store_true",
        default=None,
        help="Reject commit quorum if any ack is rejected",
    )
    ap.add_argument(
        "--fabric-retry-attempts",
        type=int,
        default=None,
        help="Ack envelope publish retry attempts (default: 2)",
    )
    ap.add_argument(
        "--fabric-commit-retry-attempts",
        type=int,
        default=None,
        help="Commit envelope publish retry attempts (default: 2)",
    )
    ap.add_argument(
        "--fabric-pending-timeout-ms",
        type=int,
        default=None,
        help="Pending quorum timeout in ms (default: disabled)",
    )
    ap.add_argument(
        "--fabric-transport",
        default=None,
        choices=["memory", "tcp"],
        help="Fabric transport adapter for handshake wiring",
    )
    ap.add_argument("--fabric-transport-host", default=None, help="Fabric transport host")
    ap.add_argument("--fabric-transport-port", type=int, default=None, help="Fabric transport port")
    ap.add_argument(
        "--fabric-transport-connect",
        dest="fabric_transport_connect",
        action="store_true",
        default=None,
        help="Connect to existing fabric relay (tcp only)",
    )
    ap.add_argument(
        "--fabric-transport-keep-open",
        dest="fabric_transport_keep_open",
        action="store_true",
        default=None,
        help="Keep local fabric relay open after run (tcp local start)",
    )
    ap.add_argument(
        "--fabric-transport-backpressure-max-pending",
        type=int,
        default=None,
        help="Max pending envelopes in live transport buffer (default: disabled)",
    )
    ap.add_argument(
        "--fabric-transport-backpressure-policy",
        choices=["block", "drop_oldest", "drop_newest", "fail"],
        default=None,
        help="Backpressure policy for live transport buffer overflow",
    )
    ap.add_argument(
        "--fabric-transport-backpressure-block-timeout-ms",
        type=int,
        default=None,
        help="Block policy timeout in ms for live transport buffer",
    )
    ap.add_argument(
        "--fabric-artifact-dir",
        default=None,
        help="Shared artifact directory for durable commit/ack resolver (default: disabled)",
    )
    ap.add_argument(
        "--fabric-inline-bridge",
        dest="fabric_inline_bridge",
        action="store_true",
        default=None,
        help="Enable inline payload bridge in fabric envelopes (default: enabled)",
    )
    ap.add_argument(
        "--fabric-no-inline-bridge",
        dest="fabric_inline_bridge",
        action="store_false",
        help="Disable inline payload bridge in fabric envelopes (requires shared artifact resolver)",
    )
    ap.add_argument(
        "--fabric-replay-sample-stride",
        type=int,
        default=None,
        help="Replay-check sampling stride for validator (0 disables sampling)",
    )
    ap.add_argument(
        "--fabric-epoch-state-path",
        default=None,
        help="Shared epoch/watermark state file path for distributed coordinator (default: in-memory)",
    )
    ap.add_argument(
        "--fabric-epoch-replica-state",
        action="append",
        default=None,
        help="Replica epoch-state file path (repeatable, also accepts comma-separated values)",
    )
    ap.add_argument(
        "--fabric-epoch-read-quorum",
        type=int,
        default=None,
        help="Read quorum for replicated epoch coordinator (default: majority)",
    )
    ap.add_argument(
        "--fabric-epoch-write-quorum",
        type=int,
        default=None,
        help="Write quorum for replicated epoch coordinator (default: majority)",
    )
    ap.add_argument(
        "--fabric-epoch-lock-timeout-ms",
        type=int,
        default=None,
        help="Epoch-state lock timeout in ms for file coordinator (default: 5000)",
    )
    ap.add_argument(
        "--fabric-epoch-lock-poll-ms",
        type=int,
        default=None,
        help="Epoch-state lock poll interval in ms (default: 10)",
    )
    ap.add_argument(
        "--fabric-epoch-lock-stale-ms",
        type=int,
        default=None,
        help="Epoch-state stale lock threshold in ms (default: 30000, <=0 disables stale cleanup)",
    )
    ap.add_argument(
        "--fabric-epoch-consensus",
        dest="fabric_epoch_consensus_enabled",
        action="store_true",
        default=None,
        help="Enable transport-based pre-consensus for epoch decisions",
    )
    ap.add_argument(
        "--fabric-no-epoch-consensus",
        dest="fabric_epoch_consensus_enabled",
        action="store_false",
        help="Disable transport-based pre-consensus for epoch decisions",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-required-total-accepts",
        type=int,
        default=None,
        help="Total accepts (including local) required for epoch consensus (default: 1)",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-timeout-ms",
        type=int,
        default=None,
        help="Timeout in ms for epoch consensus proposal collection (default: 200)",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-reject-on-any-reject",
        dest="fabric_epoch_consensus_reject_on_any_reject",
        action="store_true",
        default=None,
        help="Reject epoch proposal if any peer vote is rejected",
    )
    ap.add_argument(
        "--fabric-epoch-consensus-channel",
        default=None,
        help="Transport channel for epoch consensus proposals/votes (default: fabric.epoch)",
    )
    ap.add_argument(
        "--fabric-delivery-outbox-path",
        default=None,
        help="Path to file-backed fabric delivery outbox (default: <run>/fabric_delivery_outbox.jsonl)",
    )
    ap.add_argument(
        "--fabric-delivery-outbox-max-entries",
        type=int,
        default=None,
        help="Max number of pending envelopes kept in delivery outbox (default: unlimited)",
    )
    ap.add_argument(
        "--fabric-delivery-outbox-flush-limit",
        type=int,
        default=None,
        help="Max queued envelopes flushed per publish attempt (default: all pending)",
    )
    ap.add_argument(
        "--fabric-delivery-outbox-drop-policy",
        choices=["audit_first", "oldest", "newest"],
        default=None,
        help="Outbox overflow policy: prefer dropping audit envelopes or FIFO/LIFO style",
    )
    ap.add_argument(
        "--fabric-split-mode-channels",
        dest="fabric_split_mode_channels",
        action="store_true",
        default=None,
        help="Use separate fabric channels for realtime/audit envelopes",
    )
    ap.add_argument(
        "--fabric-no-split-mode-channels",
        dest="fabric_split_mode_channels",
        action="store_false",
        help="Use shared fabric channels for realtime/audit envelopes",
    )
    ap.add_argument(
        "--fabric-delivery-required-receipts",
        type=int,
        default=None,
        help="Required number of delivery_ack receipts per commit envelope (0 disables receipt tracking)",
    )
    ap.add_argument(
        "--fabric-delivery-validator-set",
        default=None,
        help="Comma-separated required validator ids for delivery receipts",
    )
    ap.add_argument(
        "--fabric-delivery-enforce-validator-set",
        dest="fabric_delivery_enforce_validator_set",
        action="store_true",
        default=None,
        help="Require delivery receipts from all ids listed in --fabric-delivery-validator-set",
    )
    ap.add_argument(
        "--fabric-no-delivery-enforce-validator-set",
        dest="fabric_delivery_enforce_validator_set",
        action="store_false",
        help="Do not enforce full delivery validator set",
    )
    ap.add_argument(
        "--fabric-delivery-reject-on-any-reject",
        dest="fabric_delivery_reject_on_any_reject",
        action="store_true",
        default=None,
        help="Reject tracked delivery when any delivery_ack has rejected/error status",
    )
    ap.add_argument(
        "--fabric-no-delivery-reject-on-any-reject",
        dest="fabric_delivery_reject_on_any_reject",
        action="store_false",
        help="Do not reject tracked delivery on single rejected/error receipt",
    )
    ap.add_argument(
        "--fabric-delivery-retry-interval-ms",
        type=int,
        default=None,
        help="Retry interval in ms for pending delivery receipts",
    )
    ap.add_argument(
        "--fabric-delivery-max-attempts",
        type=int,
        default=None,
        help="Maximum publish attempts per tracked commit delivery",
    )
    ap.add_argument(
        "--fabric-delivery-timeout-ms",
        type=int,
        default=None,
        help="Timeout in ms for tracked commit delivery receipts",
    )
    ap.add_argument(
        "--fabric-delivery-ack-channel",
        default=None,
        help="Channel for delivery_ack envelopes",
    )
    ap.add_argument(
        "--fabric-delivery-emit-ack",
        dest="fabric_delivery_emit_ack",
        action="store_true",
        default=None,
        help="Emit delivery_ack envelopes on commit receive",
    )
    ap.add_argument(
        "--fabric-no-delivery-emit-ack",
        dest="fabric_delivery_emit_ack",
        action="store_false",
        help="Disable delivery_ack envelope emission on commit receive",
    )

    ap.add_argument("--list-symbols", action="store_true", help="Print known symbol IDs and exit")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = _build_parser()
    args = ap.parse_args(argv)

    if args.list_symbols:
        print("\n".join(list_symbols()))
        return 0

    payload = load_merged_payload(preset=str(args.preset), override_path=args.config)
    config = build_runtime_config(payload)
    runner_defaults = _runner_defaults(payload)

    runtime_overrides: Dict[str, Any] = {}
    if args.backend is not None:
        runtime_overrides["backend"] = args.backend
    if args.device is not None:
        runtime_overrides["device"] = args.device
    if args.width is not None:
        runtime_overrides["width"] = int(args.width)
    if args.height is not None:
        runtime_overrides["height"] = int(args.height)
    if args.boundary is not None:
        runtime_overrides["boundary"] = str(args.boundary)
    if runtime_overrides:
        config = DETMConfig.from_dict({**config.to_dict(), **runtime_overrides})

    seed0 = int(args.seed0) if args.seed0 is not None else int(runner_defaults.get("seed0", 0))
    seed = int(args.seed) if args.seed is not None else int(runner_defaults.get("seed", 1))
    steps = int(args.steps) if args.steps is not None else int(runner_defaults.get("steps", 4))
    out_root = _default_out_dir(args.out if args.out is not None else runner_defaults.get("out"))

    symbols_cfg = _as_list(runner_defaults.get("symbols"))
    symbol_ids = _resolve_symbols(args.symbols if args.symbols is not None else symbols_cfg)

    viz_enabled = args.viz if args.viz is not None else bool(runner_defaults.get("viz", False))
    viz_transport_name = (
        str(args.viz_transport) if args.viz_transport is not None else str(runner_defaults.get("viz_transport", "tcp"))
    )
    viz_host = str(args.viz_host) if args.viz_host is not None else str(runner_defaults.get("viz_host", "127.0.0.1"))
    viz_port = int(args.viz_port) if args.viz_port is not None else int(runner_defaults.get("viz_port", 0))
    viz_connect = args.viz_connect if args.viz_connect is not None else bool(runner_defaults.get("viz_connect", False))
    viz_keep_open = (
        args.viz_keep_open if args.viz_keep_open is not None else bool(runner_defaults.get("viz_keep_open", False))
    )
    viz_every_steps = (
        int(args.viz_every_steps)
        if args.viz_every_steps is not None
        else int(runner_defaults.get("viz_every_steps", 1))
    )

    record_fields = (
        args.record_fields if args.record_fields is not None else bool(runner_defaults.get("record_fields", False))
    )
    fields_every_steps = (
        int(args.fields_every_steps)
        if args.fields_every_steps is not None
        else int(runner_defaults.get("fields_every_steps", 1))
    )

    invariant_streams = None
    if args.invariant_stream is not None:
        invariant_streams = list(args.invariant_stream)
    else:
        inv = runner_defaults.get("invariant_streams")
        invariant_streams = _as_list(inv)

    fabric_handshake = (
        args.fabric_handshake
        if args.fabric_handshake is not None
        else bool(runner_defaults.get("fabric_handshake", False))
    )
    fabric_required_proof_accepts = (
        int(args.fabric_proof_quorum)
        if args.fabric_proof_quorum is not None
        else int(runner_defaults.get("fabric_required_proof_accepts", 1))
    )
    fabric_required_trust_accepts = (
        int(args.fabric_trust_quorum)
        if args.fabric_trust_quorum is not None
        else int(runner_defaults.get("fabric_required_trust_accepts", 1))
    )
    fabric_required_unique_proof_validators = (
        int(args.fabric_unique_proof_validators)
        if args.fabric_unique_proof_validators is not None
        else int(runner_defaults.get("fabric_required_unique_proof_validators", 1))
    )
    fabric_required_unique_trust_validators = (
        int(args.fabric_unique_trust_validators)
        if args.fabric_unique_trust_validators is not None
        else int(runner_defaults.get("fabric_required_unique_trust_validators", 1))
    )
    if args.fabric_validator_set is not None:
        fabric_required_validator_ids = _as_list(args.fabric_validator_set)
    else:
        fabric_required_validator_ids = _as_list(runner_defaults.get("fabric_required_validator_ids"))
    fabric_enforce_required_validator_ids = (
        bool(args.fabric_enforce_validator_set)
        if args.fabric_enforce_validator_set is not None
        else bool(runner_defaults.get("fabric_enforce_required_validator_ids", False))
    )
    fabric_reject_on_any_reject = (
        bool(args.fabric_reject_on_any_reject)
        if args.fabric_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_reject_on_any_reject", False))
    )
    fabric_retry_attempts = (
        int(args.fabric_retry_attempts)
        if args.fabric_retry_attempts is not None
        else int(runner_defaults.get("fabric_retry_attempts", 2))
    )
    fabric_commit_retry_attempts = (
        int(args.fabric_commit_retry_attempts)
        if args.fabric_commit_retry_attempts is not None
        else int(runner_defaults.get("fabric_commit_retry_attempts", 2))
    )
    fabric_pending_timeout_ms = (
        int(args.fabric_pending_timeout_ms)
        if args.fabric_pending_timeout_ms is not None
        else (
            None
            if runner_defaults.get("fabric_pending_timeout_ms") is None
            else int(runner_defaults.get("fabric_pending_timeout_ms"))
        )
    )
    fabric_transport = (
        str(args.fabric_transport)
        if args.fabric_transport is not None
        else str(runner_defaults.get("fabric_transport", "memory"))
    )
    fabric_transport_host = (
        str(args.fabric_transport_host)
        if args.fabric_transport_host is not None
        else str(runner_defaults.get("fabric_transport_host", "127.0.0.1"))
    )
    fabric_transport_port = (
        int(args.fabric_transport_port)
        if args.fabric_transport_port is not None
        else int(runner_defaults.get("fabric_transport_port", 0))
    )
    fabric_transport_connect = (
        bool(args.fabric_transport_connect)
        if args.fabric_transport_connect is not None
        else bool(runner_defaults.get("fabric_transport_connect", False))
    )
    fabric_transport_keep_open = (
        bool(args.fabric_transport_keep_open)
        if args.fabric_transport_keep_open is not None
        else bool(runner_defaults.get("fabric_transport_keep_open", False))
    )
    fabric_transport_backpressure_max_pending = (
        int(args.fabric_transport_backpressure_max_pending)
        if args.fabric_transport_backpressure_max_pending is not None
        else (
            None
            if runner_defaults.get("fabric_transport_backpressure_max_pending") is None
            else int(runner_defaults.get("fabric_transport_backpressure_max_pending"))
        )
    )
    fabric_transport_backpressure_policy = (
        str(args.fabric_transport_backpressure_policy)
        if args.fabric_transport_backpressure_policy is not None
        else str(runner_defaults.get("fabric_transport_backpressure_policy", "block"))
    )
    fabric_transport_backpressure_block_timeout_ms = (
        int(args.fabric_transport_backpressure_block_timeout_ms)
        if args.fabric_transport_backpressure_block_timeout_ms is not None
        else int(runner_defaults.get("fabric_transport_backpressure_block_timeout_ms", 200))
    )
    fabric_artifact_dir = (
        str(args.fabric_artifact_dir)
        if args.fabric_artifact_dir is not None
        else (
            None
            if runner_defaults.get("fabric_artifact_dir") is None
            else str(runner_defaults.get("fabric_artifact_dir"))
        )
    )
    fabric_inline_bridge = (
        bool(args.fabric_inline_bridge)
        if args.fabric_inline_bridge is not None
        else bool(runner_defaults.get("fabric_inline_bridge", True))
    )
    fabric_replay_sample_stride = (
        int(args.fabric_replay_sample_stride)
        if args.fabric_replay_sample_stride is not None
        else int(runner_defaults.get("fabric_replay_sample_stride", 0))
    )
    fabric_epoch_state_path = (
        str(args.fabric_epoch_state_path)
        if args.fabric_epoch_state_path is not None
        else (
            None
            if runner_defaults.get("fabric_epoch_state_path") is None
            else str(runner_defaults.get("fabric_epoch_state_path"))
        )
    )
    if args.fabric_epoch_replica_state is not None:
        fabric_epoch_replica_state_paths = _flatten_list_args(list(args.fabric_epoch_replica_state))
    else:
        fabric_epoch_replica_state_paths = _as_list(runner_defaults.get("fabric_epoch_replica_state_paths"))
    fabric_epoch_replica_read_quorum = (
        int(args.fabric_epoch_read_quorum)
        if args.fabric_epoch_read_quorum is not None
        else (
            None
            if runner_defaults.get("fabric_epoch_replica_read_quorum") is None
            else int(runner_defaults.get("fabric_epoch_replica_read_quorum"))
        )
    )
    fabric_epoch_replica_write_quorum = (
        int(args.fabric_epoch_write_quorum)
        if args.fabric_epoch_write_quorum is not None
        else (
            None
            if runner_defaults.get("fabric_epoch_replica_write_quorum") is None
            else int(runner_defaults.get("fabric_epoch_replica_write_quorum"))
        )
    )
    fabric_epoch_lock_timeout_ms = (
        int(args.fabric_epoch_lock_timeout_ms)
        if args.fabric_epoch_lock_timeout_ms is not None
        else int(runner_defaults.get("fabric_epoch_lock_timeout_ms", 5000))
    )
    fabric_epoch_lock_poll_ms = (
        int(args.fabric_epoch_lock_poll_ms)
        if args.fabric_epoch_lock_poll_ms is not None
        else int(runner_defaults.get("fabric_epoch_lock_poll_ms", 10))
    )
    raw_stale = (
        args.fabric_epoch_lock_stale_ms
        if args.fabric_epoch_lock_stale_ms is not None
        else runner_defaults.get("fabric_epoch_lock_stale_ms", 30000)
    )
    fabric_epoch_lock_stale_ms = None if raw_stale is None or int(raw_stale) <= 0 else int(raw_stale)
    fabric_epoch_consensus_enabled = (
        bool(args.fabric_epoch_consensus_enabled)
        if args.fabric_epoch_consensus_enabled is not None
        else bool(runner_defaults.get("fabric_epoch_consensus_enabled", False))
    )
    fabric_epoch_consensus_required_total_accepts = (
        int(args.fabric_epoch_consensus_required_total_accepts)
        if args.fabric_epoch_consensus_required_total_accepts is not None
        else int(runner_defaults.get("fabric_epoch_consensus_required_total_accepts", 1))
    )
    fabric_epoch_consensus_timeout_ms = (
        int(args.fabric_epoch_consensus_timeout_ms)
        if args.fabric_epoch_consensus_timeout_ms is not None
        else int(runner_defaults.get("fabric_epoch_consensus_timeout_ms", 200))
    )
    fabric_epoch_consensus_reject_on_any_reject = (
        bool(args.fabric_epoch_consensus_reject_on_any_reject)
        if args.fabric_epoch_consensus_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_epoch_consensus_reject_on_any_reject", False))
    )
    fabric_epoch_consensus_channel = (
        str(args.fabric_epoch_consensus_channel)
        if args.fabric_epoch_consensus_channel is not None
        else str(runner_defaults.get("fabric_epoch_consensus_channel", "fabric.epoch"))
    )
    fabric_split_mode_channels = (
        bool(args.fabric_split_mode_channels)
        if args.fabric_split_mode_channels is not None
        else bool(runner_defaults.get("fabric_split_mode_channels", False))
    )
    fabric_delivery_required_receipts = (
        int(args.fabric_delivery_required_receipts)
        if args.fabric_delivery_required_receipts is not None
        else int(runner_defaults.get("fabric_delivery_required_receipts", 0))
    )
    if args.fabric_delivery_validator_set is not None:
        fabric_delivery_required_validator_ids = _as_list(args.fabric_delivery_validator_set)
    else:
        fabric_delivery_required_validator_ids = _as_list(runner_defaults.get("fabric_delivery_required_validator_ids"))
    fabric_delivery_enforce_required_validator_ids = (
        bool(args.fabric_delivery_enforce_validator_set)
        if args.fabric_delivery_enforce_validator_set is not None
        else bool(runner_defaults.get("fabric_delivery_enforce_required_validator_ids", False))
    )
    fabric_delivery_reject_on_any_reject = (
        bool(args.fabric_delivery_reject_on_any_reject)
        if args.fabric_delivery_reject_on_any_reject is not None
        else bool(runner_defaults.get("fabric_delivery_reject_on_any_reject", False))
    )
    fabric_delivery_retry_interval_ms = (
        int(args.fabric_delivery_retry_interval_ms)
        if args.fabric_delivery_retry_interval_ms is not None
        else int(runner_defaults.get("fabric_delivery_retry_interval_ms", 100))
    )
    fabric_delivery_max_attempts = (
        int(args.fabric_delivery_max_attempts)
        if args.fabric_delivery_max_attempts is not None
        else int(runner_defaults.get("fabric_delivery_max_attempts", 3))
    )
    fabric_delivery_timeout_ms = (
        int(args.fabric_delivery_timeout_ms)
        if args.fabric_delivery_timeout_ms is not None
        else int(runner_defaults.get("fabric_delivery_timeout_ms", 500))
    )
    fabric_delivery_ack_channel = (
        str(args.fabric_delivery_ack_channel)
        if args.fabric_delivery_ack_channel is not None
        else str(runner_defaults.get("fabric_delivery_ack_channel", "fabric.delivery.ack"))
    )
    fabric_delivery_emit_ack = (
        bool(args.fabric_delivery_emit_ack)
        if args.fabric_delivery_emit_ack is not None
        else bool(runner_defaults.get("fabric_delivery_emit_ack", True))
    )
    fabric_delivery_outbox_path = (
        str(args.fabric_delivery_outbox_path)
        if args.fabric_delivery_outbox_path is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_outbox_path") is None
            else str(runner_defaults.get("fabric_delivery_outbox_path"))
        )
    )
    fabric_delivery_outbox_max_entries = (
        int(args.fabric_delivery_outbox_max_entries)
        if args.fabric_delivery_outbox_max_entries is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_outbox_max_entries") is None
            else int(runner_defaults.get("fabric_delivery_outbox_max_entries"))
        )
    )
    fabric_delivery_outbox_flush_limit = (
        int(args.fabric_delivery_outbox_flush_limit)
        if args.fabric_delivery_outbox_flush_limit is not None
        else (
            None
            if runner_defaults.get("fabric_delivery_outbox_flush_limit") is None
            else int(runner_defaults.get("fabric_delivery_outbox_flush_limit"))
        )
    )
    fabric_delivery_outbox_drop_policy = (
        str(args.fabric_delivery_outbox_drop_policy)
        if args.fabric_delivery_outbox_drop_policy is not None
        else str(runner_defaults.get("fabric_delivery_outbox_drop_policy", "audit_first"))
    )

    if viz_enabled and args.batch is not None:
        raise SystemExit("--viz is supported only for a single run (omit --batch)")

    viz_transport = None
    if viz_enabled and str(viz_transport_name).lower() != "none":
        viz_transport = open_viz_transport(
            enabled=True,
            transport=str(viz_transport_name),
            host=str(viz_host),
            port=int(viz_port),
            connect=bool(viz_connect),
            keep_open=bool(viz_keep_open),
        )

    runs: list[dict] = []
    try:
        if args.batch is not None:
            for i in range(int(args.batch)):
                episode_seed = int(seed0) + i
                runs.append(
                    run_headless(
                        config,
                        episode_seed,
                        symbol_ids,
                        int(steps),
                        out_root / f"seed_{episode_seed:04d}",
                        None,
                        fields_npz=bool(record_fields),
                        fields_every_steps=int(fields_every_steps),
                        invariant_streams=invariant_streams,
                        fabric_handshake=bool(fabric_handshake),
                        fabric_required_proof_accepts=int(fabric_required_proof_accepts),
                        fabric_required_trust_accepts=int(fabric_required_trust_accepts),
                        fabric_required_unique_proof_validators=int(fabric_required_unique_proof_validators),
                        fabric_required_unique_trust_validators=int(fabric_required_unique_trust_validators),
                        fabric_required_validator_ids=fabric_required_validator_ids,
                        fabric_enforce_required_validator_ids=bool(fabric_enforce_required_validator_ids),
                        fabric_reject_on_any_reject=bool(fabric_reject_on_any_reject),
                        fabric_retry_attempts=int(fabric_retry_attempts),
                        fabric_pending_timeout_ms=fabric_pending_timeout_ms,
                        fabric_transport=str(fabric_transport),
                        fabric_transport_host=str(fabric_transport_host),
                        fabric_transport_port=int(fabric_transport_port),
                        fabric_transport_connect=bool(fabric_transport_connect),
                        fabric_transport_keep_open=bool(fabric_transport_keep_open),
                        fabric_transport_backpressure_max_pending=fabric_transport_backpressure_max_pending,
                        fabric_transport_backpressure_policy=str(fabric_transport_backpressure_policy),
                        fabric_transport_backpressure_block_timeout_ms=int(
                            fabric_transport_backpressure_block_timeout_ms
                        ),
                        fabric_artifact_dir=fabric_artifact_dir,
                        fabric_inline_bridge=bool(fabric_inline_bridge),
                        fabric_replay_sample_stride=int(fabric_replay_sample_stride),
                        fabric_epoch_state_path=fabric_epoch_state_path,
                        fabric_epoch_replica_state_paths=fabric_epoch_replica_state_paths,
                        fabric_epoch_replica_read_quorum=fabric_epoch_replica_read_quorum,
                        fabric_epoch_replica_write_quorum=fabric_epoch_replica_write_quorum,
                        fabric_epoch_lock_timeout_ms=int(fabric_epoch_lock_timeout_ms),
                        fabric_epoch_lock_poll_ms=int(fabric_epoch_lock_poll_ms),
                        fabric_epoch_lock_stale_ms=fabric_epoch_lock_stale_ms,
                        fabric_epoch_consensus_required_total_accepts=int(
                            fabric_epoch_consensus_required_total_accepts
                        ),
                        fabric_epoch_consensus_timeout_ms=int(fabric_epoch_consensus_timeout_ms),
                        fabric_epoch_consensus_reject_on_any_reject=bool(
                            fabric_epoch_consensus_reject_on_any_reject
                        ),
                        fabric_epoch_consensus_channel=str(fabric_epoch_consensus_channel),
                        fabric_epoch_consensus_enabled=bool(fabric_epoch_consensus_enabled),
                        fabric_split_mode_channels=bool(fabric_split_mode_channels),
                        fabric_commit_retry_attempts=int(fabric_commit_retry_attempts),
                        fabric_delivery_required_receipts=int(fabric_delivery_required_receipts),
                        fabric_delivery_required_validator_ids=fabric_delivery_required_validator_ids,
                        fabric_delivery_enforce_required_validator_ids=bool(
                            fabric_delivery_enforce_required_validator_ids
                        ),
                        fabric_delivery_reject_on_any_reject=bool(fabric_delivery_reject_on_any_reject),
                        fabric_delivery_retry_interval_ms=int(fabric_delivery_retry_interval_ms),
                        fabric_delivery_max_attempts=int(fabric_delivery_max_attempts),
                        fabric_delivery_timeout_ms=int(fabric_delivery_timeout_ms),
                        fabric_delivery_ack_channel=str(fabric_delivery_ack_channel),
                        fabric_delivery_emit_ack=bool(fabric_delivery_emit_ack),
                        fabric_delivery_outbox_path=fabric_delivery_outbox_path,
                        fabric_delivery_outbox_max_entries=fabric_delivery_outbox_max_entries,
                        fabric_delivery_outbox_flush_limit=fabric_delivery_outbox_flush_limit,
                        fabric_delivery_outbox_drop_policy=str(fabric_delivery_outbox_drop_policy),
                    )
                )
        else:
            runs.append(
                run_headless(
                    config,
                    int(seed),
                    symbol_ids,
                    int(steps),
                    out_root / f"seed_{int(seed):04d}",
                    viz_transport,
                    viz_every_steps=int(viz_every_steps),
                    fields_npz=bool(record_fields),
                    fields_every_steps=int(fields_every_steps),
                    invariant_streams=invariant_streams,
                    fabric_handshake=bool(fabric_handshake),
                    fabric_required_proof_accepts=int(fabric_required_proof_accepts),
                    fabric_required_trust_accepts=int(fabric_required_trust_accepts),
                    fabric_required_unique_proof_validators=int(fabric_required_unique_proof_validators),
                    fabric_required_unique_trust_validators=int(fabric_required_unique_trust_validators),
                    fabric_required_validator_ids=fabric_required_validator_ids,
                    fabric_enforce_required_validator_ids=bool(fabric_enforce_required_validator_ids),
                    fabric_reject_on_any_reject=bool(fabric_reject_on_any_reject),
                    fabric_retry_attempts=int(fabric_retry_attempts),
                    fabric_pending_timeout_ms=fabric_pending_timeout_ms,
                    fabric_transport=str(fabric_transport),
                    fabric_transport_host=str(fabric_transport_host),
                    fabric_transport_port=int(fabric_transport_port),
                    fabric_transport_connect=bool(fabric_transport_connect),
                    fabric_transport_keep_open=bool(fabric_transport_keep_open),
                    fabric_transport_backpressure_max_pending=fabric_transport_backpressure_max_pending,
                    fabric_transport_backpressure_policy=str(fabric_transport_backpressure_policy),
                    fabric_transport_backpressure_block_timeout_ms=int(fabric_transport_backpressure_block_timeout_ms),
                    fabric_artifact_dir=fabric_artifact_dir,
                    fabric_inline_bridge=bool(fabric_inline_bridge),
                    fabric_replay_sample_stride=int(fabric_replay_sample_stride),
                    fabric_epoch_state_path=fabric_epoch_state_path,
                    fabric_epoch_replica_state_paths=fabric_epoch_replica_state_paths,
                    fabric_epoch_replica_read_quorum=fabric_epoch_replica_read_quorum,
                    fabric_epoch_replica_write_quorum=fabric_epoch_replica_write_quorum,
                    fabric_epoch_lock_timeout_ms=int(fabric_epoch_lock_timeout_ms),
                    fabric_epoch_lock_poll_ms=int(fabric_epoch_lock_poll_ms),
                    fabric_epoch_lock_stale_ms=fabric_epoch_lock_stale_ms,
                    fabric_epoch_consensus_required_total_accepts=int(
                        fabric_epoch_consensus_required_total_accepts
                    ),
                    fabric_epoch_consensus_timeout_ms=int(fabric_epoch_consensus_timeout_ms),
                    fabric_epoch_consensus_reject_on_any_reject=bool(fabric_epoch_consensus_reject_on_any_reject),
                    fabric_epoch_consensus_channel=str(fabric_epoch_consensus_channel),
                    fabric_epoch_consensus_enabled=bool(fabric_epoch_consensus_enabled),
                    fabric_split_mode_channels=bool(fabric_split_mode_channels),
                    fabric_commit_retry_attempts=int(fabric_commit_retry_attempts),
                    fabric_delivery_required_receipts=int(fabric_delivery_required_receipts),
                    fabric_delivery_required_validator_ids=fabric_delivery_required_validator_ids,
                    fabric_delivery_enforce_required_validator_ids=bool(fabric_delivery_enforce_required_validator_ids),
                    fabric_delivery_reject_on_any_reject=bool(fabric_delivery_reject_on_any_reject),
                    fabric_delivery_retry_interval_ms=int(fabric_delivery_retry_interval_ms),
                    fabric_delivery_max_attempts=int(fabric_delivery_max_attempts),
                    fabric_delivery_timeout_ms=int(fabric_delivery_timeout_ms),
                    fabric_delivery_ack_channel=str(fabric_delivery_ack_channel),
                    fabric_delivery_emit_ack=bool(fabric_delivery_emit_ack),
                    fabric_delivery_outbox_path=fabric_delivery_outbox_path,
                    fabric_delivery_outbox_max_entries=fabric_delivery_outbox_max_entries,
                    fabric_delivery_outbox_flush_limit=fabric_delivery_outbox_flush_limit,
                    fabric_delivery_outbox_drop_policy=str(fabric_delivery_outbox_drop_policy),
                )
            )
    finally:
        if viz_transport is not None:
            viz_transport.close()

    catalog = {"schema_versions": get_schema_versions(), "runs": runs}
    (out_root / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"[OK] {len(runs)} run(s) complete. Catalog: {out_root / 'catalog.json'}")
    return 0


__all__ = ["main", "run_headless"]
