"""Window helpers for Tk runner launcher."""

from __future__ import annotations

from typing import Any


def install_fullscreen_bindings(root: Any) -> None:
    state = {"is_full": False, "prev_geom": None}

    def _toggle_fullscreen(_event: object | None = None) -> None:
        state["is_full"] = not bool(state["is_full"])
        if bool(state["is_full"]):
            state["prev_geom"] = root.geometry()
            root.attributes("-fullscreen", True)
        else:
            root.attributes("-fullscreen", False)
            if state["prev_geom"]:
                root.geometry(str(state["prev_geom"]))

    def _exit_fullscreen(_event: object | None = None) -> None:
        if bool(state["is_full"]):
            _toggle_fullscreen()

    root.bind("<F11>", _toggle_fullscreen, add=True)
    root.bind("<Escape>", _exit_fullscreen, add=True)


def configure_root_grid(root: Any) -> None:
    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)


__all__ = ["configure_root_grid", "install_fullscreen_bindings"]
