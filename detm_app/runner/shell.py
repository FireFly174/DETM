#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Composable shell orchestration for DETM entrypoints.

This module exposes explicit role selection:
- controller: who manages runs (`local|batch|external`)
- runner: who executes runtime (`headless`)
- viewer: who visualizes (`none|napari`)

It is intended as a stable shell contract for future external orchestrators,
including LLM-driven controllers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from detm_app.runner.viewer_registry import (
    build_napari_viewer_options,
    resolve_viewer_adapter,
    run_napari_viewer,
)


def _normalize_forwarded_args(values: Sequence[str]) -> list[str]:
    forwarded = [str(v) for v in list(values)]
    if forwarded and forwarded[0] == "--":
        return forwarded[1:]
    return forwarded


def _compatibility_error(*, controller: str, runner: str, viewer: str) -> str | None:
    controller = str(controller).strip().lower()
    runner = str(runner).strip().lower()
    viewer = str(viewer).strip().lower()

    if runner != "headless":
        return f"unsupported runner: {runner!r}"
    if viewer not in {"none", ""} and resolve_viewer_adapter(viewer) is None:
        return f"unsupported viewer: {viewer!r}"

    if controller == "batch" and viewer != "none":
        return "controller=batch currently supports viewer=none only"

    return None


def build_shell_contract(
    *,
    controller: str,
    runner: str,
    viewer: str,
    forwarded_args: Sequence[str],
    napari_options: dict[str, Any],
) -> dict[str, Any]:
    error = _compatibility_error(controller=controller, runner=runner, viewer=viewer)
    out: dict[str, Any] = {
        "roles": {
            "controller": str(controller),
            "runner": str(runner),
            "viewer": str(viewer),
        },
        "compatibility": {
            "supported": bool(error is None),
            "error": error,
        },
        "forwarded_args": [str(v) for v in list(forwarded_args)],
    }
    adapter = resolve_viewer_adapter(str(viewer))

    if str(controller) == "external":
        out["execution"] = {
            "mode": "contract_only",
            "producer_entrypoint": "detm_app.runner.headless.main",
            "viewer_entrypoint": (adapter.entrypoint if adapter is not None else None),
            "napari_options": dict(napari_options) if adapter is not None else {},
        }
        return out

    if error is not None:
        out["execution"] = {"mode": "invalid"}
        return out

    if adapter is not None:
        out["execution"] = {
            "mode": "direct",
            "entrypoint": adapter.entrypoint,
            "napari_options": dict(napari_options),
        }
        return out

    out["execution"] = {
        "mode": "direct",
        "entrypoint": "detm_app.runner.headless.main",
    }
    return out


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="main.py shell",
        description="Select controller/runner/viewer roles for DETM shell composition.",
    )
    ap.add_argument("--controller", choices=["local", "batch", "external"], default="local")
    ap.add_argument("--runner", choices=["headless"], default="headless")
    ap.add_argument("--viewer", choices=["none", "napari"], default="none")
    ap.add_argument("--dry-run", action="store_true", help="Print resolved shell contract and exit")
    ap.add_argument("--emit-contract", default=None, help="Optional path to write resolved contract JSON")

    # napari viewer options (applied only when viewer=napari)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5588)
    ap.add_argument("--poll-ms", type=int, default=40)
    ap.add_argument("--timeout-s", type=float, default=2.0)
    ap.add_argument("--producer-wait-timeout-s", type=float, default=15.0)
    ap.add_argument("--autoscale", action="store_true")
    ap.add_argument("--title", default="DETM napari lab (producer + subscriber)")
    ap.add_argument("--viewer-only", action="store_true")

    ap.add_argument(
        "forwarded_args",
        nargs=argparse.REMAINDER,
        help="Forwarded args for selected shell. Use `--` separator.",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    forwarded = _normalize_forwarded_args(args.forwarded_args)
    contract = build_shell_contract(
        controller=str(args.controller),
        runner=str(args.runner),
        viewer=str(args.viewer),
        forwarded_args=forwarded,
        napari_options=build_napari_viewer_options(args),
    )

    if args.emit_contract is not None:
        path = Path(str(args.emit_contract))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")

    if bool(args.dry_run) or str(args.controller) == "external":
        print(json.dumps(contract, indent=2, ensure_ascii=False))
        return 0

    error = str(dict(contract.get("compatibility", {})).get("error") or "").strip()
    if error:
        raise SystemExit(error)

    viewer = str(args.viewer)

    if resolve_viewer_adapter(viewer) is not None:
        return int(run_napari_viewer(args, forwarded_args=forwarded))

    # headless + viewer=none for local/batch controllers
    from detm_app.runner.headless import main as cli_main

    return int(cli_main(forwarded))


__all__ = ["build_shell_contract", "main"]
