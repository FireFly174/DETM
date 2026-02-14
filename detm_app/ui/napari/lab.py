#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Napari-first launcher for DETM validation runs.

This helper starts a headless producer (`detm_app.runner.headless`) with TCP viz streaming
and opens the canonical napari read-only subscriber against the same endpoint.

Use `--` to forward any extra CLI args to producer:
  python main.py napari -- --seed 7 --steps 400 --fabric-handshake
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from typing import Sequence


def _normalize_forwarded_args(values: Sequence[str]) -> list[str]:
    forwarded = [str(v) for v in list(values)]
    if forwarded and forwarded[0] == "--":
        return forwarded[1:]
    return forwarded


def _build_producer_command(*, host: str, port: int, producer_args: Sequence[str]) -> list[str]:
    bootstrap = "from detm_app.runner.headless import main; import sys; raise SystemExit(main(sys.argv[1:]))"
    cmd = [
        sys.executable,
        "-c",
        bootstrap,
        "--viz",
        "--viz-transport",
        "tcp",
        "--viz-host",
        str(host),
        "--viz-port",
        str(int(port)),
        "--viz-keep-open",
    ]
    cmd.extend(_normalize_forwarded_args(producer_args))
    return cmd


def _wait_for_tcp_endpoint(*, host: str, port: int, timeout_s: float, producer: subprocess.Popen[str]) -> None:
    deadline = time.perf_counter() + max(0.1, float(timeout_s))
    last_error: Exception | None = None
    exit_code: int | None = None
    while time.perf_counter() < deadline:
        exit_code = producer.poll()
        if exit_code is not None and int(exit_code) != 0:
            raise RuntimeError(f"Producer exited early with code {int(exit_code)} before viz endpoint became ready.")
        try:
            sock = socket.create_connection((str(host), int(port)), timeout=0.25)
            sock.close()
            return
        except Exception as exc:  # pragma: no cover - timeout branch timing-sensitive
            last_error = exc
            time.sleep(0.1)
    if last_error is None:
        raise RuntimeError("Viz TCP endpoint did not become ready in time.")
    if exit_code is not None:
        raise RuntimeError(
            f"Producer finished with code {int(exit_code)}, but viz endpoint {host}:{int(port)} is not reachable: {last_error}"
        )
    raise RuntimeError(f"Viz TCP endpoint did not become ready in time: {last_error}")


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="main.py napari",
        description="Start headless producer + napari subscriber (napari-first validation flow).",
    )
    ap.add_argument("--host", default="127.0.0.1", help="Viz host for producer/subscriber")
    ap.add_argument("--port", type=int, default=5588, help="Fixed viz TCP port (>0)")
    ap.add_argument("--poll-ms", type=int, default=40, help="Napari subscriber polling interval in ms")
    ap.add_argument("--timeout-s", type=float, default=2.0, help="Napari subscriber TCP timeout in seconds")
    ap.add_argument(
        "--producer-wait-timeout-s",
        type=float,
        default=15.0,
        help="Max wait for producer TCP endpoint before opening viewer",
    )
    ap.add_argument("--autoscale", action="store_true", help="Enable napari autoscale")
    ap.add_argument(
        "--title",
        default="DETM napari lab (producer + subscriber)",
        help="Napari window title",
    )
    ap.add_argument(
        "--viewer-only",
        action="store_true",
        help="Do not start producer; connect viewer to an already running endpoint",
    )
    ap.add_argument(
        "--interactive",
        action="store_true",
        help="Run in-process interactive controls (Tk functionality migrated to napari)",
    )
    ap.add_argument(
        "--preset",
        default=None,
        help="Config preset (forwarded to producer in normal mode; used directly in --interactive mode)",
    )
    ap.add_argument(
        "--config",
        default=None,
        help="Config path (forwarded to producer in normal mode; used directly in --interactive mode)",
    )
    ap.add_argument(
        "--startup-only",
        action="store_true",
        help="Run startup profiling and exit before entering napari event loop",
    )
    ap.add_argument(
        "--phase-profile-json",
        default=None,
        help="Optional path to write napari startup phase timings as JSON",
    )
    ap.add_argument(
        "producer_args",
        nargs=argparse.REMAINDER,
        help="Extra args forwarded to detm_app.runner.headless (use `--` separator)",
    )
    return ap


def _normalize_profile_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(float(value), 6)
    return value


def _emit_phase_profile(
    *,
    profile: dict[str, Any],
    json_path: str | None,
) -> None:
    normalized = {str(key): _normalize_profile_value(value) for key, value in dict(profile).items()}
    print("[napari-phase-profile] " + json.dumps(normalized, ensure_ascii=False, sort_keys=True))
    if json_path is None:
        return
    out_path = Path(str(json_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if bool(args.interactive):
        if bool(args.viewer_only):
            raise SystemExit("--interactive cannot be combined with --viewer-only")
        if bool(args.startup_only):
            raise SystemExit("--interactive cannot be combined with --startup-only")
        from detm_app.ui.napari.interactive import run_napari_interactive

        try:
            return int(
                run_napari_interactive(
                    preset=str(args.preset or "default"),
                    override_path=args.config,
                    autoscale=bool(args.autoscale),
                    title=str(args.title),
                )
            )
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc

    host = str(args.host).strip() or "127.0.0.1"
    port = int(args.port)
    if port <= 0:
        raise SystemExit("--port must be > 0 for napari lab mode")

    phase_profile: dict[str, Any] = {
        "host": str(host),
        "port": int(port),
        "viewer_only": bool(args.viewer_only),
        "startup_only": bool(args.startup_only),
        "producer_wait_s": None,
        "napari_qt_import_s": None,
        "viewer_create_s": None,
        "first_frame_s": None,
        "first_frame_status": "not_started",
    }
    producer: subprocess.Popen[str] | None = None
    producer_args = list(args.producer_args)
    if args.preset is not None and str(args.preset).strip():
        producer_args = ["--preset", str(args.preset).strip(), *producer_args]
    if args.config is not None and str(args.config).strip():
        producer_args = ["--config", str(args.config).strip(), *producer_args]
    try:
        if not bool(args.viewer_only):
            producer_cmd = _build_producer_command(host=host, port=port, producer_args=producer_args)
            producer = subprocess.Popen(producer_cmd)
            producer_wait_started = time.perf_counter()
            _wait_for_tcp_endpoint(
                host=host,
                port=port,
                timeout_s=float(args.producer_wait_timeout_s),
                producer=producer,
            )
            phase_profile["producer_wait_s"] = float(time.perf_counter() - producer_wait_started)
        else:
            phase_profile["first_frame_status"] = "viewer_only"

        from detm_app.ui.napari.subscriber import run_napari_subscriber

        try:
            rc = run_napari_subscriber(
                host=host,
                port=port,
                poll_ms=int(args.poll_ms),
                timeout_s=float(args.timeout_s),
                autoscale=bool(args.autoscale),
                title=str(args.title),
                startup_profile=phase_profile,
                startup_only=bool(args.startup_only),
            )
            _emit_phase_profile(profile=phase_profile, json_path=args.phase_profile_json)
            return int(rc)
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
    finally:
        if producer is not None and producer.poll() is None:
            try:
                producer.terminate()
                producer.wait(timeout=5.0)
            except Exception:  # pragma: no cover - defensive shutdown
                try:
                    producer.kill()
                except Exception:
                    pass


__all__ = [
    "main",
    "_build_producer_command",
    "_normalize_forwarded_args",
]
