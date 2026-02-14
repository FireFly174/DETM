"""Clipboard helpers for Tk launcher widgets."""

from __future__ import annotations

from typing import Any


def install_clipboard_shortcuts(root: Any) -> None:
    def gen(event_name: str) -> None:
        widget = root.focus_get()
        if widget is None:
            return
        try:
            widget.event_generate(event_name)
        except Exception:
            return

    def select_all() -> None:
        widget = root.focus_get()
        if widget is None:
            return
        try:
            widget.selection_range(0, "end")
            widget.icursor("end")
            return
        except Exception:
            pass
        try:
            widget.tag_add("sel", "1.0", "end")
            widget.mark_set("insert", "end")
        except Exception:
            return

    root.bind_all("<Control-c>", lambda _e: gen("<<Copy>>"), add=True)
    root.bind_all("<Control-v>", lambda _e: gen("<<Paste>>"), add=True)
    root.bind_all("<Control-x>", lambda _e: gen("<<Cut>>"), add=True)
    root.bind_all("<Control-a>", lambda _e: select_all(), add=True)


__all__ = ["install_clipboard_shortcuts"]
