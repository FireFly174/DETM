#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""DETM headless CLI runner (package entrypoint).

Examples:
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

import json
from pathlib import Path
from typing import Any

from detm_app.config.app_settings import build_runtime_config, load_merged_payload
from detm_app.runtime.session import DetmSession
from detm.runtime.config import DETMConfig
from detm.runtime.schemas import get_schema_versions
from detm.runtime.symbols import list_symbols
from detm_app.runner.headless.executor import execute_headless_steps
from detm_app.runner.headless.request import RunHeadlessRequest, build_run_headless_request
from detm_app.runner.headless.subscribers import attach_headless_subscribers
from detm_app.runner.headless.options import HeadlessMainOptions, resolve_headless_main_options
from detm_app.runner.headless.parser import build_headless_parser
from detm_app.runner.headless.helpers import runner_defaults as load_runner_defaults
from detm_app.transport import open_viz_transport


def run_headless(
    config: DETMConfig,
    seed: int,
    symbol_ids: list[str],
    steps: int,
    out_dir: Path,
    viz_transport,
    *,
    steps_mode: str = "per_symbol",
    viz_every_steps: int = 1,
    fields_npz: bool = False,
    fields_every_steps: int = 1,
    invariant_streams: list[str] | None = None,
    **fabric_kwargs: Any,
) -> dict:
    request = build_run_headless_request(
        config=config,
        seed=seed,
        symbol_ids=symbol_ids,
        steps=steps,
        out_dir=out_dir,
        viz_transport=viz_transport,
        steps_mode=steps_mode,
        viz_every_steps=viz_every_steps,
        fields_npz=fields_npz,
        fields_every_steps=fields_every_steps,
        invariant_streams=invariant_streams,
        fabric_kwargs=fabric_kwargs,
    )
    return run_headless_request(request)


def run_headless_request(request: RunHeadlessRequest) -> dict:
    request.out_dir.mkdir(parents=True, exist_ok=True)
    level_name = str(request.config.level_policy.active_level or "L0")

    session = DetmSession.create(request.config, int(request.seed))
    attach_headless_subscribers(
        session=session,
        config=request.config,
        seed=int(request.seed),
        out_dir=request.out_dir,
        level_name=level_name,
        invariant_streams=None if request.invariant_streams is None else list(request.invariant_streams),
        viz_transport=request.viz_transport,
        viz_every_steps=int(request.viz_every_steps),
        fields_npz=bool(request.fields_npz),
        fields_every_steps=int(request.fields_every_steps),
        fabric_kwargs=request.fabric_kwargs,
    )

    execute_headless_steps(
        session=session,
        symbol_ids=list(request.symbol_ids),
        steps=int(request.steps),
        steps_mode=str(request.steps_mode),
    )

    digest = session.digest()
    session.close()
    return {"seed": int(request.seed), "digest": digest.as_dict(), "dir": str(request.out_dir)}


def _build_run_headless_kwargs(options: HeadlessMainOptions) -> dict[str, Any]:
    return {
        "steps_mode": str(options.steps_mode),
        "fields_npz": bool(options.record_fields),
        "fields_every_steps": int(options.fields_every_steps),
        "invariant_streams": options.invariant_streams,
        "fabric_handshake": bool(options.fabric_handshake),
        "fabric_required_proof_accepts": int(options.fabric_required_proof_accepts),
        "fabric_required_trust_accepts": int(options.fabric_required_trust_accepts),
        "fabric_required_unique_proof_validators": int(options.fabric_required_unique_proof_validators),
        "fabric_required_unique_trust_validators": int(options.fabric_required_unique_trust_validators),
        "fabric_required_validator_ids": options.fabric_required_validator_ids,
        "fabric_handshake_profile": str(options.fabric_handshake_profile),
        "fabric_enforce_required_validator_ids": bool(options.fabric_enforce_required_validator_ids),
        "fabric_enforce_active_validator_membership": bool(options.fabric_enforce_active_validator_membership),
        "fabric_enforce_ack_sender_validator_match": bool(options.fabric_enforce_ack_sender_validator_match),
        "fabric_enforce_ack_auth_key_id_binding": bool(options.fabric_enforce_ack_auth_key_id_binding),
        "fabric_validator_auth_key_ids": options.fabric_validator_auth_key_ids,
        "fabric_enforce_ack_transport_identity_binding": bool(options.fabric_enforce_ack_transport_identity_binding),
        "fabric_validator_transport_identities": options.fabric_validator_transport_identities,
        "fabric_reject_on_any_reject": bool(options.fabric_reject_on_any_reject),
        "fabric_retry_attempts": int(options.fabric_retry_attempts),
        "fabric_pending_timeout_ms": options.fabric_pending_timeout_ms,
        "fabric_transport": str(options.fabric_transport),
        "fabric_transport_host": str(options.fabric_transport_host),
        "fabric_transport_port": int(options.fabric_transport_port),
        "fabric_transport_connect": bool(options.fabric_transport_connect),
        "fabric_transport_keep_open": bool(options.fabric_transport_keep_open),
        "fabric_transport_backpressure_max_pending": options.fabric_transport_backpressure_max_pending,
        "fabric_transport_backpressure_policy": str(options.fabric_transport_backpressure_policy),
        "fabric_transport_backpressure_block_timeout_ms": int(options.fabric_transport_backpressure_block_timeout_ms),
        "fabric_transport_dedup_ingress_enabled": bool(options.fabric_transport_dedup_ingress_enabled),
        "fabric_transport_dedup_ttl_ms": int(options.fabric_transport_dedup_ttl_ms),
        "fabric_transport_dedup_max_entries": int(options.fabric_transport_dedup_max_entries),
        "fabric_transport_auth_enabled": bool(options.fabric_transport_auth_enabled),
        "fabric_transport_auth_key": options.fabric_transport_auth_key,
        "fabric_transport_auth_key_id": options.fabric_transport_auth_key_id,
        "fabric_transport_tls_enabled": bool(options.fabric_transport_tls_enabled),
        "fabric_transport_tls_server_hostname": options.fabric_transport_tls_server_hostname,
        "fabric_transport_tls_ca_file": options.fabric_transport_tls_ca_file,
        "fabric_transport_tls_cert_file": options.fabric_transport_tls_cert_file,
        "fabric_transport_tls_key_file": options.fabric_transport_tls_key_file,
        "fabric_transport_tls_require_client_cert": bool(options.fabric_transport_tls_require_client_cert),
        "fabric_transport_tls_client_ca_file": options.fabric_transport_tls_client_ca_file,
        "fabric_transport_tls_insecure_skip_verify": bool(options.fabric_transport_tls_insecure_skip_verify),
        "fabric_transport_tls_identity_source": str(options.fabric_transport_tls_identity_source),
        "fabric_transport_tls_identity_fallback_to_fingerprint": bool(
            options.fabric_transport_tls_identity_fallback_to_fingerprint
        ),
        "fabric_artifact_dir": options.fabric_artifact_dir,
        "fabric_inline_bridge": bool(options.fabric_inline_bridge),
        "fabric_replay_sample_stride": int(options.fabric_replay_sample_stride),
        "fabric_replay_policy_tier": str(options.fabric_replay_policy_tier),
        "fabric_replay_strict_window_size": int(options.fabric_replay_strict_window_size),
        "fabric_validator_coordination_state_path": options.fabric_validator_coordination_state_path,
        "fabric_validator_coordination_replica_state_paths": options.fabric_validator_coordination_replica_state_paths,
        "fabric_validator_coordination_replica_read_quorum": options.fabric_validator_coordination_replica_read_quorum,
        "fabric_validator_coordination_replica_write_quorum": options.fabric_validator_coordination_replica_write_quorum,
        "fabric_epoch_state_path": options.fabric_epoch_state_path,
        "fabric_epoch_replica_state_paths": options.fabric_epoch_replica_state_paths,
        "fabric_epoch_replica_read_quorum": options.fabric_epoch_replica_read_quorum,
        "fabric_epoch_replica_write_quorum": options.fabric_epoch_replica_write_quorum,
        "fabric_epoch_lock_timeout_ms": int(options.fabric_epoch_lock_timeout_ms),
        "fabric_epoch_lock_poll_ms": int(options.fabric_epoch_lock_poll_ms),
        "fabric_epoch_lock_stale_ms": options.fabric_epoch_lock_stale_ms,
        "fabric_epoch_consensus_required_total_accepts": int(options.fabric_epoch_consensus_required_total_accepts),
        "fabric_epoch_consensus_timeout_ms": int(options.fabric_epoch_consensus_timeout_ms),
        "fabric_epoch_consensus_max_attempts": int(options.fabric_epoch_consensus_max_attempts),
        "fabric_epoch_consensus_reject_on_any_reject": bool(options.fabric_epoch_consensus_reject_on_any_reject),
        "fabric_epoch_consensus_channel": str(options.fabric_epoch_consensus_channel),
        "fabric_epoch_consensus_enabled": bool(options.fabric_epoch_consensus_enabled),
        "fabric_split_mode_channels": bool(options.fabric_split_mode_channels),
        "fabric_commit_retry_attempts": int(options.fabric_commit_retry_attempts),
        "fabric_delivery_required_receipts": int(options.fabric_delivery_required_receipts),
        "fabric_delivery_guarantee_mode": str(options.fabric_delivery_guarantee_mode),
        "fabric_delivery_required_validator_ids": options.fabric_delivery_required_validator_ids,
        "fabric_delivery_enforce_required_validator_ids": bool(options.fabric_delivery_enforce_required_validator_ids),
        "fabric_delivery_reject_on_any_reject": bool(options.fabric_delivery_reject_on_any_reject),
        "fabric_delivery_retry_interval_ms": int(options.fabric_delivery_retry_interval_ms),
        "fabric_delivery_max_attempts": int(options.fabric_delivery_max_attempts),
        "fabric_delivery_timeout_ms": int(options.fabric_delivery_timeout_ms),
        "fabric_delivery_tracking_state_path": options.fabric_delivery_tracking_state_path,
        "fabric_delivery_ack_channel": str(options.fabric_delivery_ack_channel),
        "fabric_delivery_emit_ack": bool(options.fabric_delivery_emit_ack),
        "fabric_delivery_outbox_path": options.fabric_delivery_outbox_path,
        "fabric_delivery_outbox_max_entries": options.fabric_delivery_outbox_max_entries,
        "fabric_delivery_outbox_flush_limit": options.fabric_delivery_outbox_flush_limit,
        "fabric_delivery_outbox_drop_policy": str(options.fabric_delivery_outbox_drop_policy),
    }


def main(argv: list[str] | None = None) -> int:
    ap = build_headless_parser()
    args = ap.parse_args(argv)

    if args.list_symbols:
        print("\n".join(list_symbols()))
        return 0

    payload = load_merged_payload(preset=str(args.preset), override_path=args.config)
    config = build_runtime_config(payload)
    runner_defaults = load_runner_defaults(payload)

    runtime_overrides: dict[str, Any] = {}
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

    options = resolve_headless_main_options(args=args, runner_defaults=runner_defaults)

    if options.viz_enabled and args.batch is not None:
        raise SystemExit("--viz is supported only for a single run (omit --batch)")

    viz_transport = None
    if options.viz_enabled and str(options.viz_transport_name).lower() != "none":
        viz_transport = open_viz_transport(
            enabled=True,
            transport=str(options.viz_transport_name),
            host=str(options.viz_host),
            port=int(options.viz_port),
            connect=bool(options.viz_connect),
            keep_open=bool(options.viz_keep_open),
        )

    run_kwargs = _build_run_headless_kwargs(options)
    runs: list[dict] = []
    try:
        if args.batch is not None:
            for i in range(int(args.batch)):
                episode_seed = int(options.seed0) + i
                runs.append(
                    run_headless(
                        config,
                        episode_seed,
                        options.symbol_ids,
                        int(options.steps),
                        options.out_root / f"seed_{episode_seed:04d}",
                        None,
                        **run_kwargs,
                    )
                )
        else:
            runs.append(
                run_headless(
                    config,
                    int(options.seed),
                    options.symbol_ids,
                    int(options.steps),
                    options.out_root / f"seed_{int(options.seed):04d}",
                    viz_transport,
                    viz_every_steps=int(options.viz_every_steps),
                    **run_kwargs,
                )
            )
    finally:
        if viz_transport is not None:
            viz_transport.close()

    catalog = {"schema_versions": get_schema_versions(), "runs": runs}
    (options.out_root / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"[OK] {len(runs)} run(s) complete. Catalog: {options.out_root / 'catalog.json'}")
    return 0


__all__ = ["main", "run_headless", "run_headless_request"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
