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
from detm.run.coarsening import InvariantCoarsener, parse_invariant_streams
from detm.run.session import DetmSession
from detm.run.subscribers import (
    ArtifactWriter,
    FieldHistoryRecorder,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    VizStreamer,
)
from detm.viz.transport import VizTransport, open_viz_transport


@dataclass
class UiRunSettings:
    config: DETMConfig
    seed: int = 1  # int >= 0  /// seed эпизода
    ticks_per_step: int = 4  # int > 0  /// L0-тиков на шаг UI
    tick_interval_ms: int = 60  # int >= 1  /// задержка между шагами
    # symbol | joystick_field | joystick_patch | source_sink | none  /// режим влияния
    influence_mode: str = "none"
    symbol_id: str = "none"  # list_symbols() | (none)  /// выбранный символ
    amplitude: float = 0.005  # float  /// сила влияния
    influence_duration_steps: int = 0  # 0 | int > 0  /// длительность влияния
    joy_dx: float = 0.0  # float -1..1  /// наклон поля по X
    joy_dy: float = 0.0  # float -1..1  /// наклон поля по Y
    patch_cx: int = 12  # int 0..W-1  /// центр патча по X
    patch_cy: int = 12  # int 0..H-1  /// центр патча по Y
    patch_radius: int = 6  # int >= 0  /// радиус патча
    source_x: int = 6  # int 0..W-1  /// X источника энергии
    source_y: int = 12  # int 0..H-1  /// Y источника энергии
    sink_x: int = 18  # int 0..W-1  /// X стока энергии
    sink_y: int = 12  # int 0..H-1  /// Y стока энергии
    source_value: float = 1.0  # float 0..1  /// значение источника
    sink_value: float = 0.0  # float 0..1  /// значение стока
    record_dir: Optional[Path] = None  # path | None  /// директория записи
    record_fields: bool = False  # False | True  /// запись fields_hist.npz
    invariant_streams: str = ""  # "" | "inv0=1/10,..."  /// инвариантные тики
    viz_enabled: bool = True  # False | True  /// включить viz-демон
    viz_transport: str = "tcp"  # tcp | none  /// транспорт визуализации
    viz_host: str = "127.0.0.1"  # host  /// адрес viz-демона
    viz_port: int = 0  # 0 | int > 0  /// порт viz-демона
    viz_connect: bool = False  # False | True  /// connect к внешнему daemon
    viz_keep_open: bool = False  # False | True  /// не закрывать daemon
    viz_every_steps: int = 1  # int > 0  /// период отправки кадров


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
        self._invariant_writer: InvariantTickJsonlWriter | None = None
        self._artifact_writer: ArtifactWriter | None = None
        self._fields_recorder: FieldHistoryRecorder | None = None
        self._coarsener: InvariantCoarsener | None = None
        self._invariant_key: str | None = None
        self._last_influence_key: tuple | None = None
        self._influence_remaining: int = 0

        self._configure_recording()
        self._configure_viz()
        self._configure_invariants()

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
        self._disable_invariants()

    def reset(self) -> None:
        self._session.config = self.settings.config
        self._session.reset(seed=self.settings.seed)
        self._last_signature = self._session.digest().vector

    def set_viz_enabled(self, enabled: bool) -> None:
        self.settings.viz_enabled = bool(enabled)
        self._configure_viz()

    def _make_influence(self) -> Optional[DETMInfluence]:
        mode = str(getattr(self.settings, "influence_mode", "symbol") or "symbol").strip().lower()
        duration_steps = int(getattr(self.settings, "influence_duration_steps", 0) or 0)
        amplitude = float(getattr(self.settings, "amplitude", 0.0))

        if mode in {"none", "(none)", ""}:
            return None

        if mode == "symbol":
            symbol_id = (self.settings.symbol_id or "").strip()
            if not symbol_id or symbol_id == "(none)":
                return None
            key = ("symbol", symbol_id, amplitude)
            influence = make_symbol(symbol_id, amplitude=amplitude)
        elif mode == "joystick_field":
            dx = float(getattr(self.settings, "joy_dx", 0.0))
            dy = float(getattr(self.settings, "joy_dy", 0.0))
            key = ("joystick_field", amplitude, dx, dy)
            influence = DETMInfluence(
                symbol_id="joystick_field",
                amplitude=amplitude,
                external_features={"dx": dx, "dy": dy},
            )
        elif mode == "joystick_patch":
            w, h = int(self.settings.config.width), int(self.settings.config.height)
            cx = int(getattr(self.settings, "patch_cx", w // 2)) % max(1, w)
            cy = int(getattr(self.settings, "patch_cy", h // 2)) % max(1, h)
            radius = int(
                getattr(
                    self.settings,
                    "patch_radius",
                    max(1, max(self.settings.config.width, self.settings.config.height) // 8),
                )
            )
            key = ("joystick_patch", amplitude, cx, cy, radius)
            influence = DETMInfluence(symbol_id="joystick_patch", amplitude=amplitude, region=(cx, cy, radius))
        elif mode == "source_sink":
            sx = int(getattr(self.settings, "source_x", 0))
            sy = int(getattr(self.settings, "source_y", 0))
            tx = int(getattr(self.settings, "sink_x", 0))
            ty = int(getattr(self.settings, "sink_y", 0))
            sv = float(getattr(self.settings, "source_value", 1.0))
            tv = float(getattr(self.settings, "sink_value", 0.0))
            key = ("source_sink", amplitude, sx, sy, tx, ty, sv, tv)
            influence = DETMInfluence(
                symbol_id="source_sink",
                amplitude=amplitude,
                external_features={
                    "src_x": float(sx),
                    "src_y": float(sy),
                    "dst_x": float(tx),
                    "dst_y": float(ty),
                    "src_value": float(sv),
                    "dst_value": float(tv),
                },
            )
        else:
            # Unknown mode: fall back to no influence.
            return None

        if duration_steps > 0:
            if self._last_influence_key != key:
                self._last_influence_key = key
                self._influence_remaining = int(duration_steps)
            if self._influence_remaining <= 0:
                return None
            self._influence_remaining -= 1
        else:
            self._last_influence_key = key
            self._influence_remaining = 0

        return influence

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
        if self._invariant_writer is not None:
            self._invariant_writer.on_close()
            self._invariant_writer = None
        if self._artifact_writer is not None:
            self._artifact_writer.detach()
            self._artifact_writer = None
        if self._fields_recorder is not None:
            self._fields_recorder.detach()
            self._fields_recorder = None

    def _disable_invariants(self) -> None:
        if self._coarsener is not None:
            self._coarsener.detach()
            self._coarsener = None
        if self._invariant_writer is not None:
            self._invariant_writer.on_close()
            self._invariant_writer = None
        self._invariant_key = None

    def _configure_invariants(self) -> None:
        key = (self.settings.invariant_streams or "").strip()
        if not key:
            self._disable_invariants()
            return
        if self._invariant_key == key and self._coarsener is not None:
            return
        self._disable_invariants()
        self._coarsener = InvariantCoarsener.attach(self._session.bus, parse_invariant_streams(key))
        self._invariant_key = key
        self._configure_invariant_recording()

    def _configure_invariant_recording(self) -> None:
        record_dir = self.settings.record_dir
        invariant_key = (self.settings.invariant_streams or "").strip()
        if record_dir is None or not invariant_key:
            if self._invariant_writer is not None:
                self._invariant_writer.on_close()
                self._invariant_writer = None
            return

        record_dir = Path(record_dir)
        desired_path = record_dir / "invariants.jsonl"
        if self._invariant_writer is None:
            self._invariant_writer = InvariantTickJsonlWriter.attach(self._session.bus, desired_path)
            return
        if self._invariant_writer.path.resolve() != desired_path.resolve():
            self._invariant_writer.on_close()
            self._invariant_writer = InvariantTickJsonlWriter.attach(self._session.bus, desired_path)

    def _configure_recording(self) -> None:
        record_dir = self.settings.record_dir
        if record_dir is None:
            self._disable_recording()
            return

        record_dir = Path(record_dir)
        if self._trace_writer is None:
            self._trace_writer = JsonlTraceWriter.attach(self._session.bus, record_dir / "trace.jsonl")
            self._configure_invariant_recording()
            self._artifact_writer = ArtifactWriter.attach(self._session.bus, record_dir)
            if bool(self.settings.record_fields):
                self._fields_recorder = FieldHistoryRecorder.attach(self._session.bus, record_dir / "fields_hist.npz")
            return

        if self._trace_writer.path.resolve() != (record_dir / "trace.jsonl").resolve():
            self._disable_recording()
            self._trace_writer = JsonlTraceWriter.attach(self._session.bus, record_dir / "trace.jsonl")
            self._configure_invariant_recording()
            self._artifact_writer = ArtifactWriter.attach(self._session.bus, record_dir)
            if bool(self.settings.record_fields):
                self._fields_recorder = FieldHistoryRecorder.attach(self._session.bus, record_dir / "fields_hist.npz")
        else:
            # Toggle field recorder without changing directory
            if bool(self.settings.record_fields) and self._fields_recorder is None:
                self._fields_recorder = FieldHistoryRecorder.attach(self._session.bus, record_dir / "fields_hist.npz")
            if (not bool(self.settings.record_fields)) and self._fields_recorder is not None:
                self._fields_recorder.detach()
                self._fields_recorder = None
            self._configure_invariant_recording()


def launch_tk_ui(settings: UiRunSettings) -> None:  # pragma: no cover
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as exc:
        raise RuntimeError("Tkinter is required for the UI (python -m tkinter)") from exc

    def _install_clipboard_shortcuts(root: "tk.Tk") -> None:
        def gen(event_name: str):
            w = root.focus_get()
            if w is None:
                return
            try:
                w.event_generate(event_name)
            except Exception:
                return

        def select_all():
            w = root.focus_get()
            if w is None:
                return
            try:
                w.selection_range(0, "end")
                w.icursor("end")
                return
            except Exception:
                pass
            try:
                w.tag_add("sel", "1.0", "end")
                w.mark_set("insert", "end")
            except Exception:
                return

        root.bind_all("<Control-c>", lambda _e: gen("<<Copy>>"), add=True)
        root.bind_all("<Control-v>", lambda _e: gen("<<Paste>>"), add=True)
        root.bind_all("<Control-x>", lambda _e: gen("<<Cut>>"), add=True)
        root.bind_all("<Control-a>", lambda _e: select_all(), add=True)

    runner = DetmTkRunner(settings)

    root = tk.Tk()
    root.title("DETM Runner")
    _install_clipboard_shortcuts(root)

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

    dyn_frame = ttk.Frame(frm)
    dyn_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=(4, 0))
    dyn = settings.config.dynamics
    ttk.Label(dyn_frame, text="Dyn a,b,k,g,t").grid(row=0, column=0, sticky="w")
    alpha_var = tk.DoubleVar(value=float(dyn.alpha))
    beta_var = tk.DoubleVar(value=float(dyn.beta))
    kappa_var = tk.DoubleVar(value=float(dyn.kappa))
    gamma_var = tk.DoubleVar(value=float(dyn.gamma))
    lambda_t_var = tk.DoubleVar(value=float(dyn.lambda_t))
    ttk.Entry(dyn_frame, textvariable=alpha_var, width=7).grid(row=0, column=1, sticky="w", padx=(6, 0))
    ttk.Entry(dyn_frame, textvariable=beta_var, width=7).grid(row=0, column=2, sticky="w", padx=(6, 0))
    ttk.Entry(dyn_frame, textvariable=kappa_var, width=7).grid(row=0, column=3, sticky="w", padx=(6, 0))
    ttk.Entry(dyn_frame, textvariable=gamma_var, width=7).grid(row=0, column=4, sticky="w", padx=(6, 0))
    ttk.Entry(dyn_frame, textvariable=lambda_t_var, width=7).grid(row=0, column=5, sticky="w", padx=(6, 12))
    ttk.Label(dyn_frame, text="Boundary").grid(row=0, column=6, sticky="w")
    boundary_var = tk.StringVar(value=str(settings.config.boundary))
    ttk.Combobox(dyn_frame, textvariable=boundary_var, values=["periodic", "open"], width=9).grid(
        row=0, column=7, sticky="w", padx=(6, 0)
    )

    ttk.Label(frm, text="Influence").grid(row=3, column=0, sticky="w")
    mode_var = tk.StringVar(value=getattr(settings, "influence_mode", "symbol"))
    ttk.Combobox(
        frm,
        textvariable=mode_var,
        values=["symbol", "joystick_field", "joystick_patch", "source_sink", "none"],
        width=16,
    ).grid(row=3, column=1, sticky="w", padx=(0, 12))
    ttk.Label(frm, text="Dur(steps)").grid(row=3, column=2, sticky="w")
    dur_var = tk.IntVar(value=int(getattr(settings, "influence_duration_steps", 0)))
    ttk.Entry(frm, textvariable=dur_var, width=12).grid(row=3, column=3, sticky="w", padx=(6, 12))

    ttk.Label(frm, text="Symbol").grid(row=4, column=0, sticky="w")
    symbol_var = tk.StringVar(value=settings.symbol_id)
    sym_box = ttk.Combobox(frm, textvariable=symbol_var, values=symbols, width=16)
    sym_box.grid(row=4, column=1, sticky="w", padx=(0, 12))

    ttk.Label(frm, text="Amp").grid(row=4, column=2, sticky="w")
    amp_var = tk.DoubleVar(value=settings.amplitude)
    ttk.Entry(frm, textvariable=amp_var, width=12).grid(row=4, column=3, sticky="w", padx=(6, 12))

    infl_frame = ttk.Frame(frm)
    infl_frame.grid(row=5, column=0, columnspan=4, sticky="we", pady=(2, 0))
    ttk.Label(infl_frame, text="Joy dx/dy").grid(row=0, column=0, sticky="w")
    joy_dx_var = tk.DoubleVar(value=float(getattr(settings, "joy_dx", 0.0)))
    joy_dy_var = tk.DoubleVar(value=float(getattr(settings, "joy_dy", 0.0)))
    ttk.Entry(infl_frame, textvariable=joy_dx_var, width=7).grid(row=0, column=1, sticky="w", padx=(6, 0))
    ttk.Entry(infl_frame, textvariable=joy_dy_var, width=7).grid(row=0, column=2, sticky="w", padx=(6, 12))

    ttk.Label(infl_frame, text="Patch cx/cy/r").grid(row=0, column=3, sticky="w")
    patch_cx_var = tk.IntVar(value=int(getattr(settings, "patch_cx", settings.config.width // 2)))
    patch_cy_var = tk.IntVar(value=int(getattr(settings, "patch_cy", settings.config.height // 2)))
    patch_r_var = tk.IntVar(value=int(getattr(settings, "patch_radius", max(1, max(settings.config.width, settings.config.height) // 8))))
    ttk.Entry(infl_frame, textvariable=patch_cx_var, width=5).grid(row=0, column=4, sticky="w", padx=(6, 0))
    ttk.Entry(infl_frame, textvariable=patch_cy_var, width=5).grid(row=0, column=5, sticky="w", padx=(6, 0))
    ttk.Entry(infl_frame, textvariable=patch_r_var, width=5).grid(row=0, column=6, sticky="w", padx=(6, 12))

    ttk.Label(infl_frame, text="Src(x,y)->Dst(x,y)").grid(row=1, column=0, sticky="w")
    src_x_var = tk.IntVar(value=int(getattr(settings, "source_x", 0)))
    src_y_var = tk.IntVar(value=int(getattr(settings, "source_y", 0)))
    dst_x_var = tk.IntVar(value=int(getattr(settings, "sink_x", 0)))
    dst_y_var = tk.IntVar(value=int(getattr(settings, "sink_y", 0)))
    ttk.Entry(infl_frame, textvariable=src_x_var, width=5).grid(row=1, column=1, sticky="w", padx=(6, 0))
    ttk.Entry(infl_frame, textvariable=src_y_var, width=5).grid(row=1, column=2, sticky="w", padx=(6, 12))
    ttk.Entry(infl_frame, textvariable=dst_x_var, width=5).grid(row=1, column=3, sticky="w", padx=(6, 0))
    ttk.Entry(infl_frame, textvariable=dst_y_var, width=5).grid(row=1, column=4, sticky="w", padx=(6, 12))
    ttk.Label(infl_frame, text="src/dst val").grid(row=1, column=5, sticky="w")
    src_v_var = tk.DoubleVar(value=float(getattr(settings, "source_value", 1.0)))
    dst_v_var = tk.DoubleVar(value=float(getattr(settings, "sink_value", 0.0)))
    ttk.Entry(infl_frame, textvariable=src_v_var, width=7).grid(row=1, column=6, sticky="w", padx=(6, 0))
    ttk.Entry(infl_frame, textvariable=dst_v_var, width=7).grid(row=1, column=7, sticky="w", padx=(6, 0))

    ttk.Label(frm, text="Ticks/step").grid(row=6, column=0, sticky="w")
    ticks_var = tk.IntVar(value=settings.ticks_per_step)
    ttk.Entry(frm, textvariable=ticks_var, width=8).grid(row=6, column=1, sticky="w")

    ttk.Label(frm, text="Interval (ms)").grid(row=6, column=2, sticky="w")
    interval_var = tk.IntVar(value=settings.tick_interval_ms)
    ttk.Entry(frm, textvariable=interval_var, width=12).grid(row=6, column=3, sticky="w", padx=(6, 12))

    record_var = tk.BooleanVar(value=settings.record_dir is not None)
    ttk.Checkbutton(frm, text="Record trace", variable=record_var).grid(row=7, column=0, sticky="w")
    out_var = tk.StringVar(value=str(settings.record_dir) if settings.record_dir else "runs/out/ui_run")
    ttk.Entry(frm, textvariable=out_var, width=38).grid(row=7, column=1, columnspan=3, sticky="we", padx=(6, 0))
    frm.columnconfigure(3, weight=1)

    fields_var = tk.BooleanVar(value=bool(getattr(settings, "record_fields", False)))
    ttk.Checkbutton(frm, text="fields_hist.npz", variable=fields_var).grid(row=7, column=3, sticky="e")

    inv_var = tk.StringVar(value=getattr(settings, "invariant_streams", ""))
    ttk.Label(frm, text="Invariant streams").grid(row=8, column=0, sticky="w")
    ttk.Entry(frm, textvariable=inv_var, width=52).grid(row=8, column=1, columnspan=3, sticky="we", padx=(6, 0))

    viz_enabled_var = tk.BooleanVar(value=settings.viz_enabled)
    ttk.Checkbutton(frm, text="Viz daemon", variable=viz_enabled_var).grid(row=9, column=0, sticky="w")
    viz_transport_var = tk.StringVar(value=settings.viz_transport)
    ttk.Combobox(frm, textvariable=viz_transport_var, values=["tcp", "none"], width=6).grid(
        row=9, column=1, sticky="w", padx=(6, 6)
    )
    viz_host_var = tk.StringVar(value=settings.viz_host)
    ttk.Entry(frm, textvariable=viz_host_var, width=14).grid(row=9, column=2, sticky="w", padx=(6, 6))
    viz_port_var = tk.IntVar(value=settings.viz_port)
    ttk.Entry(frm, textvariable=viz_port_var, width=8).grid(row=9, column=3, sticky="w")

    viz_connect_var = tk.BooleanVar(value=settings.viz_connect)
    ttk.Checkbutton(frm, text="connect", variable=viz_connect_var).grid(row=10, column=0, sticky="w")
    viz_every_var = tk.IntVar(value=settings.viz_every_steps)
    ttk.Entry(frm, textvariable=viz_every_var, width=6).grid(row=10, column=1, sticky="w", padx=(6, 6))
    ttk.Label(frm, text="every_steps").grid(row=10, column=2, sticky="w")

    status = tk.StringVar(value="Ready")
    ttk.Label(frm, textvariable=status).grid(row=11, column=0, columnspan=4, sticky="w")

    def _apply_settings_to_runner(reset: bool) -> None:
        base = settings.config.to_dict()
        dyn_cfg = dict(base.get("dynamics", {}))
        dyn_cfg.update(
            {
                "alpha": float(alpha_var.get()),
                "beta": float(beta_var.get()),
                "kappa": float(kappa_var.get()),
                "gamma": float(gamma_var.get()),
                "lambda_t": float(lambda_t_var.get()),
            }
        )
        cfg = DETMConfig.from_dict(
            {
                **base,
                "backend": backend_var.get().strip() or settings.config.backend,
                "device": device_var.get().strip() or settings.config.device,
                "width": int(w_var.get()),
                "height": int(h_var.get()),
                "boundary": boundary_var.get().strip() or settings.config.boundary,
                "dynamics": dyn_cfg,
            }
        )
        settings.config = cfg
        settings.seed = int(seed_var.get())
        settings.influence_mode = str(mode_var.get()).strip() or "symbol"
        settings.symbol_id = symbol_var.get()
        settings.amplitude = float(amp_var.get())
        settings.influence_duration_steps = int(dur_var.get())
        settings.joy_dx = float(joy_dx_var.get())
        settings.joy_dy = float(joy_dy_var.get())
        settings.patch_cx = int(patch_cx_var.get())
        settings.patch_cy = int(patch_cy_var.get())
        settings.patch_radius = int(patch_r_var.get())
        settings.source_x = int(src_x_var.get())
        settings.source_y = int(src_y_var.get())
        settings.sink_x = int(dst_x_var.get())
        settings.sink_y = int(dst_y_var.get())
        settings.source_value = float(src_v_var.get())
        settings.sink_value = float(dst_v_var.get())
        settings.ticks_per_step = int(ticks_var.get())
        settings.tick_interval_ms = int(interval_var.get())
        settings.record_dir = Path(out_var.get()) if record_var.get() else None
        settings.record_fields = bool(fields_var.get())
        settings.invariant_streams = str(inv_var.get()).strip()
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
        runner._configure_invariants()
        runner._configure_viz()

    def _update_status():
        st = runner.state
        sig = runner.last_observables
        dyn = settings.config.dynamics
        status.set(
            f"tick={st.step_count}  sig0..3={sig[:4]}  backend={settings.config.backend}/{settings.config.device}  "
            f"boundary={settings.config.boundary}  a,b,k,g,t="
            f"[{dyn.alpha:.3g},{dyn.beta:.3g},{dyn.kappa:.3g},{dyn.gamma:.3g},{dyn.lambda_t:.3g}]"
        )

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
    btns.grid(row=12, column=0, columnspan=4, sticky="w", pady=(6, 0))
    ttk.Button(btns, text="Reset", command=on_reset).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(btns, text="Step", command=on_step).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(btns, text="Run/Stop", command=on_run_toggle).grid(row=0, column=2, padx=(0, 6))

    def _on_close():
        runner.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    runner._configure_recording()
    runner._configure_invariants()
    runner._configure_viz()
    _update_status()
    root.mainloop()


__all__ = ["DetmTkRunner", "UiRunSettings", "launch_tk_ui"]
