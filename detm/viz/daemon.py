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

    canvas = tk.Canvas(frm, width=520, height=520, bg="#111111", highlightthickness=1, highlightbackground="#333333")
    canvas.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

    rects: list[list[int]] = []
    current_shape: Tuple[int, int] | None = None

    def _ensure_grid(h: int, w: int) -> None:
        nonlocal current_shape
        if current_shape == (h, w):
            return
        current_shape = (h, w)
        rects.clear()
        canvas.delete("all")
        canvas_w = int(canvas["width"])
        canvas_h = int(canvas["height"])
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

    last_ts = 0.0
    last_tick = 0

    def _apply_packet(packet: StatePacket) -> None:
        nonlocal last_ts, last_tick
        state = deserialize_state(packet.state_blob)
        lattice = state.lattice
        energy = np.asarray(state.field_state.energy, dtype=float).reshape(lattice.height, lattice.width)
        img = _to_image_gray(energy)
        _ensure_grid(lattice.height, lattice.width)

        for y in range(lattice.height):
            for x in range(lattice.width):
                c = int(img[y, x])
                color = f"#{c:02x}{c:02x}{c:02x}"
                canvas.itemconfig(rects[y][x], fill=color)

        now = time.perf_counter()
        dt = now - last_ts if last_ts else 0.0
        last_ts = now
        last_tick = packet.tick

        sig_preview = ""
        if packet.signature:
            sig_preview = f" sig0..3={packet.signature[:4]}"

        fps = (1.0 / dt) if dt > 1e-9 else 0.0
        status_var.set(f"tick={last_tick}  fps~{fps:.1f}  lattice={lattice.width}x{lattice.height}{sig_preview}")

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

