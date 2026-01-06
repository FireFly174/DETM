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
from detm.presets import preset_names
from detm.runtime.config import DETMConfig
from detm.runtime.schemas import get_schema_versions
from detm.runtime.symbols import list_symbols, make_symbol
from detm.run.coarsening import InvariantCoarsener, parse_invariant_streams
from detm.run.session import DetmSession
from detm.run.subscribers import (
    ArtifactWriter,
    FieldHistoryRecorder,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    TraceRecorder,
    VizStreamer,
)
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
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    session = DetmSession.create(config, seed)
    if invariant_streams:
        InvariantCoarsener.attach(session.bus, parse_invariant_streams(invariant_streams))
        InvariantTickJsonlWriter.attach(session.bus, out_dir / "invariants.jsonl")
    TraceRecorder.attach(session.bus, out_dir)
    ArtifactWriter.attach(session.bus, out_dir)
    JsonlTraceWriter.attach(session.bus, out_dir / "trace.jsonl")
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
