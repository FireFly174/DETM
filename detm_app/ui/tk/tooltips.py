"""Tiny Tk tooltip helper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Tooltip:
    widget: object
    text: str
    _win: Optional[object] = None

    def show(self) -> None:
        if self._win is not None:
            return
        try:
            import tkinter as tk
        except Exception:
            return

        w = self.widget
        try:
            x = int(w.winfo_rootx()) + 12
            y = int(w.winfo_rooty()) + int(w.winfo_height()) + 8
        except Exception:
            x, y = 0, 0

        win = tk.Toplevel(w)
        win.wm_overrideredirect(True)
        win.wm_geometry(f"+{x}+{y}")
        win.attributes("-topmost", True)
        label = tk.Label(
            win,
            text=str(self.text),
            justify="left",
            background="#222222",
            foreground="#f0f0f0",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=4,
            wraplength=360,
        )
        label.pack()
        self._win = win

    def hide(self) -> None:
        if self._win is None:
            return
        try:
            self._win.destroy()
        except Exception:
            pass
        self._win = None


def attach_tooltip(widget: object, text: str) -> None:
    if not text:
        return
    tip = Tooltip(widget=widget, text=text)
    try:
        widget.bind("<Enter>", lambda _e: tip.show(), add=True)
        widget.bind("<Leave>", lambda _e: tip.hide(), add=True)
        widget.bind("<ButtonPress>", lambda _e: tip.hide(), add=True)
    except Exception:
        return


__all__ = ["Tooltip", "attach_tooltip"]

