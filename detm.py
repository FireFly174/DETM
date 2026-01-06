#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""DETM headless CLI runner.

Examples:
  python detm.py
  python detm.py --seed 1 --steps 4 --symbols pulse ring
  python detm.py --batch 10 --seed0 0 --out runs/out/my_batch
  python detm.py --viz   # start viz daemon and stream state
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

from detm.presets import load_preset_config, preset_names
from detm.runtime.config import DETMConfig
from detm.runtime.symbols import list_symbols, make_symbol
from detm.run.session import DetmSession
from detm.run.subscribers import ArtifactWriter, FieldHistoryRecorder, JsonlTraceWriter, TraceRecorder, VizStreamer
from detm.viz.transport import open_viz_transport


def _load_config(args) -> DETMConfig:
    if args.preset is not None:
        config = load_preset_config(args.preset)
    else:
        config = DETMConfig()

    if args.config is not None:
        payload = json.loads(Path(args.config).read_text(encoding="utf-8"))
        config = DETMConfig.from_dict({**config.to_dict(), **payload})

    overrides = {}
    if args.backend is not None:
        overrides["backend"] = args.backend
    if args.device is not None:
        overrides["device"] = args.device
    if args.width is not None:
        overrides["width"] = args.width
    if args.height is not None:
        overrides["height"] = args.height
    if overrides:
        config = DETMConfig.from_dict({**config.to_dict(), **overrides})
    return config


def _resolve_symbols(symbols: list[str] | None) -> list[str]:
    if symbols is None:
        return list_symbols()
    out = []
    known = set(list_symbols())
    for sid in symbols:
        if sid in known:
            out.append(sid)
        else:
            raise SystemExit(f"Unknown symbol_id: {sid}. Known: {sorted(known)}")
    return out


def _default_out_dir(out: str | None) -> Path:
    if out is not None:
        return Path(out)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("runs/out") / f"run_{stamp}"


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
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    session = DetmSession.create(config, seed)
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preset", default="default", choices=sorted(set(preset_names())), help="Packaged preset name")
    ap.add_argument("--config", default=None, help="Path to config override JSON")
    ap.add_argument("--backend", default=None, choices=["torch", "numpy"], help="Override backend")
    ap.add_argument("--device", default=None, help="Override device (e.g. cuda/cpu)")
    ap.add_argument("--width", type=int, default=None, help="Override lattice width")
    ap.add_argument("--height", type=int, default=None, help="Override lattice height")

    ap.add_argument("--seed", type=int, default=1, help="Seed")
    ap.add_argument("--seed0", type=int, default=0, help="Seed start for --batch")
    ap.add_argument("--batch", type=int, default=None, help="Run N episodes with seeds seed0..seed0+N-1")

    ap.add_argument("--steps", type=int, default=4, help="Ticks per influence")
    ap.add_argument("--symbols", nargs="*", default=None, help="Symbol IDs to apply (default: all)")
    ap.add_argument("--out", default=None, help="Output directory root (default: runs/out/run_<timestamp>)")

    ap.add_argument(
        "--viz",
        action="store_true",
        help="Start a local viz daemon and stream state updates (headless runner still writes artifacts)",
    )
    ap.add_argument(
        "--viz-transport",
        default="tcp",
        choices=["tcp", "none"],
        help="Visualization transport (default: tcp)",
    )
    ap.add_argument(
        "--viz-connect",
        action="store_true",
        help="Connect to an existing viz daemon instead of starting a new one (requires --viz-host/--viz-port)",
    )
    ap.add_argument("--viz-host", default="127.0.0.1", help="Viz daemon host (default: localhost)")
    ap.add_argument("--viz-port", type=int, default=0, help="Viz daemon port (0 = auto when starting locally)")
    ap.add_argument(
        "--viz-keep-open",
        action="store_true",
        help="Do not terminate the locally started viz daemon after the run finishes",
    )
    ap.add_argument("--viz-every-steps", type=int, default=1, help="Send viz updates every N step_count increments")
    ap.add_argument("--record-fields", action="store_true", help="Write `fields_hist.npz` with E/S/tau (+J approx) history")
    ap.add_argument("--fields-every-steps", type=int, default=1, help="Record fields every N step_count increments")

    ap.add_argument("--list-symbols", action="store_true", help="Print known symbol IDs and exit")
    args = ap.parse_args(argv)

    if args.list_symbols:
        print("\n".join(list_symbols()))
        return 0

    config = _load_config(args)
    symbol_ids = _resolve_symbols(args.symbols)

    if args.viz and args.batch is not None:
        raise SystemExit("--viz is supported only for a single run (omit --batch)")

    viz_transport = None
    if args.viz and str(args.viz_transport).lower() != "none":
        viz_transport = open_viz_transport(
            enabled=True,
            transport=str(args.viz_transport),
            host=str(args.viz_host),
            port=int(args.viz_port),
            connect=bool(args.viz_connect),
            keep_open=bool(args.viz_keep_open),
        )

    out_root = _default_out_dir(args.out)
    runs = []
    try:
        if args.batch is not None:
            for i in range(int(args.batch)):
                seed = int(args.seed0) + i
            runs.append(
                run_headless(
                    config,
                    seed,
                    symbol_ids,
                    int(args.steps),
                    out_root / f"seed_{seed:04d}",
                    None,
                )
            )
        else:
            seed = int(args.seed)
            runs.append(
                run_headless(
                    config,
                    seed,
                    symbol_ids,
                    int(args.steps),
                    out_root / f"seed_{seed:04d}",
                    viz_transport,
                    viz_every_steps=int(args.viz_every_steps),
                    fields_npz=bool(args.record_fields),
                    fields_every_steps=int(args.fields_every_steps),
                )
            )
    finally:
        if viz_transport is not None:
            viz_transport.close()

    from detm.runtime.schemas import get_schema_versions

    catalog = {"schema_versions": get_schema_versions(), "runs": runs}
    (out_root / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"[OK] {len(runs)} run(s) complete. Catalog: {out_root / 'catalog.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
