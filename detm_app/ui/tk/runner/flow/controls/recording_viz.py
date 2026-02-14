"""Recording/viz controls section for Tk runner launcher."""

from __future__ import annotations

from typing import Any

from detm_app.ui.tk.tooltips import attach_tooltip


def add_recording_and_viz_controls(*, frame: Any, tk: Any, ttk: Any, settings: Any, tips: dict[str, str]) -> dict[str, Any]:
    record_enabled_var = tk.BooleanVar(value=settings.record_dir is not None)
    ttk.Checkbutton(frame, text="Record trace", variable=record_enabled_var).grid(row=7, column=0, sticky="w")
    out_var = tk.StringVar(value=str(settings.record_dir) if settings.record_dir else "runs/out/ui_run")
    out_entry = ttk.Entry(frame, textvariable=out_var, width=38)
    out_entry.grid(row=7, column=1, columnspan=3, sticky="we", padx=(6, 0))
    attach_tooltip(out_entry, tips.get("ui.record_dir", tips.get("record_dir", "")))
    frame.columnconfigure(3, weight=1)

    fields_var = tk.BooleanVar(value=bool(getattr(settings, "record_fields", False)))
    fields_check = ttk.Checkbutton(frame, text="fields_hist.npz", variable=fields_var)
    fields_check.grid(row=7, column=3, sticky="e")
    attach_tooltip(fields_check, tips.get("ui.record_fields", tips.get("record_fields", "")))

    invariant_streams_var = tk.StringVar(value=getattr(settings, "invariant_streams", ""))
    ttk.Label(frame, text="Invariant streams").grid(row=8, column=0, sticky="w")
    invariant_streams_entry = ttk.Entry(frame, textvariable=invariant_streams_var, width=52)
    invariant_streams_entry.grid(row=8, column=1, columnspan=3, sticky="we", padx=(6, 0))
    attach_tooltip(invariant_streams_entry, tips.get("ui.invariant_streams", tips.get("invariant_streams", "")))

    viz_enabled_var = tk.BooleanVar(value=settings.viz_enabled)
    viz_enabled_check = ttk.Checkbutton(frame, text="Viz", variable=viz_enabled_var)
    viz_enabled_check.grid(row=9, column=0, sticky="w")
    attach_tooltip(viz_enabled_check, tips.get("ui.viz_enabled", tips.get("viz_enabled", "")))
    viz_transport_var = tk.StringVar(value=settings.viz_transport)
    viz_transport_box = ttk.Combobox(frame, textvariable=viz_transport_var, values=["embedded", "tcp", "none"], width=9)
    viz_transport_box.grid(row=9, column=1, sticky="w", padx=(6, 6))
    attach_tooltip(viz_transport_box, tips.get("ui.viz_transport", tips.get("viz_transport", "")))
    viz_host_var = tk.StringVar(value=settings.viz_host)
    viz_host_entry = ttk.Entry(frame, textvariable=viz_host_var, width=14)
    viz_host_entry.grid(row=9, column=2, sticky="w", padx=(6, 6))
    attach_tooltip(viz_host_entry, tips.get("ui.viz_host", tips.get("viz_host", "")))
    viz_port_var = tk.IntVar(value=settings.viz_port)
    viz_port_entry = ttk.Entry(frame, textvariable=viz_port_var, width=8)
    viz_port_entry.grid(row=9, column=3, sticky="w")
    attach_tooltip(viz_port_entry, tips.get("ui.viz_port", tips.get("viz_port", "")))

    viz_connect_var = tk.BooleanVar(value=settings.viz_connect)
    viz_connect_check = ttk.Checkbutton(frame, text="connect", variable=viz_connect_var)
    viz_connect_check.grid(row=10, column=0, sticky="w")
    attach_tooltip(viz_connect_check, tips.get("ui.viz_connect", tips.get("viz_connect", "")))
    viz_every_var = tk.IntVar(value=settings.viz_every_steps)
    viz_every_entry = ttk.Entry(frame, textvariable=viz_every_var, width=6)
    viz_every_entry.grid(row=10, column=1, sticky="w", padx=(6, 6))
    attach_tooltip(viz_every_entry, tips.get("ui.viz_every_steps", tips.get("viz_every_steps", "")))
    ttk.Label(frame, text="every_steps").grid(row=10, column=2, sticky="w")

    ttk.Label(frame, text="Mode").grid(row=11, column=0, sticky="w")
    ui_mode_var = tk.StringVar(value="interactive")
    ui_mode_box = ttk.Combobox(
        frame, textvariable=ui_mode_var, values=["interactive", "batch"], width=12, state="readonly"
    )
    ui_mode_box.grid(row=11, column=1, sticky="w", padx=(6, 0))

    status_var = tk.StringVar(value="Ready")
    ttk.Label(frame, textvariable=status_var).grid(row=12, column=0, columnspan=4, sticky="w")

    return {
        "record_enabled_var": record_enabled_var,
        "out_var": out_var,
        "fields_var": fields_var,
        "invariant_streams_var": invariant_streams_var,
        "viz_enabled_var": viz_enabled_var,
        "viz_transport_var": viz_transport_var,
        "viz_host_var": viz_host_var,
        "viz_port_var": viz_port_var,
        "viz_connect_var": viz_connect_var,
        "viz_every_var": viz_every_var,
        "ui_mode_var": ui_mode_var,
        "status_var": status_var,
    }


__all__ = ["add_recording_and_viz_controls"]
