from __future__ import annotations

from typing import Any

import numpy as np

from detm.runtime.signature import project_field_plane_any, projection_metadata_any


def to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def to_image_gray(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    vmin = float(np.min(arr))
    vmax = float(np.max(arr))
    span = max(1e-9, vmax - vmin)
    if not np.isfinite(span) or span <= 1e-9:
        norm = np.full_like(arr, 0.5, dtype=float)
    else:
        norm = (arr - vmin) / span
    return np.clip(np.round(norm * 255.0), 0, 255).astype(np.uint8)


def cmap_color(v: float, mode: str) -> str:
    v = max(0.0, min(1.0, float(v)))
    if mode == "gray":
        c = int(round(v * 255.0))
        return f"#{c:02x}{c:02x}{c:02x}"
    r = int(round(min(1.0, v * 1.4) * 255.0))
    g = int(round(max(0.0, min(1.0, (v - 0.35) * 1.6)) * 255.0))
    b = int(round(max(0.0, min(1.0, (v - 0.75) * 4.0)) * 255.0))
    return f"#{r:02x}{g:02x}{b:02x}"


def central_grad(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    dx = 0.5 * (np.roll(arr, -1, axis=1) - np.roll(arr, 1, axis=1))
    dy = 0.5 * (np.roll(arr, -1, axis=0) - np.roll(arr, 1, axis=0))
    return dx, dy


def field_from_state(*, state: Any, mode: str) -> np.ndarray:
    lattice = getattr(state, "lattice")
    def _normalize_field(values: Any) -> np.ndarray:
        array = to_numpy(values).astype(float, copy=False)
        if array.ndim == 1:
            array = array.reshape(lattice.height, lattice.width)
        return project_field_plane_any(array).astype(float, copy=False).reshape(
            lattice.height,
            lattice.width,
        )
    if mode == "entropy":
        return _normalize_field(state.field_state.entropy)
    if mode in {"internal_time", "time", "tau"}:
        return _normalize_field(state.field_state.internal_time)
    return _normalize_field(state.field_state.energy)


def projection_status_from_state(*, state: Any) -> str:
    projection = projection_metadata_any(getattr(getattr(state, "field_state"), "energy"))
    source_shape = list(projection.get("source_shape", []))
    projected_shape = list(projection.get("projected_shape", []))
    if len(source_shape) <= 0 or len(projected_shape) <= 0:
        return ""
    if source_shape == projected_shape:
        return ""
    source = "x".join(str(int(dim)) for dim in source_shape)
    projected = "x".join(str(int(dim)) for dim in projected_shape)
    return f" proj={source}->{projected}"


def ensure_grid(panel: Any, *, h: int, w: int) -> None:
    if panel._h == int(h) and panel._w == int(w) and panel._rects:
        return
    panel._h = int(h)
    panel._w = int(w)
    panel._rects.clear()
    panel.canvas.delete("all")
    for y in range(panel._h):
        row: list[int] = []
        for x in range(panel._w):
            rid = panel.canvas.create_rectangle(0, 0, 0, 0, outline="", fill="#000000")
            row.append(rid)
        panel._rects.append(row)
    layout_grid(panel)


def on_canvas_configure(panel: Any, *, event: Any) -> None:
    w = int(getattr(event, "width", 0) or 0)
    h = int(getattr(event, "height", 0) or 0)
    if w <= 0 or h <= 0:
        return
    if w == panel._canvas_w and h == panel._canvas_h:
        return
    panel._canvas_w, panel._canvas_h = w, h
    layout_grid(panel)


def layout_grid(panel: Any) -> None:
    if panel._h <= 0 or panel._w <= 0 or not panel._rects:
        return

    canvas_w = int(panel._canvas_w or panel.canvas.winfo_width() or int(panel.canvas["width"]))
    canvas_h = int(panel._canvas_h or panel.canvas.winfo_height() or int(panel.canvas["height"]))
    if canvas_w <= 1 or canvas_h <= 1:
        return

    cell = max(1.0, min(canvas_w / float(panel._w), canvas_h / float(panel._h)))
    panel._cell_w = cell
    panel._cell_h = cell

    grid_w = cell * panel._w
    grid_h = cell * panel._h

    ox = (canvas_w - grid_w) * 0.5
    oy = (canvas_h - grid_h) * 0.5
    panel._off_x = ox
    panel._off_y = oy
    for y in range(panel._h):
        for x in range(panel._w):
            x0 = ox + x * cell
            y0 = oy + (panel._h - 1 - y) * cell
            x1 = x0 + cell
            y1 = y0 + cell
            panel.canvas.coords(panel._rects[y][x], x0, y0, x1, y1)

    if panel._last_field is not None:
        draw_quiver(panel, panel._last_field)


def draw_quiver(panel: Any, arr: np.ndarray) -> None:
    for aid in panel._arrows:
        try:
            panel.canvas.delete(aid)
        except Exception:
            pass
    panel._arrows = []

    if not bool(panel.quiver_var.get()):
        return

    step = max(1, int(panel.q_step_var.get() or 1))
    scale = float(panel.q_scale_var.get() or 1.0)
    dx, dy = central_grad(arr)
    mag = np.hypot(dx, dy)
    mmax = float(np.max(mag)) if mag.size else 0.0
    if not np.isfinite(mmax) or mmax <= 1e-12:
        return

    base_len = scale * 0.45 * float(min(panel._cell_w, panel._cell_h))

    for yy in range(0, panel._h, step):
        for xx in range(0, panel._w, step):
            vx = float(dx[yy, xx]) / mmax
            vy = float(dy[yy, xx]) / mmax
            x0 = panel._off_x + (xx + 0.5) * panel._cell_w
            y0 = panel._off_y + (panel._h - 1 - yy + 0.5) * panel._cell_h
            x1 = x0 + vx * base_len
            y1 = y0 - vy * base_len
            aid = panel.canvas.create_line(x0, y0, x1, y1, fill="#00ffcc", arrow=panel._tk.LAST, width=1)
            panel._arrows.append(aid)


def paint_field(panel: Any, *, field: np.ndarray, cmap: str) -> None:
    img = to_image_gray(field)
    for y in range(field.shape[0]):
        for x in range(field.shape[1]):
            c = int(img[y, x])
            panel.canvas.itemconfig(panel._rects[y][x], fill=cmap_color(c / 255.0, cmap))


__all__ = [
    "cmap_color",
    "central_grad",
    "draw_quiver",
    "ensure_grid",
    "field_from_state",
    "layout_grid",
    "on_canvas_configure",
    "paint_field",
    "projection_status_from_state",
    "to_image_gray",
    "to_numpy",
]
