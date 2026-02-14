"""Influence controls section for Tk runner launcher."""

from __future__ import annotations

from typing import Any

from detm_app.ui.tk.tooltips import attach_tooltip


def add_influence_controls(
    *,
    frame: Any,
    tk: Any,
    ttk: Any,
    settings: Any,
    tips: dict[str, str],
    symbols: list[str],
) -> dict[str, Any]:
    ttk.Label(frame, text="Influence").grid(row=3, column=0, sticky="w")
    influence_mode_var = tk.StringVar(value=getattr(settings, "influence_mode", "symbol"))
    influence_mode_box = ttk.Combobox(
        frame,
        textvariable=influence_mode_var,
        values=["symbol", "joystick_field", "joystick_patch", "source_sink", "none"],
        width=16,
    )
    influence_mode_box.grid(row=3, column=1, sticky="w", padx=(0, 12))
    attach_tooltip(influence_mode_box, tips.get("ui.influence_mode", ""))
    ttk.Label(frame, text="Dur(steps)").grid(row=3, column=2, sticky="w")
    duration_var = tk.IntVar(value=int(getattr(settings, "influence_duration_steps", 0)))
    duration_entry = ttk.Entry(frame, textvariable=duration_var, width=12)
    duration_entry.grid(row=3, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(duration_entry, tips.get("ui.influence_duration_steps", ""))

    ttk.Label(frame, text="Symbol").grid(row=4, column=0, sticky="w")
    symbol_var = tk.StringVar(value=settings.symbol_id)
    symbol_box = ttk.Combobox(frame, textvariable=symbol_var, values=symbols, width=16)
    symbol_box.grid(row=4, column=1, sticky="w", padx=(0, 12))
    attach_tooltip(symbol_box, tips.get("ui.symbol_id", ""))

    ttk.Label(frame, text="Amp").grid(row=4, column=2, sticky="w")
    amplitude_var = tk.DoubleVar(value=settings.amplitude)
    amplitude_entry = ttk.Entry(frame, textvariable=amplitude_var, width=12)
    amplitude_entry.grid(row=4, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(amplitude_entry, tips.get("ui.amplitude", ""))

    influence_frame = ttk.Frame(frame)
    influence_frame.grid(row=5, column=0, columnspan=4, sticky="we", pady=(2, 0))
    ttk.Label(influence_frame, text="Joy dx/dy").grid(row=0, column=0, sticky="w")
    joy_dx_var = tk.DoubleVar(value=float(getattr(settings, "joy_dx", 0.0)))
    joy_dy_var = tk.DoubleVar(value=float(getattr(settings, "joy_dy", 0.0)))
    joy_dx_entry = ttk.Entry(influence_frame, textvariable=joy_dx_var, width=7)
    joy_dx_entry.grid(row=0, column=1, sticky="w", padx=(6, 0))
    joy_dy_entry = ttk.Entry(influence_frame, textvariable=joy_dy_var, width=7)
    joy_dy_entry.grid(row=0, column=2, sticky="w", padx=(6, 12))
    attach_tooltip(joy_dx_entry, tips.get("ui.joy_dx", ""))
    attach_tooltip(joy_dy_entry, tips.get("ui.joy_dy", ""))

    ttk.Label(influence_frame, text="Patch cx/cy/r").grid(row=0, column=3, sticky="w")
    patch_cx_var = tk.IntVar(value=int(getattr(settings, "patch_cx", settings.config.width // 2)))
    patch_cy_var = tk.IntVar(value=int(getattr(settings, "patch_cy", settings.config.height // 2)))
    patch_radius_var = tk.IntVar(
        value=int(getattr(settings, "patch_radius", max(1, max(settings.config.width, settings.config.height) // 8)))
    )
    patch_cx_entry = ttk.Entry(influence_frame, textvariable=patch_cx_var, width=5)
    patch_cx_entry.grid(row=0, column=4, sticky="w", padx=(6, 0))
    patch_cy_entry = ttk.Entry(influence_frame, textvariable=patch_cy_var, width=5)
    patch_cy_entry.grid(row=0, column=5, sticky="w", padx=(6, 0))
    patch_radius_entry = ttk.Entry(influence_frame, textvariable=patch_radius_var, width=5)
    patch_radius_entry.grid(row=0, column=6, sticky="w", padx=(6, 12))
    attach_tooltip(patch_cx_entry, tips.get("ui.patch_cx", ""))
    attach_tooltip(patch_cy_entry, tips.get("ui.patch_cy", ""))
    attach_tooltip(patch_radius_entry, tips.get("ui.patch_radius", ""))

    ttk.Label(influence_frame, text="Src(x,y)->Dst(x,y)").grid(row=1, column=0, sticky="w")
    source_x_var = tk.IntVar(value=int(getattr(settings, "source_x", 0)))
    source_y_var = tk.IntVar(value=int(getattr(settings, "source_y", 0)))
    sink_x_var = tk.IntVar(value=int(getattr(settings, "sink_x", 0)))
    sink_y_var = tk.IntVar(value=int(getattr(settings, "sink_y", 0)))
    source_x_entry = ttk.Entry(influence_frame, textvariable=source_x_var, width=5)
    source_x_entry.grid(row=1, column=1, sticky="w", padx=(6, 0))
    source_y_entry = ttk.Entry(influence_frame, textvariable=source_y_var, width=5)
    source_y_entry.grid(row=1, column=2, sticky="w", padx=(6, 12))
    sink_x_entry = ttk.Entry(influence_frame, textvariable=sink_x_var, width=5)
    sink_x_entry.grid(row=1, column=3, sticky="w", padx=(6, 0))
    sink_y_entry = ttk.Entry(influence_frame, textvariable=sink_y_var, width=5)
    sink_y_entry.grid(row=1, column=4, sticky="w", padx=(6, 12))
    attach_tooltip(source_x_entry, tips.get("ui.source_x", ""))
    attach_tooltip(source_y_entry, tips.get("ui.source_y", ""))
    attach_tooltip(sink_x_entry, tips.get("ui.sink_x", ""))
    attach_tooltip(sink_y_entry, tips.get("ui.sink_y", ""))
    ttk.Label(influence_frame, text="src/dst val").grid(row=1, column=5, sticky="w")
    source_value_var = tk.DoubleVar(value=float(getattr(settings, "source_value", 1.0)))
    sink_value_var = tk.DoubleVar(value=float(getattr(settings, "sink_value", 0.0)))
    source_value_entry = ttk.Entry(influence_frame, textvariable=source_value_var, width=7)
    source_value_entry.grid(row=1, column=6, sticky="w", padx=(6, 0))
    sink_value_entry = ttk.Entry(influence_frame, textvariable=sink_value_var, width=7)
    sink_value_entry.grid(row=1, column=7, sticky="w", padx=(6, 0))
    attach_tooltip(source_value_entry, tips.get("ui.source_value", ""))
    attach_tooltip(sink_value_entry, tips.get("ui.sink_value", ""))

    return {
        "influence_mode_var": influence_mode_var,
        "duration_var": duration_var,
        "symbol_var": symbol_var,
        "amplitude_var": amplitude_var,
        "joy_dx_var": joy_dx_var,
        "joy_dy_var": joy_dy_var,
        "patch_cx_var": patch_cx_var,
        "patch_cy_var": patch_cy_var,
        "patch_radius_var": patch_radius_var,
        "source_x_var": source_x_var,
        "source_y_var": source_y_var,
        "sink_x_var": sink_x_var,
        "sink_y_var": sink_y_var,
        "source_value_var": source_value_var,
        "sink_value_var": sink_value_var,
    }


__all__ = ["add_influence_controls"]
