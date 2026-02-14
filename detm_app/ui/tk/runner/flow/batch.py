"""Batch flow helpers for Tk runner launcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from detm.runtime.symbols import list_symbols
from detm_app.runner.batch_service import (
    BatchRunHandle,
    BatchRunRequest,
    build_batch_start_message,
    parse_batch_symbols_csv,
    start_batch_run,
)


class TkBatchFlow:
    def __init__(
        self,
        *,
        root: Any,
        tk: Any,
        ttk: Any,
        parent: Any,
        row: int,
        build_config_from_widgets: Callable[[], Any],
        read_invariant_streams: Callable[[], str],
        log: Callable[[str], None],
        clear_log: Callable[[], None],
        show_viz_view: Callable[[str], None],
    ) -> None:
        self._root = root
        self._tk = tk
        self._ttk = ttk
        self._build_config_from_widgets = build_config_from_widgets
        self._read_invariant_streams = read_invariant_streams
        self._log = log
        self._clear_log = clear_log
        self._show_viz_view = show_viz_view
        self._batch_running = False
        self._batch_handle: BatchRunHandle | None = None

        self.frame = ttk.LabelFrame(parent, text="Batch", padding=8)
        self.frame.grid(row=row, column=0, columnspan=4, sticky="we", pady=(8, 0))
        self.frame.grid_remove()

        self._batch_n_var = tk.IntVar(value=10)
        self._batch_seed0_var = tk.IntVar(value=0)
        self._batch_steps_var = tk.IntVar(value=4)
        self._batch_symbols_var = tk.StringVar(value="")
        self._batch_out_var = tk.StringVar(value="runs/out/batch_ui")
        self._batch_record_fields_var = tk.BooleanVar(value=False)
        self._batch_fields_every_var = tk.IntVar(value=1)

        ttk.Label(self.frame, text="N").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.frame, textvariable=self._batch_n_var, width=6).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(self.frame, text="seed0").grid(row=0, column=2, sticky="w")
        ttk.Entry(self.frame, textvariable=self._batch_seed0_var, width=8).grid(
            row=0, column=3, sticky="w", padx=(6, 12)
        )
        ttk.Label(self.frame, text="ticks/symbol").grid(row=0, column=4, sticky="w")
        ttk.Entry(self.frame, textvariable=self._batch_steps_var, width=8).grid(row=0, column=5, sticky="w", padx=(6, 0))

        ttk.Label(self.frame, text="symbols").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(self.frame, textvariable=self._batch_symbols_var, width=42).grid(
            row=1, column=1, columnspan=5, sticky="we", padx=(6, 0), pady=(6, 0)
        )
        ttk.Label(self.frame, text="out").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(self.frame, textvariable=self._batch_out_var, width=42).grid(
            row=2, column=1, columnspan=5, sticky="we", padx=(6, 0), pady=(6, 0)
        )
        ttk.Checkbutton(self.frame, text="fields_hist.npz", variable=self._batch_record_fields_var).grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Label(self.frame, text="every").grid(row=3, column=2, sticky="w", pady=(6, 0))
        ttk.Entry(self.frame, textvariable=self._batch_fields_every_var, width=6).grid(
            row=3, column=3, sticky="w", padx=(6, 0), pady=(6, 0)
        )

        batch_btns = ttk.Frame(self.frame)
        batch_btns.grid(row=4, column=0, columnspan=6, sticky="w", pady=(8, 0))
        ttk.Button(batch_btns, text="Run/Stop batch", command=self.on_toggle).grid(row=0, column=0, padx=(0, 6))

    def _poll_queue(self) -> None:
        if self._batch_handle is None:
            return
        items, done = self._batch_handle.drain_messages()
        for item in items:
            self._log(str(item))
        if done:
            self._batch_running = False
            self._batch_handle = None
            return
        self._root.after(75, self._poll_queue)

    def on_toggle(self) -> None:
        if self._batch_running:
            if self._batch_handle is not None:
                self._batch_handle.cancel()
            self._log("[cancel] requested")
            return

        try:
            cfg = self._build_config_from_widgets()
            symbol_ids = parse_batch_symbols_csv(str(self._batch_symbols_var.get() or ""), available_symbols=list_symbols())
            batch_n = max(1, int(self._batch_n_var.get()))
            seed0 = int(self._batch_seed0_var.get())
            steps = max(1, int(self._batch_steps_var.get()))
            out_root = Path(self._batch_out_var.get() or "runs/out/batch_ui")
            fields_npz = bool(self._batch_record_fields_var.get())
            fields_every = max(1, int(self._batch_fields_every_var.get()))
            invariant_streams = [s.strip() for s in str(self._read_invariant_streams() or "").split(",") if s.strip()] or None
        except Exception as exc:
            self._show_viz_view("log")
            self._log(f"[error] {exc}")
            return

        self._show_viz_view("log")
        self._clear_log()
        request = BatchRunRequest(
            config=cfg,
            symbol_ids=symbol_ids,
            batch_n=int(batch_n),
            seed0=int(seed0),
            tick_budget=int(steps),
            out_root=Path(out_root),
            fields_npz=bool(fields_npz),
            fields_every_steps=int(fields_every),
            invariant_streams=invariant_streams,
        )
        self._log(build_batch_start_message(request))
        self._batch_running = True
        self._batch_handle = start_batch_run(request)
        self._root.after(75, self._poll_queue)

    def close(self) -> None:
        if self._batch_handle is not None:
            self._batch_handle.cancel()
            self._batch_handle = None
        self._batch_running = False


__all__ = ["TkBatchFlow"]
