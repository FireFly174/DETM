from __future__ import annotations

import time
from pathlib import Path

from detm.runtime.config import DETMConfig
from detm_app.runner.batch_service import (
    BatchRunRequest,
    parse_batch_symbols_csv,
    start_batch_run,
)


def test_parse_batch_symbols_csv_defaults_to_available_symbols() -> None:
    symbols = ["pulse", "ring"]
    assert parse_batch_symbols_csv("", available_symbols=symbols) == symbols
    assert parse_batch_symbols_csv("   ", available_symbols=symbols) == symbols


def test_parse_batch_symbols_csv_validates_unknown_symbol() -> None:
    try:
        parse_batch_symbols_csv("pulse,unknown", available_symbols=["pulse", "ring"])
    except ValueError as exc:
        assert "Unknown symbol_id: unknown" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for unknown symbol")


def test_start_batch_run_emits_run_and_ok_messages() -> None:
    cfg = DETMConfig(width=8, height=8, backend="numpy")
    calls: list[int] = []

    def _fake_run_headless(config, seed, symbol_ids, steps, out_dir, viz_transport, **kwargs):  # noqa: ANN001
        assert config is cfg
        assert symbol_ids == ["pulse"]
        assert int(steps) == 3
        assert viz_transport is None
        assert isinstance(out_dir, Path)
        calls.append(int(seed))

    req = BatchRunRequest(
        config=cfg,
        symbol_ids=["pulse"],
        batch_n=2,
        seed0=10,
        tick_budget=3,
        out_root=Path("runs/out/test_batch_service"),
    )
    handle = start_batch_run(req, run_headless_fn=_fake_run_headless)

    messages: list[str] = []
    done = False
    for _ in range(200):
        items, done = handle.drain_messages()
        messages.extend(items)
        if done:
            break
        time.sleep(0.01)

    assert done is True
    assert calls == [10, 11]
    assert "[run] seed=10" in messages
    assert "[ok] seed=10" in messages
    assert "[run] seed=11" in messages
    assert "[ok] seed=11" in messages


def test_start_batch_run_cancel_stops_future_seeds() -> None:
    cfg = DETMConfig(width=8, height=8, backend="numpy")
    calls: list[int] = []

    def _slow_run_headless(config, seed, symbol_ids, steps, out_dir, viz_transport, **kwargs):  # noqa: ANN001
        calls.append(int(seed))
        time.sleep(0.03)

    req = BatchRunRequest(
        config=cfg,
        symbol_ids=["pulse"],
        batch_n=5,
        seed0=0,
        tick_budget=2,
        out_root=Path("runs/out/test_batch_cancel"),
    )
    handle = start_batch_run(req, run_headless_fn=_slow_run_headless)

    messages: list[str] = []
    seen_first_run = False
    done = False
    for _ in range(300):
        items, done = handle.drain_messages()
        messages.extend(items)
        if any(msg == "[run] seed=0" for msg in items):
            seen_first_run = True
            handle.cancel()
        if done:
            break
        time.sleep(0.01)

    assert done is True
    assert seen_first_run is True
    assert any(msg == "[batch] canceled" for msg in messages)
    assert len(calls) < 5
