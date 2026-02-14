"""Lightweight Tkinter settings UI.

The UI is intentionally "controller-only": it does not render fields itself.
If visualization is enabled, it starts a separate viz daemon process and streams
serialized DETM state blobs to it.
"""

from __future__ import annotations

from detm_app.config.ui_models import UiRunSettings
from detm_app.runtime.ui_runtime import DetmUiRunner
from detm_app.ui.tk.runner.flow import (
    TkBatchFlow,
    TkControlVars,
    TkLauncherLayout,
    TkRuntimeActionFlow,
    TkSettingsFlow,
    TkVizFlow,
    build_launcher_controls,
    build_launcher_layout,
    configure_root_grid,
    install_clipboard_shortcuts,
    install_fullscreen_bindings,
)


DetmTkRunner = DetmUiRunner


def launch_tk_ui(settings: UiRunSettings) -> None:  # pragma: no cover
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as exc:
        raise RuntimeError("Tkinter is required for the UI (python -m tkinter)") from exc

    root = tk.Tk()
    root.title("DETM Runner")
    install_clipboard_shortcuts(root)
    install_fullscreen_bindings(root)
    configure_root_grid(root)

    runner = DetmTkRunner(settings)
    layout: TkLauncherLayout = build_launcher_layout(root=root, tk=tk, ttk=ttk)
    controls: TkControlVars = build_launcher_controls(
        frame=layout.controls_frame,
        tk=tk,
        ttk=ttk,
        settings=settings,
    )

    layout.viz_panel.status_mid.set("Viz: embedded")
    viz_flow = TkVizFlow(settings=settings, runner=runner, viz_panel=layout.viz_panel)
    settings_flow = TkSettingsFlow(
        settings=settings,
        runner=runner,
        controls=controls,
    )

    buttons = ttk.Frame(layout.controls_frame)
    buttons.grid(row=13, column=0, columnspan=4, sticky="w", pady=(6, 0))

    def _log(message: str) -> None:
        layout.log_text.insert("end", message.rstrip() + "\n")
        layout.log_text.see("end")

    def _show_viz_view(view: str) -> None:
        if view == "log":
            layout.log_frame.tkraise()
        else:
            layout.viz_panel_frame.tkraise()

    batch_flow = TkBatchFlow(
        root=root,
        tk=tk,
        ttk=ttk,
        parent=layout.controls_frame,
        row=14,
        build_config_from_widgets=settings_flow.build_config,
        read_invariant_streams=settings_flow.read_invariant_streams,
        log=_log,
        clear_log=lambda: layout.log_text.delete("1.0", "end"),
        show_viz_view=_show_viz_view,
    )

    action_flow = TkRuntimeActionFlow(
        root=root,
        settings=settings,
        runner=runner,
        status_var=controls.status_var,
        ui_mode_var=controls.ui_mode_var,
        interactive_buttons_frame=buttons,
        batch_flow=batch_flow,
        viz_flow=viz_flow,
        apply_settings=settings_flow.apply,
        show_viz_view=_show_viz_view,
    )
    ttk.Button(buttons, text="Reset", command=action_flow.on_reset).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(buttons, text="Step", command=action_flow.on_step).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(buttons, text="Run/Stop", command=action_flow.on_run_toggle).grid(row=0, column=2, padx=(0, 6))
    controls.ui_mode_var.trace_add("write", action_flow.on_mode_change)
    root.protocol("WM_DELETE_WINDOW", action_flow.on_close)

    runner._configure_recording()
    runner._configure_invariants()
    runner._configure_viz()
    action_flow.update_status()
    viz_flow.update_embedded(force=True)
    viz_flow.update_tcp()
    root.mainloop()


__all__ = ["DetmTkRunner", "UiRunSettings", "launch_tk_ui"]
