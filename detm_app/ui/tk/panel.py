"""Embedded Tk visualization panel for DETM.

Used by:
- `detm_app.transport.daemon` (TCP daemon UI)
- `detm_app.ui.tk.runner` (single-window embedded viz)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


from detm.runtime.serialization import deserialize_state
from detm_app.ui.tk import panel_flow as _flow


def _to_numpy(array: Any) -> np.ndarray:
    return _flow.to_numpy(array)


def _to_image_gray(arr: np.ndarray) -> np.ndarray:
    return _flow.to_image_gray(arr)


def _cmap_color(v: float, mode: str) -> str:
    return _flow.cmap_color(v, mode)


def _central_grad(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return _flow.central_grad(arr)


@dataclass
class VizFrame:
    tick: int
    state_blob: bytes
    signature: Optional[list[float]] = None
    meta: Optional[Dict[str, Any]] = None


class DetmVizPanel:
    def __init__(self, parent) -> None:  # pragma: no cover (UI)
        import tkinter as tk
        from tkinter import ttk

        from tkinter import font as tkfont
        self._tk = tk
        self._ttk = ttk
        self._parent = parent

        self._rects: list[list[int]] = []
        self._arrows: list[int] = []
        self._cell_w = 1
        self._cell_h = 1
        self._w = 0
        self._h = 0
        self._canvas_w = 0
        self._canvas_h = 0
        self._last_field: np.ndarray | None = None
        self._off_x = 0.0
        self._off_y = 0.0

        status = ttk.Frame(parent)
        status.grid(row=0, column=0, sticky="we")
        status.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="")  # alias, will be kept in sync 


        fixed = tkfont.nametofont("TkFixedFont")

        self.status_left = tk.StringVar(value="tick=0")
        self.status_mid = tk.StringVar(value="lattice=?x?")
        self.status_right = tk.StringVar(value="field=energy")

        ttk.Label(status, textvariable=self.status_left, font=fixed).grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.status_mid,  font=fixed).grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Label(status, textvariable=self.status_right, font=fixed).grid(row=0, column=2, sticky="w", padx=(12, 0))

        controls = ttk.Frame(parent)
        controls.grid(row=1, column=0, sticky="we", pady=(6, 0))
        controls.columnconfigure(9, weight=1)

        self.field_var = tk.StringVar(value="energy")
        ttk.Label(controls, text="Field").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.field_var,
            values=["energy", "entropy", "internal_time"],
            width=14,
            state="readonly",
        ).grid(row=0, column=1, sticky="w", padx=(6, 12))

        self.cmap_var = tk.StringVar(value="heat")
        ttk.Label(controls, text="Cmap").grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.cmap_var,
            values=["gray", "heat"],
            width=8,
            state="readonly",
        ).grid(row=0, column=3, sticky="w", padx=(6, 12))

        self.quiver_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Quiver", variable=self.quiver_var).grid(row=0, column=4, sticky="w")

        self.q_step_var = tk.IntVar(value=2)
        ttk.Label(controls, text="step").grid(row=0, column=5, sticky="w", padx=(8, 2))
        ttk.Entry(controls, textvariable=self.q_step_var, width=4).grid(row=0, column=6, sticky="w", padx=(2, 12))

        self.q_scale_var = tk.DoubleVar(value=0.8)
        ttk.Label(controls, text="scale").grid(row=0, column=7, sticky="w", padx=(0, 2))
        ttk.Entry(controls, textvariable=self.q_scale_var, width=6).grid(row=0, column=8, sticky="w", padx=(2, 0))

        # self.canvas = tk.Canvas(parent, width=520, height=520, bg="#000000", highlightthickness=1)
        # self.canvas.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        self.nb = ttk.Notebook(parent)
        self.nb.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        parent.rowconfigure(2, weight=1)
        parent.columnconfigure(0, weight=1)

        tab_field = ttk.Frame(self.nb)
        tab_plot = ttk.Frame(self.nb)
        self.nb.add(tab_field, text="Field")
        self.nb.add(tab_plot, text="Graph")

        # --- Field tab ---
        tab_field.rowconfigure(0, weight=1)
        tab_field.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(tab_field, bg="#000000", highlightthickness=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Graph tab: show runtime learning/readout summary.
        tab_plot.rowconfigure(0, weight=1)
        tab_plot.columnconfigure(0, weight=1)
        self.learning_text = tk.Text(tab_plot, height=14, wrap="word", state="disabled")
        self.learning_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.canvas.bind("<Configure>", self._on_canvas_configure, add=True)

        parent.rowconfigure(2, weight=1)
        parent.columnconfigure(0, weight=1)

        self.canvas.bind("<Configure>", self._on_canvas_configure, add=True)

    def _ensure_grid(self, h: int, w: int) -> None:
        _flow.ensure_grid(self, h=int(h), w=int(w))

    def _sync_status_var(self) -> None:
        try:
            self.status_var.set(
                f"{self.status_left.get()}  {self.status_mid.get()}  {self.status_right.get()}"
            )
        except Exception:
            pass

    def _on_canvas_configure(self, event) -> None:
        _flow.on_canvas_configure(self, event=event)

    def _layout_grid(self) -> None:
        _flow.layout_grid(self)


    def _draw_quiver(self, arr: np.ndarray) -> None:
        _flow.draw_quiver(self, arr)

    def update_learning_text(self, text: str) -> None:
        payload = str(text or "")
        if not hasattr(self, "learning_text"):
            return
        try:
            self.learning_text.configure(state="normal")
            self.learning_text.delete("1.0", "end")
            self.learning_text.insert("1.0", payload.rstrip() + "\n")
            self.learning_text.configure(state="disabled")
        except Exception:
            return

    def update_from_state_blob(self, *, state_blob: bytes, tick: int, signature: Optional[list[float]] = None) -> None:
        state = deserialize_state(state_blob)
        mode = str(self.field_var.get()).strip().lower() or "energy"
        field = _flow.field_from_state(state=state, mode=mode)
        projection_suffix = _flow.projection_status_from_state(state=state)

        lattice = state.lattice
        self._ensure_grid(int(lattice.height), int(lattice.width))
        self._last_field = field
        cmap = str(self.cmap_var.get()).strip().lower() or "heat"
        _flow.paint_field(self, field=field, cmap=cmap)

        self._draw_quiver(field)
        sig_preview = f" sig0..3={signature[:4]}" if signature else ""
        self.status_left.set(f"tick={int(tick)}")
        self.status_mid.set(f"lattice={lattice.width}x{lattice.height}")
        self.status_right.set(f"field={mode}{projection_suffix}{sig_preview}")
        self._sync_status_var()


    def update_from_state(self, *, state: Any, tick: int, signature: Optional[list[float]] = None) -> None:
        mode = str(self.field_var.get()).strip().lower() or "energy"
        field = _flow.field_from_state(state=state, mode=mode)
        projection_suffix = _flow.projection_status_from_state(state=state)
        lattice = getattr(state, "lattice")

        self._ensure_grid(int(lattice.height), int(lattice.width))
        self._last_field = field
        cmap = str(self.cmap_var.get()).strip().lower() or "heat"
        _flow.paint_field(self, field=field, cmap=cmap)

        self._draw_quiver(field)
        sig_preview = f" sig0..3={signature[:4]}" if signature else ""
        self.status_left.set(f"tick={int(tick)}")
        self.status_mid.set(f"lattice={lattice.width}x{lattice.height}")
        self.status_right.set(f"field={mode}{projection_suffix}{sig_preview}")
        self._sync_status_var()


__all__ = ["DetmVizPanel", "VizFrame"]
