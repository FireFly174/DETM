"""Control builder orchestration for Tk runner launcher."""

from __future__ import annotations

from typing import Any

from detm.runtime.symbols import list_symbols
from detm_app.config.tooltips import load_tooltips_from_config_default
from detm_app.ui.tk.runner.flow.controls.influence import add_influence_controls
from detm_app.ui.tk.runner.flow.controls.model import TkControlVars
from detm_app.ui.tk.runner.flow.controls.recording_viz import add_recording_and_viz_controls
from detm_app.ui.tk.runner.flow.controls.runtime import add_runtime_controls


def build_launcher_controls(*, frame: Any, tk: Any, ttk: Any, settings: Any) -> TkControlVars:
    tips = load_tooltips_from_config_default()
    symbols = ["(none)"] + list_symbols()

    values: dict[str, Any] = {}
    values.update(add_runtime_controls(frame=frame, tk=tk, ttk=ttk, settings=settings, tips=tips))
    values.update(
        add_influence_controls(
            frame=frame,
            tk=tk,
            ttk=ttk,
            settings=settings,
            tips=tips,
            symbols=symbols,
        )
    )
    values.update(add_recording_and_viz_controls(frame=frame, tk=tk, ttk=ttk, settings=settings, tips=tips))
    return TkControlVars(**values)


__all__ = ["build_launcher_controls"]
