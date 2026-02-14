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


def _to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def _to_image_gray(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    vmin = float(np.min(arr))
    vmax = float(np.max(arr))
    span = max(1e-9, vmax - vmin)
    if not np.isfinite(span) or span <= 1e-9:
        norm = np.full_like(arr, 0.5, dtype=float)
    else:
        norm = (arr - vmin) / span
    img = np.clip(np.round(norm * 255.0), 0, 255).astype(np.uint8)
    return img


def _cmap_color(v: float, mode: str) -> str:
    v = max(0.0, min(1.0, float(v)))
    if mode == "gray":
        c = int(round(v * 255.0))
        return f"#{c:02x}{c:02x}{c:02x}"
    r = int(round(min(1.0, v * 1.4) * 255.0))
    g = int(round(max(0.0, min(1.0, (v - 0.35) * 1.6)) * 255.0))
    b = int(round(max(0.0, min(1.0, (v - 0.75) * 4.0)) * 255.0))
    return f"#{r:02x}{g:02x}{b:02x}"


def _central_grad(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    dx = 0.5 * (np.roll(arr, -1, axis=1) - np.roll(arr, 1, axis=1))
    dy = 0.5 * (np.roll(arr, -1, axis=0) - np.roll(arr, 1, axis=0))
    return dx, dy


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

        # --- Graph tab (пока просто заглушка, но место готово) ---
        ttk.Label(tab_plot, text="(Graph view: TODO) ").grid(row=0, column=0, sticky="nw", padx=8, pady=8)

        self.canvas.bind("<Configure>", self._on_canvas_configure, add=True)

        parent.rowconfigure(2, weight=1)
        parent.columnconfigure(0, weight=1)

        self.canvas.bind("<Configure>", self._on_canvas_configure, add=True)

    def _ensure_grid(self, h: int, w: int) -> None:
        if self._h == int(h) and self._w == int(w) and self._rects:
            return
        self._h = int(h)
        self._w = int(w)
        self._rects.clear()
        self.canvas.delete("all")
        for y in range(self._h):
            row: list[int] = []
            for x in range(self._w):
                rid = self.canvas.create_rectangle(0, 0, 0, 0, outline="", fill="#000000")
                row.append(rid)
            self._rects.append(row)
        self._layout_grid()

    def _sync_status_var(self) -> None:
        try:
            self.status_var.set(
                f"{self.status_left.get()}  {self.status_mid.get()}  {self.status_right.get()}"
            )
        except Exception:
            pass

    def _on_canvas_configure(self, event) -> None:
        w = int(getattr(event, "width", 0) or 0)
        h = int(getattr(event, "height", 0) or 0)
        if w <= 0 or h <= 0:
            return
        if w == self._canvas_w and h == self._canvas_h:
            return
        self._canvas_w, self._canvas_h = w, h
        self._layout_grid()

    def _layout_grid(self) -> None:
        if self._h <= 0 or self._w <= 0 or not self._rects:
            return

        canvas_w = int(self._canvas_w or self.canvas.winfo_width() or int(self.canvas["width"]))
        canvas_h = int(self._canvas_h or self.canvas.winfo_height() or int(self.canvas["height"]))
        if canvas_w <= 1 or canvas_h <= 1:
            return

        # квадратная клетка, как “CSS grid: auto-fit”
        cell = max(1.0, min(canvas_w / float(self._w), canvas_h / float(self._h)))
        self._cell_w = cell
        self._cell_h = cell

        grid_w = cell * self._w
        grid_h = cell * self._h

        # центрируем
        ox = (canvas_w - grid_w) * 0.5
        oy = (canvas_h - grid_h) * 0.5
        self._off_x = ox
        self._off_y = oy
        for y in range(self._h):
            for x in range(self._w):
                x0 = ox + x * cell
                y0 = oy + (self._h - 1 - y) * cell
                x1 = x0 + cell
                y1 = y0 + cell
                self.canvas.coords(self._rects[y][x], x0, y0, x1, y1)

        if self._last_field is not None:
            self._draw_quiver(self._last_field)


    def _draw_quiver(self, arr: np.ndarray) -> None:
        for aid in self._arrows:
            try:
                self.canvas.delete(aid)
            except Exception:
                pass
        self._arrows = []

        if not bool(self.quiver_var.get()):
            return

        step = max(1, int(self.q_step_var.get() or 1))
        scale = float(self.q_scale_var.get() or 1.0)
        dx, dy = _central_grad(arr)
        mag = np.hypot(dx, dy)
        mmax = float(np.max(mag)) if mag.size else 0.0
        if not np.isfinite(mmax) or mmax <= 1e-12:
            return

        base_len = scale * 0.45 * float(min(self._cell_w, self._cell_h))

        for yy in range(0, self._h, step):
            for xx in range(0, self._w, step):
                vx = float(dx[yy, xx]) / mmax
                vy = float(dy[yy, xx]) / mmax
                x0 = self._off_x + (xx + 0.5) * self._cell_w
                y0 = self._off_y + (self._h - 1 - yy + 0.5) * self._cell_h
                x1 = x0 + vx * base_len
                y1 = y0 - vy * base_len
                aid = self.canvas.create_line(x0, y0, x1, y1, fill="#00ffcc", arrow=self._tk.LAST, width=1)
                self._arrows.append(aid)

    def update_from_state_blob(self, *, state_blob: bytes, tick: int, signature: Optional[list[float]] = None) -> None:
        state = deserialize_state(state_blob)
        lattice = state.lattice
        mode = str(self.field_var.get()).strip().lower() or "energy"
        if mode == "entropy":
            field = _to_numpy(state.field_state.entropy).astype(float, copy=False).reshape(lattice.height, lattice.width)
        elif mode in {"internal_time", "time", "tau"}:
            field = (
                _to_numpy(state.field_state.internal_time)
                .astype(float, copy=False)
                .reshape(lattice.height, lattice.width)
            )
        else:
            field = _to_numpy(state.field_state.energy).astype(float, copy=False).reshape(lattice.height, lattice.width)

        self._ensure_grid(lattice.height, lattice.width)
        self._last_field = field
        img = _to_image_gray(field)
        cmap = str(self.cmap_var.get()).strip().lower() or "heat"
        for y in range(lattice.height):
            for x in range(lattice.width):
                c = int(img[y, x])
                self.canvas.itemconfig(self._rects[y][x], fill=_cmap_color(c / 255.0, cmap))

        self._draw_quiver(field)
        sig_preview = f" sig0..3={signature[:4]}" if signature else ""
        self.status_left.set(f"tick={int(tick)}")
        self.status_mid.set(f"lattice={lattice.width}x{lattice.height}")
        self.status_right.set(f"field={mode}{sig_preview}")
        self._sync_status_var()


    def update_from_state(self, *, state: Any, tick: int, signature: Optional[list[float]] = None) -> None:
        lattice = getattr(state, "lattice")
        mode = str(self.field_var.get()).strip().lower() or "energy"
        if mode == "entropy":
            field = _to_numpy(state.field_state.entropy).astype(float, copy=False).reshape(lattice.height, lattice.width)
        elif mode in {"internal_time", "time", "tau"}:
            field = (
                _to_numpy(state.field_state.internal_time)
                .astype(float, copy=False)
                .reshape(lattice.height, lattice.width)
            )
        else:
            field = _to_numpy(state.field_state.energy).astype(float, copy=False).reshape(lattice.height, lattice.width)

        self._ensure_grid(lattice.height, lattice.width)
        self._last_field = field
        img = _to_image_gray(field)
        cmap = str(self.cmap_var.get()).strip().lower() or "heat"
        for y in range(lattice.height):
            for x in range(lattice.width):
                c = int(img[y, x])
                self.canvas.itemconfig(self._rects[y][x], fill=_cmap_color(c / 255.0, cmap))

        self._draw_quiver(field)
        sig_preview = f" sig0..3={signature[:4]}" if signature else ""
        self.status_var.set(
            f"tick={int(tick)}  lattice={lattice.width}x{lattice.height}  field={mode}{sig_preview}"
        )


__all__ = ["DetmVizPanel", "VizFrame"]
