"""Visualization daemon (separate process).

Receives serialized DETMState blobs and renders them in a lightweight Tk window.
The daemon is intentionally dumb: it only deserializes state and displays it.
"""

from __future__ import annotations

import argparse
import json
import queue
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

from detm.runtime.serialization import deserialize_state
from detm.viz.protocol import recv_msg


def _to_image_gray(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    vmin = float(np.min(arr))
    vmax = float(np.max(arr))
    span = max(1e-9, vmax - vmin)
    # If the field becomes (nearly) constant, avoid collapsing to all-black.
    # A constant snapshot still carries meaning and should remain visible.
    if not np.isfinite(span) or span <= 1e-9:
        norm = np.full_like(arr, 0.5, dtype=float)
    else:
        norm = (arr - vmin) / span
    img = np.clip(np.round(norm * 255.0), 0, 255).astype(np.uint8)
    return img


@dataclass
class StatePacket:
    tick: int
    state_blob: bytes
    signature: Optional[list[float]] = None
    meta: Optional[Dict[str, Any]] = None


class VizServer:
    def __init__(self, host: str, port: int):
        self.host = str(host)
        self.port = int(port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(4)
        self._sock.settimeout(0.5)
        self._queue: "queue.Queue[StatePacket]" = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)

    @property
    def address(self) -> Tuple[str, int]:
        h, p = self._sock.getsockname()
        return str(h), int(p)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass

    def poll(self) -> Optional[StatePacket]:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                client, _addr = self._sock.accept()
            except OSError:
                continue
            t = threading.Thread(target=self._client_loop, args=(client,), daemon=True)
            t.start()

    def _client_loop(self, client: socket.socket) -> None:
        with client:
            while not self._stop.is_set():
                try:
                    msg = recv_msg(client)
                except Exception:
                    return
                mtype = msg.get("type")
                if mtype == "close":
                    return
                if mtype != "state":
                    continue
                packet = StatePacket(
                    tick=int(msg.get("tick", 0)),
                    state_blob=msg.get("state_blob", b""),
                    signature=msg.get("signature"),
                    meta=msg.get("meta"),
                )
                self._queue.put(packet)


def run_daemon(host: str, port: int) -> None:  # pragma: no cover (UI)
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as exc:
        raise RuntimeError("Tkinter is required for the viz daemon") from exc

    server = VizServer(host, port)
    server.start()
    ready_host, ready_port = server.address
    print(json.dumps({"host": ready_host, "port": ready_port}), flush=True)

    root = tk.Tk()
    root.title("DETM Viz Daemon")

    frm = ttk.Frame(root, padding=10)
    frm.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frm.columnconfigure(0, weight=1)
    frm.rowconfigure(1, weight=1)

    status_var = tk.StringVar(value=f"Listening on {ready_host}:{ready_port}")
    ttk.Label(frm, textvariable=status_var).grid(row=0, column=0, sticky="w")

    controls = ttk.Frame(frm)
    controls.grid(row=1, column=0, sticky="we", pady=(8, 0))
    controls.columnconfigure(9, weight=1)

    field_var = tk.StringVar(value="energy")
    ttk.Label(controls, text="Field").grid(row=0, column=0, sticky="w")
    ttk.Combobox(
        controls,
        textvariable=field_var,
        values=["energy", "entropy", "internal_time"],
        width=14,
        state="readonly",
    ).grid(row=0, column=1, sticky="w", padx=(6, 12))

    cmap_var = tk.StringVar(value="heat")
    ttk.Label(controls, text="Cmap").grid(row=0, column=2, sticky="w")
    ttk.Combobox(
        controls,
        textvariable=cmap_var,
        values=["gray", "heat"],
        width=8,
        state="readonly",
    ).grid(row=0, column=3, sticky="w", padx=(6, 12))

    quiver_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(controls, text="Quiver", variable=quiver_var).grid(row=0, column=4, sticky="w")

    q_step_var = tk.IntVar(value=2)
    ttk.Label(controls, text="step").grid(row=0, column=5, sticky="w", padx=(8, 2))
    ttk.Entry(controls, textvariable=q_step_var, width=4).grid(row=0, column=6, sticky="w")

    q_scale_var = tk.DoubleVar(value=0.8)
    ttk.Label(controls, text="scale").grid(row=0, column=7, sticky="w", padx=(8, 2))
    ttk.Entry(controls, textvariable=q_scale_var, width=6).grid(row=0, column=8, sticky="w")

    canvas = tk.Canvas(frm, width=520, height=520, bg="#111111", highlightthickness=1, highlightbackground="#333333")
    canvas.grid(row=2, column=0, sticky="nsew", pady=(8, 0))

    rects: list[list[int]] = []
    current_shape: Tuple[int, int] | None = None
    arrows: list[int] = []
    cell_w = 1
    cell_h = 1

    def _ensure_grid(h: int, w: int) -> None:
        nonlocal current_shape
        if current_shape == (h, w):
            return
        current_shape = (h, w)
        rects.clear()
        arrows.clear()
        canvas.delete("all")
        canvas_w = int(canvas["width"])
        canvas_h = int(canvas["height"])
        nonlocal cell_w, cell_h
        cell_w = max(1, canvas_w // w)
        cell_h = max(1, canvas_h // h)
        for y in range(h):
            row: list[int] = []
            for x in range(w):
                x0, y0 = x * cell_w, (h - 1 - y) * cell_h
                x1, y1 = x0 + cell_w, y0 + cell_h
                rid = canvas.create_rectangle(x0, y0, x1, y1, outline="", fill="#000000")
                row.append(rid)
            rects.append(row)

    def _cmap_color(v: float, mode: str) -> str:
        # v expected in [0..1]
        v = max(0.0, min(1.0, float(v)))
        if mode == "gray":
            c = int(round(v * 255.0))
            return f"#{c:02x}{c:02x}{c:02x}"
        # "heat": black -> red -> yellow -> white
        r = int(round(min(1.0, v * 1.4) * 255.0))
        g = int(round(max(0.0, min(1.0, (v - 0.35) * 1.6)) * 255.0))
        b = int(round(max(0.0, min(1.0, (v - 0.75) * 4.0)) * 255.0))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _central_grad(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        # dx along x (cols), dy along y (rows)
        dx = 0.5 * (np.roll(arr, -1, axis=1) - np.roll(arr, 1, axis=1))
        dy = 0.5 * (np.roll(arr, -1, axis=0) - np.roll(arr, 1, axis=0))
        return dx, dy

    def _draw_quiver(arr: np.ndarray, h: int, w: int) -> None:
        # Clear existing arrows
        nonlocal arrows
        for aid in arrows:
            try:
                canvas.delete(aid)
            except Exception:
                pass
        arrows = []

        if not bool(quiver_var.get()):
            return

        step = max(1, int(q_step_var.get() or 1))
        scale = float(q_scale_var.get() or 1.0)
        dx, dy = _central_grad(arr)
        mag = np.hypot(dx, dy)
        mmax = float(np.max(mag)) if mag.size else 0.0
        if not np.isfinite(mmax) or mmax <= 1e-12:
            return

        # Arrow length in pixels
        base_len = scale * 0.45 * float(min(cell_w, cell_h))

        for yy in range(0, h, step):
            for xx in range(0, w, step):
                vx = float(dx[yy, xx]) / mmax
                vy = float(dy[yy, xx]) / mmax
                x0 = (xx + 0.5) * cell_w
                y0 = (h - 1 - yy + 0.5) * cell_h
                x1 = x0 + vx * base_len
                y1 = y0 - vy * base_len
                aid = canvas.create_line(x0, y0, x1, y1, fill="#00ffcc", arrow=tk.LAST, width=1)
                arrows.append(aid)

    last_ts = 0.0
    last_tick = 0

    def _apply_packet(packet: StatePacket) -> None:
        nonlocal last_ts, last_tick
        state = deserialize_state(packet.state_blob)
        lattice = state.lattice
        mode = str(field_var.get()).strip().lower() or "energy"
        if mode == "entropy":
            field = np.asarray(state.field_state.entropy, dtype=float).reshape(lattice.height, lattice.width)
        elif mode in {"internal_time", "time", "tau"}:
            field = np.asarray(state.field_state.internal_time, dtype=float).reshape(lattice.height, lattice.width)
        else:
            field = np.asarray(state.field_state.energy, dtype=float).reshape(lattice.height, lattice.width)

        img = _to_image_gray(field)
        _ensure_grid(lattice.height, lattice.width)

        for y in range(lattice.height):
            for x in range(lattice.width):
                c = int(img[y, x])
                color = _cmap_color(c / 255.0, str(cmap_var.get()).strip().lower() or "heat")
                canvas.itemconfig(rects[y][x], fill=color)

        _draw_quiver(field, lattice.height, lattice.width)

        now = time.perf_counter()
        dt = now - last_ts if last_ts else 0.0
        last_ts = now
        last_tick = packet.tick

        sig_preview = ""
        if packet.signature:
            sig_preview = f" sig0..3={packet.signature[:4]}"

        fps = (1.0 / dt) if dt > 1e-9 else 0.0
        status_var.set(
            f"tick={last_tick}  fps~{fps:.1f}  lattice={lattice.width}x{lattice.height}  field={mode}{sig_preview}"
        )

    def _poll():
        # Drain queue, keep the most recent state only.
        latest = None
        while True:
            pkt = server.poll()
            if pkt is None:
                break
            latest = pkt
        if latest is not None:
            _apply_packet(latest)
        root.after(30, _poll)

    def _on_close():
        server.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.after(30, _poll)
    root.mainloop()


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1", help="Bind host (default: localhost)")
    ap.add_argument("--port", type=int, default=0, help="Bind port (0 = auto)")
    args = ap.parse_args()
    run_daemon(args.host, args.port)


if __name__ == "__main__":
    main()
