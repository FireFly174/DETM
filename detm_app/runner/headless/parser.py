"""CLI parser factory for DETM headless runner."""

from __future__ import annotations

import argparse

from detm.presets import preset_names
from detm_app.runner.headless.parser_fabric import add_fabric_arguments


def build_headless_parser() -> argparse.ArgumentParser:
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

    ap.add_argument("--steps", type=int, default=None, help="Tick budget (see --steps-mode)")
    ap.add_argument(
        "--steps-mode",
        type=str,
        default=None,
        choices=["total", "per_symbol"],
        help="How to apply --steps: total budget or per symbol",
    )
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

    add_fabric_arguments(ap)

    ap.add_argument("--list-symbols", action="store_true", help="Print known symbol IDs and exit")
    return ap


__all__ = ["build_headless_parser"]
