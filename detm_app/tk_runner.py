"""Lightweight Tkinter settings UI.

The UI is intentionally "controller-only": it does not render fields itself.
If visualization is enabled, it starts a separate viz daemon process and streams
serialized DETM state blobs to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from detm_app.bus import EventBus
from detm_app.coarsening import InvariantCoarsener, parse_invariant_streams
from detm_app.session import DetmSession
from detm_app.subscribers import (
    ArtifactWriter,
    CommitJsonlWriter,
    CommitValidationReporter,
    FieldHistoryRecorder,
    InvariantTickJsonlWriter,
    JsonlTraceWriter,
    WatchContractWriter,
    WatchTraceWriter,
    VizStreamer,
)
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.symbols import list_symbols, make_symbol
from detm_app.transport import VizTransport, open_viz_transport
from detm_app.tk_panel import DetmVizPanel
from detm_app.subscriber import TcpVizSubscriber
from detm_app.config_hints import load_tooltips_from_config_default
from detm_app.tooltips import attach_tooltip


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
    viz_transport: str = "embedded"  # embedded | tcp | none  /// транспорт визуализации
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
        self._watch_trace_writer: WatchTraceWriter | None = None
        self._watch_contract_writer: WatchContractWriter | None = None
        self._commit_writer: CommitJsonlWriter | None = None
        self._audit_commit_writer: CommitJsonlWriter | None = None
        self._commit_validation_reporter: CommitValidationReporter | None = None
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

    def _storage_policy(self, artifact: str) -> dict[str, int]:
        level_name = str(self.settings.config.level_policy.active_level or "L0")
        return self.settings.config.resolve_artifact_storage_policy(
            artifact=str(artifact),
            level=level_name,
        )

    def _disable_viz(self) -> None:
        if self._viz_streamer is not None:
            self._viz_streamer.detach()
            self._viz_streamer = None
        if self._viz_transport is not None:
            self._viz_transport.close()
            self._viz_transport = None
        self._viz_key = None

    def _configure_viz(self) -> None:
        transport = str(self.settings.viz_transport).lower().strip()
        if not bool(self.settings.viz_enabled) or transport in {"none", "embedded"}:
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
        if self._watch_trace_writer is not None:
            self._watch_trace_writer.on_close()
            self._watch_trace_writer = None
        if self._watch_contract_writer is not None:
            self._watch_contract_writer.on_close()
            self._watch_contract_writer = None
        if self._commit_writer is not None:
            self._commit_writer.on_close()
            self._commit_writer = None
        if self._audit_commit_writer is not None:
            self._audit_commit_writer.on_close()
            self._audit_commit_writer = None
        if self._commit_validation_reporter is not None:
            self._commit_validation_reporter.detach()
            self._commit_validation_reporter = None
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
        inv_policy = self._storage_policy("invariants")
        if self._invariant_writer is None:
            self._invariant_writer = InvariantTickJsonlWriter.attach(
                self._session.bus,
                desired_path,
                retention_window=int(inv_policy.get("retention_window", 0)),
                compaction_budget=int(inv_policy.get("compaction_budget", 0)),
            )
            return
        if self._invariant_writer.path.resolve() != desired_path.resolve():
            self._invariant_writer.on_close()
            self._invariant_writer = InvariantTickJsonlWriter.attach(
                self._session.bus,
                desired_path,
                retention_window=int(inv_policy.get("retention_window", 0)),
                compaction_budget=int(inv_policy.get("compaction_budget", 0)),
            )

    def _configure_recording(self) -> None:
        record_dir = self.settings.record_dir
        if record_dir is None:
            self._disable_recording()
            return

        record_dir = Path(record_dir)
        trace_policy = self._storage_policy("trace")
        watch_policy = self._storage_policy("watch_trace")
        watch_contract_policy = self._storage_policy("watch_contract")
        outerfields_policy = self._storage_policy("outerfields")
        commits_policy = self._storage_policy("commits")
        commits_audit_policy = self._storage_policy("commits_audit")
        commit_validation_policy = self._storage_policy("commit_validation")
        if self._trace_writer is None:
            self._trace_writer = JsonlTraceWriter.attach(
                self._session.bus,
                record_dir / "trace.jsonl",
                retention_window=int(trace_policy.get("retention_window", 0)),
                compaction_budget=int(trace_policy.get("compaction_budget", 0)),
            )
            if bool(self.settings.config.watch_trace_enabled):
                self._watch_trace_writer = WatchTraceWriter.attach(
                    self._session.bus,
                    record_dir / "watch_trace.jsonl",
                    retention_window=int(watch_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_policy.get("compaction_budget", 0)),
                )
                self._watch_contract_writer = WatchContractWriter.attach(
                    self._session.bus,
                    record_dir / "watch_contract.jsonl",
                    outerfields_dir=record_dir / "outerfields",
                    level_src=str(self.settings.config.level_policy.active_level or "L0"),
                    base_level="L0",
                    retention_window=int(watch_contract_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
                    outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
                    outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
                )
            self._commit_writer = CommitJsonlWriter.attach(
                self._session.bus,
                record_dir / "commits.jsonl",
                node_id=f"ui_seed_{int(self.settings.seed):04d}",
                mode="realtime",
                retention_window=int(commits_policy.get("retention_window", 0)),
                compaction_budget=int(commits_policy.get("compaction_budget", 0)),
            )
            if bool(self.settings.config.level_policy.audit_commit_enabled):
                self._audit_commit_writer = CommitJsonlWriter.attach(
                    self._session.bus,
                    record_dir / "commits_audit.jsonl",
                    node_id=f"ui_seed_{int(self.settings.seed):04d}",
                    commit_type="proof",
                    mode="audit",
                    retention_window=int(commits_audit_policy.get("retention_window", 0)),
                    compaction_budget=int(commits_audit_policy.get("compaction_budget", 0)),
                )
            self._commit_validation_reporter = CommitValidationReporter.attach(
                self._session.bus,
                record_dir,
                retention_window=int(commit_validation_policy.get("retention_window", 0)),
                compaction_budget=int(commit_validation_policy.get("compaction_budget", 0)),
            )
            self._configure_invariant_recording()
            self._artifact_writer = ArtifactWriter.attach(self._session.bus, record_dir)
            if bool(self.settings.record_fields):
                self._fields_recorder = FieldHistoryRecorder.attach(self._session.bus, record_dir / "fields_hist.npz")
            return

        if self._trace_writer.path.resolve() != (record_dir / "trace.jsonl").resolve():
            self._disable_recording()
            self._trace_writer = JsonlTraceWriter.attach(
                self._session.bus,
                record_dir / "trace.jsonl",
                retention_window=int(trace_policy.get("retention_window", 0)),
                compaction_budget=int(trace_policy.get("compaction_budget", 0)),
            )
            if bool(self.settings.config.watch_trace_enabled):
                self._watch_trace_writer = WatchTraceWriter.attach(
                    self._session.bus,
                    record_dir / "watch_trace.jsonl",
                    retention_window=int(watch_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_policy.get("compaction_budget", 0)),
                )
                self._watch_contract_writer = WatchContractWriter.attach(
                    self._session.bus,
                    record_dir / "watch_contract.jsonl",
                    outerfields_dir=record_dir / "outerfields",
                    level_src=str(self.settings.config.level_policy.active_level or "L0"),
                    base_level="L0",
                    retention_window=int(watch_contract_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
                    outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
                    outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
                )
            self._commit_writer = CommitJsonlWriter.attach(
                self._session.bus,
                record_dir / "commits.jsonl",
                node_id=f"ui_seed_{int(self.settings.seed):04d}",
                mode="realtime",
                retention_window=int(commits_policy.get("retention_window", 0)),
                compaction_budget=int(commits_policy.get("compaction_budget", 0)),
            )
            if bool(self.settings.config.level_policy.audit_commit_enabled):
                self._audit_commit_writer = CommitJsonlWriter.attach(
                    self._session.bus,
                    record_dir / "commits_audit.jsonl",
                    node_id=f"ui_seed_{int(self.settings.seed):04d}",
                    commit_type="proof",
                    mode="audit",
                    retention_window=int(commits_audit_policy.get("retention_window", 0)),
                    compaction_budget=int(commits_audit_policy.get("compaction_budget", 0)),
                )
            self._commit_validation_reporter = CommitValidationReporter.attach(
                self._session.bus,
                record_dir,
                retention_window=int(commit_validation_policy.get("retention_window", 0)),
                compaction_budget=int(commit_validation_policy.get("compaction_budget", 0)),
            )
            self._configure_invariant_recording()
            self._artifact_writer = ArtifactWriter.attach(self._session.bus, record_dir)
            if bool(self.settings.record_fields):
                self._fields_recorder = FieldHistoryRecorder.attach(self._session.bus, record_dir / "fields_hist.npz")
        else:
            watch_enabled = bool(self.settings.config.watch_trace_enabled)
            if watch_enabled and self._watch_trace_writer is None:
                self._watch_trace_writer = WatchTraceWriter.attach(
                    self._session.bus,
                    record_dir / "watch_trace.jsonl",
                    retention_window=int(watch_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_policy.get("compaction_budget", 0)),
                )
            if watch_enabled and self._watch_contract_writer is None:
                self._watch_contract_writer = WatchContractWriter.attach(
                    self._session.bus,
                    record_dir / "watch_contract.jsonl",
                    outerfields_dir=record_dir / "outerfields",
                    level_src=str(self.settings.config.level_policy.active_level or "L0"),
                    base_level="L0",
                    retention_window=int(watch_contract_policy.get("retention_window", 0)),
                    compaction_budget=int(watch_contract_policy.get("compaction_budget", 0)),
                    outerfields_retention_window=int(outerfields_policy.get("retention_window", 0)),
                    outerfields_compaction_budget=int(outerfields_policy.get("compaction_budget", 0)),
                )
            if (not watch_enabled) and self._watch_trace_writer is not None:
                self._watch_trace_writer.on_close()
                self._watch_trace_writer = None
            if (not watch_enabled) and self._watch_contract_writer is not None:
                self._watch_contract_writer.on_close()
                self._watch_contract_writer = None
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

    root = tk.Tk()
    root.title("DETM Runner")
    _install_clipboard_shortcuts(root)
    is_full = {"v": False}
    prev_geom = {"v": None}

    def _toggle_fullscreen(_e=None):
        is_full["v"] = not is_full["v"]
        if is_full["v"]:
            prev_geom["v"] = root.geometry()
            root.attributes("-fullscreen", True)
        else:
            root.attributes("-fullscreen", False)
            if prev_geom["v"]:
                root.geometry(prev_geom["v"])

    def _exit_fullscreen(_e=None):
        if is_full["v"]:
            _toggle_fullscreen()

    root.bind("<F11>", _toggle_fullscreen, add=True)
    root.bind("<Escape>", _exit_fullscreen, add=True)

    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)

    runner = DetmTkRunner(settings)
    tcp_subscriber: TcpVizSubscriber | None = None
    tcp_sub_key: tuple | None = None
    tcp_rendered_frames = 0

    symbols = ["(none)"] + list_symbols()

    frm = ttk.Frame(root, padding=(10, 10, 6, 10))
    frm.grid(row=0, column=0, sticky="nsw")


    viz_frame = ttk.Frame(root, padding=(6, 10, 10, 10))
    viz_frame.grid(row=0, column=1, sticky="nsew")
    viz_frame.columnconfigure(0, weight=1)
    viz_frame.rowconfigure(0, weight=1)
    viz_stack = ttk.Frame(viz_frame)
    viz_stack.grid(row=0, column=0, sticky="nsew")
    viz_stack.columnconfigure(0, weight=1)
    viz_stack.rowconfigure(0, weight=1)

    viz_panel_frame = ttk.Frame(viz_stack)
    viz_panel_frame.grid(row=0, column=0, sticky="nsew")
    viz_panel_frame.columnconfigure(0, weight=1)
    viz_panel_frame.rowconfigure(0, weight=1)

    viz_panel = DetmVizPanel(viz_panel_frame)
    viz_panel.status_mid.set("Viz: embedded")

    log_frame = ttk.Frame(viz_stack)
    log_frame.grid(row=0, column=0, sticky="nsew")
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    log_text = tk.Text(log_frame, height=24, wrap="word")
    log_text.grid(row=0, column=0, sticky="nsew")
    log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_scroll.grid(row=0, column=1, sticky="ns")
    log_text.configure(yscrollcommand=log_scroll.set)

    viz_panel_frame.tkraise()

    # Settings widgets
    tips = load_tooltips_from_config_default()

    ttk.Label(frm, text="Backend").grid(row=0, column=0, sticky="w")
    backend_var = tk.StringVar(value=settings.config.backend)
    backend_box = ttk.Combobox(frm, textvariable=backend_var, values=["torch", "numpy"], width=10)
    backend_box.grid(row=0, column=1, sticky="w", padx=(6, 12))
    attach_tooltip(backend_box, tips.get("backend", ""))

    ttk.Label(frm, text="Device").grid(row=0, column=2, sticky="w")
    device_var = tk.StringVar(value=settings.config.device)
    device_entry = ttk.Entry(frm, textvariable=device_var, width=12)
    device_entry.grid(row=0, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(device_entry, tips.get("device", ""))

    ttk.Label(frm, text="Lattice (W×H)").grid(row=1, column=0, sticky="w")
    w_var = tk.IntVar(value=settings.config.width)
    h_var = tk.IntVar(value=settings.config.height)
    w_entry = ttk.Entry(frm, textvariable=w_var, width=6)
    w_entry.grid(row=1, column=1, sticky="w")
    h_entry = ttk.Entry(frm, textvariable=h_var, width=6)
    h_entry.grid(row=1, column=1, sticky="e")
    attach_tooltip(w_entry, tips.get("width", ""))
    attach_tooltip(h_entry, tips.get("height", ""))

    ttk.Label(frm, text="Seed").grid(row=1, column=2, sticky="w")
    seed_var = tk.IntVar(value=settings.seed)
    seed_entry = ttk.Entry(frm, textvariable=seed_var, width=12)
    seed_entry.grid(row=1, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(seed_entry, tips.get("ui.seed", tips.get("seed", "")))

    dyn_frame = ttk.Frame(frm)
    dyn_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=(4, 0))
    dyn = settings.config.dynamics
    ttk.Label(dyn_frame, text="Dyn a,b,k,g,t").grid(row=0, column=0, sticky="w")
    alpha_var = tk.DoubleVar(value=float(dyn.alpha))
    beta_var = tk.DoubleVar(value=float(dyn.beta))
    kappa_var = tk.DoubleVar(value=float(dyn.kappa))
    gamma_var = tk.DoubleVar(value=float(dyn.gamma))
    lambda_t_var = tk.DoubleVar(value=float(dyn.lambda_t))
    alpha_entry = ttk.Entry(dyn_frame, textvariable=alpha_var, width=7)
    alpha_entry.grid(row=0, column=1, sticky="w", padx=(6, 0))
    beta_entry = ttk.Entry(dyn_frame, textvariable=beta_var, width=7)
    beta_entry.grid(row=0, column=2, sticky="w", padx=(6, 0))
    kappa_entry = ttk.Entry(dyn_frame, textvariable=kappa_var, width=7)
    kappa_entry.grid(row=0, column=3, sticky="w", padx=(6, 0))
    gamma_entry = ttk.Entry(dyn_frame, textvariable=gamma_var, width=7)
    gamma_entry.grid(row=0, column=4, sticky="w", padx=(6, 0))
    lambda_t_entry = ttk.Entry(dyn_frame, textvariable=lambda_t_var, width=7)
    lambda_t_entry.grid(row=0, column=5, sticky="w", padx=(6, 12))
    attach_tooltip(alpha_entry, tips.get("dynamics.alpha", ""))
    attach_tooltip(beta_entry, tips.get("dynamics.beta", ""))
    attach_tooltip(kappa_entry, tips.get("dynamics.kappa", ""))
    attach_tooltip(gamma_entry, tips.get("dynamics.gamma", ""))
    attach_tooltip(lambda_t_entry, tips.get("dynamics.lambda_t", ""))
    ttk.Label(dyn_frame, text="Boundary").grid(row=0, column=6, sticky="w")
    boundary_var = tk.StringVar(value=str(settings.config.boundary))
    boundary_box = ttk.Combobox(dyn_frame, textvariable=boundary_var, values=["periodic", "open"], width=9)
    boundary_box.grid(row=0, column=7, sticky="w", padx=(6, 0))
    attach_tooltip(boundary_box, tips.get("boundary", ""))

    ttk.Label(frm, text="Influence").grid(row=3, column=0, sticky="w")
    mode_var = tk.StringVar(value=getattr(settings, "influence_mode", "symbol"))
    mode_box = ttk.Combobox(
        frm,
        textvariable=mode_var,
        values=["symbol", "joystick_field", "joystick_patch", "source_sink", "none"],
        width=16,
    )
    mode_box.grid(row=3, column=1, sticky="w", padx=(0, 12))
    attach_tooltip(mode_box, tips.get("ui.influence_mode", ""))
    ttk.Label(frm, text="Dur(steps)").grid(row=3, column=2, sticky="w")
    dur_var = tk.IntVar(value=int(getattr(settings, "influence_duration_steps", 0)))
    dur_entry = ttk.Entry(frm, textvariable=dur_var, width=12)
    dur_entry.grid(row=3, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(dur_entry, tips.get("ui.influence_duration_steps", ""))

    ttk.Label(frm, text="Symbol").grid(row=4, column=0, sticky="w")
    symbol_var = tk.StringVar(value=settings.symbol_id)
    sym_box = ttk.Combobox(frm, textvariable=symbol_var, values=symbols, width=16)
    sym_box.grid(row=4, column=1, sticky="w", padx=(0, 12))
    attach_tooltip(sym_box, tips.get("ui.symbol_id", ""))

    ttk.Label(frm, text="Amp").grid(row=4, column=2, sticky="w")
    amp_var = tk.DoubleVar(value=settings.amplitude)
    amp_entry = ttk.Entry(frm, textvariable=amp_var, width=12)
    amp_entry.grid(row=4, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(amp_entry, tips.get("ui.amplitude", ""))

    infl_frame = ttk.Frame(frm)
    infl_frame.grid(row=5, column=0, columnspan=4, sticky="we", pady=(2, 0))
    ttk.Label(infl_frame, text="Joy dx/dy").grid(row=0, column=0, sticky="w")
    joy_dx_var = tk.DoubleVar(value=float(getattr(settings, "joy_dx", 0.0)))
    joy_dy_var = tk.DoubleVar(value=float(getattr(settings, "joy_dy", 0.0)))
    joy_dx_entry = ttk.Entry(infl_frame, textvariable=joy_dx_var, width=7)
    joy_dx_entry.grid(row=0, column=1, sticky="w", padx=(6, 0))
    joy_dy_entry = ttk.Entry(infl_frame, textvariable=joy_dy_var, width=7)
    joy_dy_entry.grid(row=0, column=2, sticky="w", padx=(6, 12))
    attach_tooltip(joy_dx_entry, tips.get("ui.joy_dx", ""))
    attach_tooltip(joy_dy_entry, tips.get("ui.joy_dy", ""))

    ttk.Label(infl_frame, text="Patch cx/cy/r").grid(row=0, column=3, sticky="w")
    patch_cx_var = tk.IntVar(value=int(getattr(settings, "patch_cx", settings.config.width // 2)))
    patch_cy_var = tk.IntVar(value=int(getattr(settings, "patch_cy", settings.config.height // 2)))
    patch_r_var = tk.IntVar(value=int(getattr(settings, "patch_radius", max(1, max(settings.config.width, settings.config.height) // 8))))
    patch_cx_entry = ttk.Entry(infl_frame, textvariable=patch_cx_var, width=5)
    patch_cx_entry.grid(row=0, column=4, sticky="w", padx=(6, 0))
    patch_cy_entry = ttk.Entry(infl_frame, textvariable=patch_cy_var, width=5)
    patch_cy_entry.grid(row=0, column=5, sticky="w", padx=(6, 0))
    patch_r_entry = ttk.Entry(infl_frame, textvariable=patch_r_var, width=5)
    patch_r_entry.grid(row=0, column=6, sticky="w", padx=(6, 12))
    attach_tooltip(patch_cx_entry, tips.get("ui.patch_cx", ""))
    attach_tooltip(patch_cy_entry, tips.get("ui.patch_cy", ""))
    attach_tooltip(patch_r_entry, tips.get("ui.patch_radius", ""))

    ttk.Label(infl_frame, text="Src(x,y)->Dst(x,y)").grid(row=1, column=0, sticky="w")
    src_x_var = tk.IntVar(value=int(getattr(settings, "source_x", 0)))
    src_y_var = tk.IntVar(value=int(getattr(settings, "source_y", 0)))
    dst_x_var = tk.IntVar(value=int(getattr(settings, "sink_x", 0)))
    dst_y_var = tk.IntVar(value=int(getattr(settings, "sink_y", 0)))
    src_x_entry = ttk.Entry(infl_frame, textvariable=src_x_var, width=5)
    src_x_entry.grid(row=1, column=1, sticky="w", padx=(6, 0))
    src_y_entry = ttk.Entry(infl_frame, textvariable=src_y_var, width=5)
    src_y_entry.grid(row=1, column=2, sticky="w", padx=(6, 12))
    dst_x_entry = ttk.Entry(infl_frame, textvariable=dst_x_var, width=5)
    dst_x_entry.grid(row=1, column=3, sticky="w", padx=(6, 0))
    dst_y_entry = ttk.Entry(infl_frame, textvariable=dst_y_var, width=5)
    dst_y_entry.grid(row=1, column=4, sticky="w", padx=(6, 12))
    attach_tooltip(src_x_entry, tips.get("ui.source_x", ""))
    attach_tooltip(src_y_entry, tips.get("ui.source_y", ""))
    attach_tooltip(dst_x_entry, tips.get("ui.sink_x", ""))
    attach_tooltip(dst_y_entry, tips.get("ui.sink_y", ""))
    ttk.Label(infl_frame, text="src/dst val").grid(row=1, column=5, sticky="w")
    src_v_var = tk.DoubleVar(value=float(getattr(settings, "source_value", 1.0)))
    dst_v_var = tk.DoubleVar(value=float(getattr(settings, "sink_value", 0.0)))
    src_v_entry = ttk.Entry(infl_frame, textvariable=src_v_var, width=7)
    src_v_entry.grid(row=1, column=6, sticky="w", padx=(6, 0))
    dst_v_entry = ttk.Entry(infl_frame, textvariable=dst_v_var, width=7)
    dst_v_entry.grid(row=1, column=7, sticky="w", padx=(6, 0))
    attach_tooltip(src_v_entry, tips.get("ui.source_value", ""))
    attach_tooltip(dst_v_entry, tips.get("ui.sink_value", ""))

    ttk.Label(frm, text="Ticks/step").grid(row=6, column=0, sticky="w")
    ticks_var = tk.IntVar(value=settings.ticks_per_step)
    ticks_entry = ttk.Entry(frm, textvariable=ticks_var, width=8)
    ticks_entry.grid(row=6, column=1, sticky="w")
    attach_tooltip(ticks_entry, tips.get("ui.ticks_per_step", tips.get("ticks_per_step", "")))

    ttk.Label(frm, text="Interval (ms)").grid(row=6, column=2, sticky="w")
    interval_var = tk.IntVar(value=settings.tick_interval_ms)
    interval_entry = ttk.Entry(frm, textvariable=interval_var, width=12)
    interval_entry.grid(row=6, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(interval_entry, tips.get("ui.tick_interval_ms", tips.get("tick_interval_ms", "")))

    record_var = tk.BooleanVar(value=settings.record_dir is not None)
    ttk.Checkbutton(frm, text="Record trace", variable=record_var).grid(row=7, column=0, sticky="w")
    out_var = tk.StringVar(value=str(settings.record_dir) if settings.record_dir else "runs/out/ui_run")
    out_entry = ttk.Entry(frm, textvariable=out_var, width=38)
    out_entry.grid(row=7, column=1, columnspan=3, sticky="we", padx=(6, 0))
    attach_tooltip(out_entry, tips.get("ui.record_dir", tips.get("record_dir", "")))
    frm.columnconfigure(3, weight=1)

    fields_var = tk.BooleanVar(value=bool(getattr(settings, "record_fields", False)))
    fields_chk = ttk.Checkbutton(frm, text="fields_hist.npz", variable=fields_var)
    fields_chk.grid(row=7, column=3, sticky="e")
    attach_tooltip(fields_chk, tips.get("ui.record_fields", tips.get("record_fields", "")))

    inv_var = tk.StringVar(value=getattr(settings, "invariant_streams", ""))
    ttk.Label(frm, text="Invariant streams").grid(row=8, column=0, sticky="w")
    inv_entry = ttk.Entry(frm, textvariable=inv_var, width=52)
    inv_entry.grid(row=8, column=1, columnspan=3, sticky="we", padx=(6, 0))
    attach_tooltip(inv_entry, tips.get("ui.invariant_streams", tips.get("invariant_streams", "")))

    viz_enabled_var = tk.BooleanVar(value=settings.viz_enabled)
    viz_chk = ttk.Checkbutton(frm, text="Viz", variable=viz_enabled_var)
    viz_chk.grid(row=9, column=0, sticky="w")
    attach_tooltip(viz_chk, tips.get("ui.viz_enabled", tips.get("viz_enabled", "")))
    viz_transport_var = tk.StringVar(value=settings.viz_transport)
    viz_transport_box = ttk.Combobox(frm, textvariable=viz_transport_var, values=["embedded", "tcp", "none"], width=9)
    viz_transport_box.grid(row=9, column=1, sticky="w", padx=(6, 6))
    attach_tooltip(viz_transport_box, tips.get("ui.viz_transport", tips.get("viz_transport", "")))
    viz_host_var = tk.StringVar(value=settings.viz_host)
    viz_host_entry = ttk.Entry(frm, textvariable=viz_host_var, width=14)
    viz_host_entry.grid(row=9, column=2, sticky="w", padx=(6, 6))
    attach_tooltip(viz_host_entry, tips.get("ui.viz_host", tips.get("viz_host", "")))
    viz_port_var = tk.IntVar(value=settings.viz_port)
    viz_port_entry = ttk.Entry(frm, textvariable=viz_port_var, width=8)
    viz_port_entry.grid(row=9, column=3, sticky="w")
    attach_tooltip(viz_port_entry, tips.get("ui.viz_port", tips.get("viz_port", "")))

    viz_connect_var = tk.BooleanVar(value=settings.viz_connect)
    viz_connect_chk = ttk.Checkbutton(frm, text="connect", variable=viz_connect_var)
    viz_connect_chk.grid(row=10, column=0, sticky="w")
    attach_tooltip(viz_connect_chk, tips.get("ui.viz_connect", tips.get("viz_connect", "")))
    viz_every_var = tk.IntVar(value=settings.viz_every_steps)
    viz_every_entry = ttk.Entry(frm, textvariable=viz_every_var, width=6)
    viz_every_entry.grid(row=10, column=1, sticky="w", padx=(6, 6))
    attach_tooltip(viz_every_entry, tips.get("ui.viz_every_steps", tips.get("viz_every_steps", "")))
    ttk.Label(frm, text="every_steps").grid(row=10, column=2, sticky="w")

    ttk.Label(frm, text="Mode").grid(row=11, column=0, sticky="w")
    ui_mode_var = tk.StringVar(value="interactive")
    ui_mode_box = ttk.Combobox(
        frm, textvariable=ui_mode_var, values=["interactive", "batch"], width=12, state="readonly"
    )
    ui_mode_box.grid(row=11, column=1, sticky="w", padx=(6, 0))

    status = tk.StringVar(value="Ready")
    ttk.Label(frm, textvariable=status).grid(row=12, column=0, columnspan=4, sticky="w")

    def _build_config_from_widgets() -> DETMConfig:
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
        return cfg

    def _apply_settings_to_runner(reset: bool) -> None:
        settings.config = _build_config_from_widgets()
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
        settings.viz_transport = str(viz_transport_var.get()).strip() or "embedded"
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

    def _disable_tcp_viz_subscriber() -> None:
        nonlocal tcp_subscriber, tcp_sub_key, tcp_rendered_frames
        if tcp_subscriber is not None:
            try:
                tcp_subscriber.close()
            except Exception:
                pass
            tcp_subscriber = None
        tcp_sub_key = None
        tcp_rendered_frames = 0

    def _configure_tcp_viz_subscriber() -> None:
        nonlocal tcp_subscriber, tcp_sub_key, tcp_rendered_frames
        if not bool(settings.viz_enabled):
            _disable_tcp_viz_subscriber()
            return
        transport_name = str(settings.viz_transport).strip().lower() or "embedded"
        if transport_name != "tcp":
            _disable_tcp_viz_subscriber()
            return

        host = str(settings.viz_host).strip() or "127.0.0.1"
        port = int(settings.viz_port)

        # If we're running a local daemon (port=0), extract the actual address from the transport.
        if port <= 0 and getattr(runner, "_viz_transport", None) is not None:
            try:
                vt = getattr(runner, "_viz_transport")
                if hasattr(vt, "address"):
                    host, port = vt.address  # type: ignore[misc]
            except Exception:
                pass

        key = ("tcp", host, int(port))
        if tcp_sub_key == key and tcp_subscriber is not None:
            return

        _disable_tcp_viz_subscriber()
        if int(port) <= 0:
            return
        try:
            tcp_subscriber = TcpVizSubscriber(host, int(port))
            tcp_sub_key = key
            tcp_rendered_frames = 0
        except Exception:
            tcp_subscriber = None
            tcp_sub_key = None
            tcp_rendered_frames = 0

    def _update_status():
        st = runner.state
        sig = runner.last_observables
        dyn = settings.config.dynamics
        status.set(
            f"tick={st.step_count}  sig0..3={sig[:4]}  backend={settings.config.backend}/{settings.config.device}  "
            f"boundary={settings.config.boundary}  a,b,k,g,t="
            f"[{dyn.alpha:.3g},{dyn.beta:.3g},{dyn.kappa:.3g},{dyn.gamma:.3g},{dyn.lambda_t:.3g}]"
        )

    last_embedded_step = -1
    embedded_draws = 0
    embedded_fps_ema = 0.0
    embedded_window_start = 0.0
    embedded_window_count = 0

    def _maybe_update_embedded_viz(*, force: bool = False) -> None:
        nonlocal last_embedded_step, embedded_draws, embedded_fps_ema, embedded_window_start, embedded_window_count
        if not bool(settings.viz_enabled):
            viz_panel.status_var.set("Viz: disabled")
            return
        transport = str(settings.viz_transport).strip().lower() or "embedded"
        if transport != "embedded":
            viz_panel.status_var.set(f"Viz: {transport}")
            return
        step = int(runner.state.step_count)
        every = max(1, int(getattr(settings, "viz_every_steps", 1) or 1))
        if not force and last_embedded_step >= 0 and (step - last_embedded_step) < every:
            return
        last_embedded_step = step
        try:
            signature = list(runner.last_observables) if runner.last_observables is not None else None
            viz_panel.update_from_state(state=runner.state, tick=step, signature=signature)
            embedded_draws += 1
            now = __import__("time").perf_counter()
            if embedded_window_start <= 0.0:
                embedded_window_start = now
                embedded_window_count = 0
            embedded_window_count += 1
            dt = now - embedded_window_start
            if dt >= 0.5:
                fps = float(embedded_window_count) / max(1e-9, dt)
                embedded_fps_ema = 0.85 * float(embedded_fps_ema) + 0.15 * fps
                embedded_window_start = now
                embedded_window_count = 0
            viz_panel.status_var.set(viz_panel.status_var.get() + f"  embedded={embedded_draws}~{embedded_fps_ema:.1f}fps")
        except Exception as exc:
            viz_panel.status_var.set(f"Viz: error ({exc})")

    def _maybe_update_tcp_viz() -> None:
        nonlocal tcp_rendered_frames
        if not bool(settings.viz_enabled):
            viz_panel.status_var.set("Viz: disabled")
            return
        transport = str(settings.viz_transport).strip().lower() or "embedded"
        if transport != "tcp":
            return
        _configure_tcp_viz_subscriber()
        if tcp_subscriber is None:
            viz_panel.status_var.set("Viz: tcp (no connection)")
            return
        pkt = tcp_subscriber.poll_latest()
        if pkt is None:
            # Still show that we're connected.
            viz_panel.status_var.set(
                f"Viz: tcp (recv={tcp_subscriber.recv_frames}, rendered={tcp_rendered_frames})"
            )
            return
        try:
            viz_panel.update_from_state_blob(
                state_blob=pkt.state_blob,
                tick=int(pkt.tick),
                signature=pkt.signature,
            )
            tcp_rendered_frames += 1
            sent = None
            vt = getattr(runner, "_viz_transport", None)
            if vt is not None and hasattr(vt, "sent_frames"):
                sent = int(getattr(vt, "sent_frames"))
            if sent is not None:
                viz_panel.status_var.set(
                    viz_panel.status_var.get()
                    + f"  tcp sent={sent}~{getattr(vt,'sent_fps_ema',0.0):.1f}fps"
                    + f" recv={tcp_subscriber.recv_frames}~{tcp_subscriber.recv_fps_ema:.1f}fps"
                    + f" rendered={tcp_rendered_frames}"
                )
            else:
                viz_panel.status_var.set(
                    viz_panel.status_var.get()
                    + f"  tcp recv={tcp_subscriber.recv_frames}~{tcp_subscriber.recv_fps_ema:.1f}fps"
                    + f" rendered={tcp_rendered_frames}"
                )
        except Exception as exc:
            viz_panel.status_var.set(f"Viz: tcp error ({exc})")

    def _tick():
        if runner.is_running():
            runner.step_once()
            _update_status()
            _maybe_update_embedded_viz()
            _maybe_update_tcp_viz()
            root.after(max(1, settings.tick_interval_ms), _tick)

    def on_reset():
        _apply_settings_to_runner(reset=True)
        _update_status()
        _maybe_update_embedded_viz(force=True)
        _maybe_update_tcp_viz()

    def on_step():
        _apply_settings_to_runner(reset=False)
        runner.step_once()
        _update_status()
        _maybe_update_embedded_viz(force=True)
        _maybe_update_tcp_viz()

    def on_run_toggle():
        _apply_settings_to_runner(reset=False)
        if runner.is_running():
            runner.stop()
        else:
            runner.start()
            _tick()

    btns = ttk.Frame(frm)
    btns.grid(row=13, column=0, columnspan=4, sticky="w", pady=(6, 0))
    ttk.Button(btns, text="Reset", command=on_reset).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(btns, text="Step", command=on_step).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(btns, text="Run/Stop", command=on_run_toggle).grid(row=0, column=2, padx=(0, 6))

    batch_frame = ttk.LabelFrame(frm, text="Batch", padding=8)
    batch_frame.grid(row=14, column=0, columnspan=4, sticky="we", pady=(8, 0))
    batch_frame.grid_remove()

    batch_n_var = tk.IntVar(value=10)
    batch_seed0_var = tk.IntVar(value=0)
    batch_steps_var = tk.IntVar(value=4)
    batch_symbols_var = tk.StringVar(value="")
    batch_out_var = tk.StringVar(value="runs/out/batch_ui")
    batch_record_fields_var = tk.BooleanVar(value=False)
    batch_fields_every_var = tk.IntVar(value=1)

    ttk.Label(batch_frame, text="N").grid(row=0, column=0, sticky="w")
    ttk.Entry(batch_frame, textvariable=batch_n_var, width=6).grid(row=0, column=1, sticky="w", padx=(6, 12))
    ttk.Label(batch_frame, text="seed0").grid(row=0, column=2, sticky="w")
    ttk.Entry(batch_frame, textvariable=batch_seed0_var, width=8).grid(row=0, column=3, sticky="w", padx=(6, 12))
    ttk.Label(batch_frame, text="ticks/symbol").grid(row=0, column=4, sticky="w")
    ttk.Entry(batch_frame, textvariable=batch_steps_var, width=8).grid(row=0, column=5, sticky="w", padx=(6, 0))

    ttk.Label(batch_frame, text="symbols").grid(row=1, column=0, sticky="w", pady=(6, 0))
    ttk.Entry(batch_frame, textvariable=batch_symbols_var, width=42).grid(
        row=1, column=1, columnspan=5, sticky="we", padx=(6, 0), pady=(6, 0)
    )
    ttk.Label(batch_frame, text="out").grid(row=2, column=0, sticky="w", pady=(6, 0))
    ttk.Entry(batch_frame, textvariable=batch_out_var, width=42).grid(
        row=2, column=1, columnspan=5, sticky="we", padx=(6, 0), pady=(6, 0)
    )
    ttk.Checkbutton(batch_frame, text="fields_hist.npz", variable=batch_record_fields_var).grid(
        row=3, column=0, sticky="w", pady=(6, 0)
    )
    ttk.Label(batch_frame, text="every").grid(row=3, column=2, sticky="w", pady=(6, 0))
    ttk.Entry(batch_frame, textvariable=batch_fields_every_var, width=6).grid(
        row=3, column=3, sticky="w", padx=(6, 0), pady=(6, 0)
    )

    batch_running = False
    batch_cancel = None
    batch_queue = None

    def _log(msg: str) -> None:
        log_text.insert("end", msg.rstrip() + "\n")
        log_text.see("end")

    def _show_viz_view(view: str) -> None:
        if view == "log":
            log_frame.tkraise()
        else:
            viz_panel_frame.tkraise()

    def _poll_batch_queue() -> None:
        nonlocal batch_running, batch_queue
        if batch_queue is None:
            return
        try:
            while True:
                item = batch_queue.get_nowait()
                if item is None:
                    batch_running = False
                    return
                _log(str(item))
        except Exception:
            pass
        root.after(75, _poll_batch_queue)

    def _parse_symbols(text: str) -> list[str]:
        raw = [c.strip() for c in (text or "").split(",") if c.strip()]
        if not raw:
            return list_symbols()
        known = set(list_symbols())
        out = []
        for sid in raw:
            if sid not in known:
                raise ValueError(f"Unknown symbol_id: {sid}")
            out.append(sid)
        return out

    def on_batch_toggle() -> None:
        nonlocal batch_running, batch_cancel, batch_queue
        if batch_running:
            if batch_cancel is not None:
                batch_cancel.set()
            _log("[cancel] requested")
            return

        import queue as _queue
        import threading as _threading
        from detm_app.cli import run_headless

        try:
            cfg = _build_config_from_widgets()
            symbol_ids = _parse_symbols(batch_symbols_var.get())
            n = max(1, int(batch_n_var.get()))
            seed0 = int(batch_seed0_var.get())
            steps = max(1, int(batch_steps_var.get()))
            out_root = Path(batch_out_var.get() or "runs/out/batch_ui")
            fields_npz = bool(batch_record_fields_var.get())
            fields_every = max(1, int(batch_fields_every_var.get()))
            invariant_streams = [s.strip() for s in str(inv_var.get() or "").split(",") if s.strip()] or None
        except Exception as exc:
            _show_viz_view("log")
            _log(f"[error] {exc}")
            return

        _show_viz_view("log")
        log_text.delete("1.0", "end")
        _log(f"[batch] n={n} seed0={seed0} steps={steps} symbols={len(symbol_ids)} out={out_root}")

        batch_running = True
        batch_cancel = _threading.Event()
        batch_queue = _queue.Queue()

        def _worker():
            assert batch_queue is not None
            assert batch_cancel is not None
            for i in range(n):
                if batch_cancel.is_set():
                    batch_queue.put("[batch] canceled")
                    break
                seed = seed0 + i
                batch_queue.put(f"[run] seed={seed}")
                try:
                    run_headless(
                        cfg,
                        int(seed),
                        symbol_ids,
                        int(steps),
                        Path(out_root) / f"seed_{int(seed):04d}",
                        None,
                        fields_npz=fields_npz,
                        fields_every_steps=int(fields_every),
                        invariant_streams=invariant_streams,
                    )
                    batch_queue.put(f"[ok] seed={seed}")
                except Exception as exc:
                    batch_queue.put(f"[error] seed={seed} {exc}")
                    break
            batch_queue.put(None)

        _threading.Thread(target=_worker, daemon=True).start()
        root.after(75, _poll_batch_queue)

    batch_btns = ttk.Frame(batch_frame)
    batch_btns.grid(row=4, column=0, columnspan=6, sticky="w", pady=(8, 0))
    ttk.Button(batch_btns, text="Run/Stop batch", command=on_batch_toggle).grid(row=0, column=0, padx=(0, 6))

    def _on_mode_change(*_args: object) -> None:
        mode = str(ui_mode_var.get()).strip().lower()
        if mode == "batch":
            runner.stop()
            btns.grid_remove()
            batch_frame.grid()
            _show_viz_view("log")
        else:
            batch_frame.grid_remove()
            btns.grid()
            _show_viz_view("viz")
            _maybe_update_embedded_viz(force=True)
            _maybe_update_tcp_viz()

    ui_mode_var.trace_add("write", _on_mode_change)

    def _on_close():
        _disable_tcp_viz_subscriber()
        runner.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    runner._configure_recording()
    runner._configure_invariants()
    runner._configure_viz()
    _update_status()
    _maybe_update_embedded_viz(force=True)
    _maybe_update_tcp_viz()
    root.mainloop()


__all__ = ["DetmTkRunner", "UiRunSettings", "launch_tk_ui"]
