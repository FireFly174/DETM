"""Option resolution helpers for headless CLI main()."""

from __future__ import annotations

from typing import Any

from detm_app.runner.headless.helpers import as_list, default_out_dir, normalize_steps_mode, resolve_symbols
from detm_app.runner.headless.options_fabric import resolve_headless_fabric_options
from detm_app.runner.headless.options_model import HeadlessMainOptions


def resolve_headless_main_options(*, args: Any, runner_defaults: dict[str, Any]) -> HeadlessMainOptions:
    seed0 = int(args.seed0) if args.seed0 is not None else int(runner_defaults.get("seed0", 0))
    seed = int(args.seed) if args.seed is not None else int(runner_defaults.get("seed", 1))
    steps = int(args.steps) if args.steps is not None else int(runner_defaults.get("steps", 4))
    steps_mode = normalize_steps_mode(
        args.steps_mode if args.steps_mode is not None else runner_defaults.get("steps_mode"),
        default="total",
    )
    out_root = default_out_dir(args.out if args.out is not None else runner_defaults.get("out"))

    symbols_cfg = as_list(runner_defaults.get("symbols"))
    symbol_ids = resolve_symbols(args.symbols if args.symbols is not None else symbols_cfg)

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
        invariant_streams = as_list(inv)

    fabric_values = resolve_headless_fabric_options(args=args, runner_defaults=runner_defaults)
    return HeadlessMainOptions(
        seed0=seed0,
        seed=seed,
        steps=steps,
        steps_mode=steps_mode,
        out_root=out_root,
        symbol_ids=symbol_ids,
        viz_enabled=bool(viz_enabled),
        viz_transport_name=viz_transport_name,
        viz_host=viz_host,
        viz_port=viz_port,
        viz_connect=bool(viz_connect),
        viz_keep_open=bool(viz_keep_open),
        viz_every_steps=viz_every_steps,
        record_fields=bool(record_fields),
        fields_every_steps=fields_every_steps,
        invariant_streams=invariant_streams,
        **fabric_values,
    )


__all__ = ["HeadlessMainOptions", "resolve_headless_main_options"]
