"""Shared batch orchestration service for UI frontends."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from detm.runtime.config import DETMConfig


@dataclass(frozen=True)
class BatchRunRequest:
    config: DETMConfig
    symbol_ids: list[str]
    batch_n: int
    seed0: int
    tick_budget: int
    out_root: Path
    fields_npz: bool = False
    fields_every_steps: int = 1
    invariant_streams: list[str] | None = None


def parse_batch_symbols_csv(text: str, *, available_symbols: Sequence[str]) -> list[str]:
    raw = [chunk.strip() for chunk in str(text or "").split(",") if chunk.strip()]
    if not raw:
        return list(available_symbols)
    known = set(str(symbol) for symbol in available_symbols)
    out: list[str] = []
    for sid in raw:
        if sid not in known:
            raise ValueError(f"Unknown symbol_id: {sid}")
        out.append(sid)
    return out


def build_batch_start_message(request: BatchRunRequest) -> str:
    return (
        f"[batch] n={int(request.batch_n)} seed0={int(request.seed0)} "
        f"tick_budget={int(request.tick_budget)} symbols={len(request.symbol_ids)} "
        f"out={str(request.out_root)}"
    )


class BatchRunHandle:
    def __init__(
        self,
        *,
        message_queue: queue.Queue[str | None],
        cancel_event: threading.Event,
        thread: threading.Thread,
    ) -> None:
        self._message_queue = message_queue
        self._cancel_event = cancel_event
        self._thread = thread
        self._finished = False

    def cancel(self) -> None:
        self._cancel_event.set()

    def drain_messages(self) -> tuple[list[str], bool]:
        out: list[str] = []
        done = bool(self._finished)
        while True:
            try:
                item = self._message_queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                done = True
                self._finished = True
                break
            out.append(str(item))
        return out, done

    @property
    def finished(self) -> bool:
        return bool(self._finished)


def start_batch_run(
    request: BatchRunRequest,
    *,
    run_headless_fn: Callable[..., object] | None = None,
) -> BatchRunHandle:
    if run_headless_fn is None:
        from detm_app.runner.headless import run_headless as run_headless_fn  # lazy import

    message_queue: queue.Queue[str | None] = queue.Queue()
    cancel_event = threading.Event()

    def _worker() -> None:
        for index in range(max(1, int(request.batch_n))):
            if cancel_event.is_set():
                message_queue.put("[batch] canceled")
                break
            seed = int(request.seed0 + index)
            message_queue.put(f"[run] seed={seed}")
            try:
                run_headless_fn(
                    request.config,
                    seed,
                    request.symbol_ids,
                    int(request.tick_budget),
                    Path(request.out_root) / f"seed_{seed:04d}",
                    None,
                    steps_mode="total",
                    fields_npz=bool(request.fields_npz),
                    fields_every_steps=max(1, int(request.fields_every_steps)),
                    invariant_streams=request.invariant_streams,
                )
                message_queue.put(f"[ok] seed={seed}")
            except Exception as exc:  # pragma: no cover - runtime failure branch
                message_queue.put(f"[error] seed={seed} {exc}")
                break
        message_queue.put(None)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return BatchRunHandle(message_queue=message_queue, cancel_event=cancel_event, thread=thread)


__all__ = [
    "BatchRunHandle",
    "BatchRunRequest",
    "build_batch_start_message",
    "parse_batch_symbols_csv",
    "start_batch_run",
]
