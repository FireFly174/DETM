"""Lightweight Tkinter settings UI.

The UI is intentionally "controller-only": it does not render fields itself.
If visualization is enabled, it starts a separate viz daemon process and streams
serialized DETM state blobs to it.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.symbols import list_symbols, make_symbol
from detm.viz.client import VizClient, VizDaemon, start_local_daemon


@dataclass
class UiRunSettings:
    config: DETMConfig
    seed: int = 1
    ticks_per_step: int = 4
    tick_interval_ms: int = 60
    symbol_id: str = "pulse"
    amplitude: float = 1.0
    record_dir: Optional[Path] = None
    viz_enabled: bool = True
    viz_host: str = "127.0.0.1"
    viz_port: int = 0


class DetmTkRunner:
    def __init__(self, settings: UiRunSettings):
        self.settings = settings
        self._state = api.reset(settings.config, settings.seed)
        self._last_obs = api.step(self._state, None, 0)[1]
        self._running = False
        self._trace_fh = None
        self._viz_daemon: VizDaemon | None = None
        self._viz_client: VizClient | None = None

    @property
    def state(self):
        return self._state

    @property
    def last_observables(self):
        return self._last_obs

    def close(self) -> None:
        self._running = False
        if self._trace_fh is not None:
            self._trace_fh.close()
            self._trace_fh = None
        if self._viz_client is not None:
            self._viz_client.close()
            self._viz_client = None
        if self._viz_daemon is not None:
            self._viz_daemon.terminate()
            self._viz_daemon = None

    def reset(self) -> None:
        self._state = api.reset(self.settings.config, self.settings.seed)
        self._last_obs = api.step(self._state, None, 0)[1]
        self._send_viz()

    def set_viz_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if not enabled:
            if self._viz_client is not None:
                self._viz_client.close()
                self._viz_client = None
            if self._viz_daemon is not None:
                self._viz_daemon.terminate()
                self._viz_daemon = None
            return
        self.ensure_viz()

    def ensure_viz(self) -> None:
        if not self.settings.viz_enabled:
            return
        if self._viz_client is not None:
            return
        self._viz_daemon = start_local_daemon(host=self.settings.viz_host, port=self.settings.viz_port)
        self._viz_client = self._viz_daemon.connect()
        self._send_viz()

    def _send_viz(self) -> None:
        if self._viz_client is None:
            return
        sig = api.digest(self._state).vector
        self._viz_client.send_state(state_blob=api.serialize(self._state), tick=int(self._state.step_count), signature=sig)

    def _make_influence(self) -> Optional[DETMInfluence]:
        symbol_id = (self.settings.symbol_id or "").strip()
        if not symbol_id or symbol_id == "(none)":
            return None
        return make_symbol(symbol_id, amplitude=float(self.settings.amplitude))

    def step_once(self) -> None:
        influence = self._make_influence()
        start = time.perf_counter()
        self._state, self._last_obs = api.step(self._state, influence, int(self.settings.ticks_per_step))
        elapsed = (time.perf_counter() - start) * 1000.0
        self._send_viz()

        if self.settings.record_dir is not None:
            self._ensure_trace()
            entry = {
                "tick": int(self._state.step_count),
                "signature": self._last_obs.signature.as_dict(),
                "field_summaries": {
                    "energy": self._last_obs.field_summaries.energy,
                    "entropy": self._last_obs.field_summaries.entropy,
                    "internal_time": self._last_obs.field_summaries.internal_time,
                },
                "cost": dict(self._last_obs.cost),
                "quality": dict(self._last_obs.quality),
                "events": list(self._last_obs.events),
                "ui": {"elapsed_ms": elapsed},
            }
            self._trace_fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._trace_fh.flush()

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def _ensure_trace(self) -> None:
        if self._trace_fh is not None:
            return
        record_dir = self.settings.record_dir
        if record_dir is None:
            return
        record_dir.mkdir(parents=True, exist_ok=True)
        self._trace_fh = (record_dir / "trace.jsonl").open("a", encoding="utf-8")


def launch_tk_ui(settings: UiRunSettings) -> None:  # pragma: no cover
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as exc:
        raise RuntimeError("Tkinter is required for the UI (python -m tkinter)") from exc

    runner = DetmTkRunner(settings)

    root = tk.Tk()
    root.title("DETM Runner")

    symbols = ["(none)"] + list_symbols()

    frm = ttk.Frame(root, padding=10)
    frm.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Settings widgets
    ttk.Label(frm, text="Backend").grid(row=0, column=0, sticky="w")
    backend_var = tk.StringVar(value=settings.config.backend)
    backend_box = ttk.Combobox(frm, textvariable=backend_var, values=["torch", "numpy"], width=10)
    backend_box.grid(row=0, column=1, sticky="w", padx=(6, 12))

    ttk.Label(frm, text="Device").grid(row=0, column=2, sticky="w")
    device_var = tk.StringVar(value=settings.config.device)
    ttk.Entry(frm, textvariable=device_var, width=12).grid(row=0, column=3, sticky="w", padx=(6, 12))

    ttk.Label(frm, text="Lattice (W×H)").grid(row=1, column=0, sticky="w")
    w_var = tk.IntVar(value=settings.config.width)
    h_var = tk.IntVar(value=settings.config.height)
    ttk.Entry(frm, textvariable=w_var, width=6).grid(row=1, column=1, sticky="w")
    ttk.Entry(frm, textvariable=h_var, width=6).grid(row=1, column=1, sticky="e")

    ttk.Label(frm, text="Seed").grid(row=1, column=2, sticky="w")
    seed_var = tk.IntVar(value=settings.seed)
    ttk.Entry(frm, textvariable=seed_var, width=12).grid(row=1, column=3, sticky="w", padx=(6, 12))

    ttk.Label(frm, text="Symbol").grid(row=2, column=0, sticky="w")
    symbol_var = tk.StringVar(value=settings.symbol_id)
    sym_box = ttk.Combobox(frm, textvariable=symbol_var, values=symbols, width=16)
    sym_box.grid(row=2, column=1, sticky="w", padx=(0, 12))

    ttk.Label(frm, text="Amp").grid(row=2, column=2, sticky="w")
    amp_var = tk.DoubleVar(value=settings.amplitude)
    ttk.Entry(frm, textvariable=amp_var, width=12).grid(row=2, column=3, sticky="w", padx=(6, 12))

    ttk.Label(frm, text="Ticks/step").grid(row=3, column=0, sticky="w")
    ticks_var = tk.IntVar(value=settings.ticks_per_step)
    ttk.Entry(frm, textvariable=ticks_var, width=8).grid(row=3, column=1, sticky="w")

    ttk.Label(frm, text="Interval (ms)").grid(row=3, column=2, sticky="w")
    interval_var = tk.IntVar(value=settings.tick_interval_ms)
    ttk.Entry(frm, textvariable=interval_var, width=12).grid(row=3, column=3, sticky="w", padx=(6, 12))

    record_var = tk.BooleanVar(value=settings.record_dir is not None)
    ttk.Checkbutton(frm, text="Record trace", variable=record_var).grid(row=4, column=0, sticky="w")
    out_var = tk.StringVar(value=str(settings.record_dir) if settings.record_dir else "runs/out/ui_run")
    ttk.Entry(frm, textvariable=out_var, width=38).grid(row=4, column=1, columnspan=3, sticky="we", padx=(6, 0))
    frm.columnconfigure(3, weight=1)

    viz_enabled_var = tk.BooleanVar(value=settings.viz_enabled)
    ttk.Checkbutton(frm, text="Viz daemon", variable=viz_enabled_var).grid(row=5, column=0, sticky="w")
    viz_host_var = tk.StringVar(value=settings.viz_host)
    ttk.Entry(frm, textvariable=viz_host_var, width=14).grid(row=5, column=1, sticky="w", padx=(6, 6))
    viz_port_var = tk.IntVar(value=settings.viz_port)
    ttk.Entry(frm, textvariable=viz_port_var, width=8).grid(row=5, column=2, sticky="w")
    ttk.Label(frm, text="host/port").grid(row=5, column=3, sticky="w")

    status = tk.StringVar(value="Ready")
    ttk.Label(frm, textvariable=status).grid(row=6, column=0, columnspan=4, sticky="w")

    def _apply_settings_to_runner(reset: bool) -> None:
        cfg = DETMConfig.from_dict(
            {
                **settings.config.to_dict(),
                "backend": backend_var.get().strip() or settings.config.backend,
                "device": device_var.get().strip() or settings.config.device,
                "width": int(w_var.get()),
                "height": int(h_var.get()),
            }
        )
        settings.config = cfg
        settings.seed = int(seed_var.get())
        settings.symbol_id = symbol_var.get()
        settings.amplitude = float(amp_var.get())
        settings.ticks_per_step = int(ticks_var.get())
        settings.tick_interval_ms = int(interval_var.get())
        settings.record_dir = Path(out_var.get()) if record_var.get() else None
        settings.viz_enabled = bool(viz_enabled_var.get())
        settings.viz_host = str(viz_host_var.get()).strip() or "127.0.0.1"
        settings.viz_port = int(viz_port_var.get())
        runner.settings = settings
        if reset:
            runner.reset()
        runner.set_viz_enabled(settings.viz_enabled)

    def _update_status():
        st = runner.state
        sig = runner.last_observables.signature.vector
        status.set(f"tick={st.step_count}  sig0..3={sig[:4]}  backend={settings.config.backend}/{settings.config.device}")

    def _tick():
        if runner.is_running():
            runner.step_once()
            _update_status()
            root.after(max(1, settings.tick_interval_ms), _tick)

    def on_reset():
        _apply_settings_to_runner(reset=True)
        _update_status()

    def on_step():
        _apply_settings_to_runner(reset=False)
        runner.step_once()
        _update_status()

    def on_run_toggle():
        _apply_settings_to_runner(reset=False)
        if runner.is_running():
            runner.stop()
        else:
            runner.start()
            _tick()

    btns = ttk.Frame(frm)
    btns.grid(row=7, column=0, columnspan=4, sticky="w", pady=(6, 0))
    ttk.Button(btns, text="Reset", command=on_reset).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(btns, text="Step", command=on_step).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(btns, text="Run/Stop", command=on_run_toggle).grid(row=0, column=2, padx=(0, 6))

    def _on_close():
        runner.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    runner.set_viz_enabled(bool(settings.viz_enabled))
    _update_status()
    root.mainloop()


__all__ = ["DetmTkRunner", "UiRunSettings", "launch_tk_ui"]
