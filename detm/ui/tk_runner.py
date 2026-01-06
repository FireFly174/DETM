"""Lightweight Tkinter settings UI.

The UI is intentionally "controller-only": it does not render fields itself.
If visualization is enabled, it starts a separate viz daemon process and streams
serialized DETM state blobs to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.symbols import list_symbols, make_symbol
from detm.run.bus import EventBus
from detm.run.session import DetmSession
from detm.run.subscribers import ArtifactWriter, JsonlTraceWriter, VizStreamer
from detm.viz.transport import VizTransport, open_viz_transport


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
    viz_transport: str = "tcp"  # tcp | none
    viz_host: str = "127.0.0.1"
    viz_port: int = 0
    viz_connect: bool = False
    viz_keep_open: bool = False
    viz_every_steps: int = 1


class DetmTkRunner:
    def __init__(self, settings: UiRunSettings):
        self.settings = settings
        self._bus = EventBus()
        self._session = DetmSession.create(settings.config, settings.seed, bus=self._bus)
        self._last_signature = self._session.digest().vector
        self._running = False
        self._viz_transport: VizTransport | None = None
        self._viz_streamer: VizStreamer | None = None
        self._viz_key: tuple | None = None
        self._trace_writer: JsonlTraceWriter | None = None
        self._artifact_writer: ArtifactWriter | None = None

        self._configure_recording()
        self._configure_viz()

    @property
    def state(self):
        return self._session.state

    @property
    def last_observables(self):
        return self._last_signature

    def close(self) -> None:
        self._running = False
        self._session.close()
        self._disable_viz()
        self._disable_recording()

    def reset(self) -> None:
        self._session.config = self.settings.config
        self._session.reset(seed=self.settings.seed)
        self._last_signature = self._session.digest().vector

    def set_viz_enabled(self, enabled: bool) -> None:
        self.settings.viz_enabled = bool(enabled)
        self._configure_viz()

    def _make_influence(self) -> Optional[DETMInfluence]:
        symbol_id = (self.settings.symbol_id or "").strip()
        if not symbol_id or symbol_id == "(none)":
            return None
        return make_symbol(symbol_id, amplitude=float(self.settings.amplitude))

    def step_once(self) -> None:
        influence = self._make_influence()
        obs = self._session.step(influence, int(self.settings.ticks_per_step))
        self._last_signature = obs.signature.vector

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def _disable_viz(self) -> None:
        if self._viz_streamer is not None:
            self._viz_streamer.detach()
            self._viz_streamer = None
        if self._viz_transport is not None:
            self._viz_transport.close()
            self._viz_transport = None
        self._viz_key = None

    def _configure_viz(self) -> None:
        if not bool(self.settings.viz_enabled) or str(self.settings.viz_transport).lower() == "none":
            self._disable_viz()
            return

        desired_key = (
            str(self.settings.viz_transport),
            str(self.settings.viz_host),
            int(self.settings.viz_port),
            bool(self.settings.viz_connect),
            bool(self.settings.viz_keep_open),
            int(self.settings.viz_every_steps),
        )
        if self._viz_key is not None and self._viz_key != desired_key:
            self._disable_viz()

        if self._viz_transport is None:
            self._viz_transport = open_viz_transport(
                enabled=True,
                transport=str(self.settings.viz_transport),
                host=str(self.settings.viz_host),
                port=int(self.settings.viz_port),
                connect=bool(self.settings.viz_connect),
                keep_open=bool(self.settings.viz_keep_open),
            )
            self._viz_streamer = VizStreamer.attach(
                self._session.bus,
                self._viz_transport,
                every_steps=int(self.settings.viz_every_steps),
            )
            self._viz_key = desired_key
            self._viz_streamer.on_reset(state=self._session.state)

    def _disable_recording(self) -> None:
        if self._trace_writer is not None:
            self._trace_writer.on_close()
            self._trace_writer = None
        if self._artifact_writer is not None:
            self._artifact_writer.detach()
            self._artifact_writer = None

    def _configure_recording(self) -> None:
        record_dir = self.settings.record_dir
        if record_dir is None:
            self._disable_recording()
            return

        record_dir = Path(record_dir)
        if self._trace_writer is None:
            self._trace_writer = JsonlTraceWriter.attach(self._session.bus, record_dir / "trace.jsonl")
            self._artifact_writer = ArtifactWriter.attach(self._session.bus, record_dir)
            return

        if self._trace_writer.path.resolve() != (record_dir / "trace.jsonl").resolve():
            self._disable_recording()
            self._trace_writer = JsonlTraceWriter.attach(self._session.bus, record_dir / "trace.jsonl")
            self._artifact_writer = ArtifactWriter.attach(self._session.bus, record_dir)


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
    viz_transport_var = tk.StringVar(value=settings.viz_transport)
    ttk.Combobox(frm, textvariable=viz_transport_var, values=["tcp", "none"], width=6).grid(
        row=5, column=1, sticky="w", padx=(6, 6)
    )
    viz_host_var = tk.StringVar(value=settings.viz_host)
    ttk.Entry(frm, textvariable=viz_host_var, width=14).grid(row=5, column=2, sticky="w", padx=(6, 6))
    viz_port_var = tk.IntVar(value=settings.viz_port)
    ttk.Entry(frm, textvariable=viz_port_var, width=8).grid(row=5, column=3, sticky="w")

    viz_connect_var = tk.BooleanVar(value=settings.viz_connect)
    ttk.Checkbutton(frm, text="connect", variable=viz_connect_var).grid(row=6, column=0, sticky="w")
    viz_every_var = tk.IntVar(value=settings.viz_every_steps)
    ttk.Entry(frm, textvariable=viz_every_var, width=6).grid(row=6, column=1, sticky="w", padx=(6, 6))
    ttk.Label(frm, text="every_steps").grid(row=6, column=2, sticky="w")

    status = tk.StringVar(value="Ready")
    ttk.Label(frm, textvariable=status).grid(row=7, column=0, columnspan=4, sticky="w")

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
        settings.viz_transport = str(viz_transport_var.get()).strip() or "tcp"
        settings.viz_host = str(viz_host_var.get()).strip() or "127.0.0.1"
        settings.viz_port = int(viz_port_var.get())
        settings.viz_connect = bool(viz_connect_var.get()) and settings.viz_port > 0
        settings.viz_every_steps = int(viz_every_var.get())
        runner.settings = settings
        if reset:
            runner.reset()
        runner._configure_recording()
        runner._configure_viz()

    def _update_status():
        st = runner.state
        sig = runner.last_observables
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
    btns.grid(row=8, column=0, columnspan=4, sticky="w", pady=(6, 0))
    ttk.Button(btns, text="Reset", command=on_reset).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(btns, text="Step", command=on_step).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(btns, text="Run/Stop", command=on_run_toggle).grid(row=0, column=2, padx=(0, 6))

    def _on_close():
        runner.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    runner._configure_recording()
    runner._configure_viz()
    _update_status()
    root.mainloop()


__all__ = ["DetmTkRunner", "UiRunSettings", "launch_tk_ui"]
