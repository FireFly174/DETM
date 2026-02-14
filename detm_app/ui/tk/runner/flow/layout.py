"""Layout builders for Tk runner launcher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from detm_app.ui.tk.panel import DetmVizPanel


@dataclass(frozen=True)
class TkLauncherLayout:
    controls_frame: Any
    viz_panel_frame: Any
    viz_panel: Any
    log_frame: Any
    log_text: Any


def build_launcher_layout(*, root: Any, tk: Any, ttk: Any) -> TkLauncherLayout:
    controls_frame = ttk.Frame(root, padding=(10, 10, 6, 10))
    controls_frame.grid(row=0, column=0, sticky="nsw")

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
    return TkLauncherLayout(
        controls_frame=controls_frame,
        viz_panel_frame=viz_panel_frame,
        viz_panel=viz_panel,
        log_frame=log_frame,
        log_text=log_text,
    )


__all__ = ["TkLauncherLayout", "build_launcher_layout"]
