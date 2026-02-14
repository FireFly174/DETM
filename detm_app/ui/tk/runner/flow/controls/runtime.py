"""Runtime controls section for Tk runner launcher."""

from __future__ import annotations

from typing import Any

from detm_app.ui.tk.tooltips import attach_tooltip


def add_runtime_controls(*, frame: Any, tk: Any, ttk: Any, settings: Any, tips: dict[str, str]) -> dict[str, Any]:
    ttk.Label(frame, text="Backend").grid(row=0, column=0, sticky="w")
    backend_var = tk.StringVar(value=settings.config.backend)
    backend_box = ttk.Combobox(frame, textvariable=backend_var, values=["torch", "numpy"], width=10)
    backend_box.grid(row=0, column=1, sticky="w", padx=(6, 12))
    attach_tooltip(backend_box, tips.get("backend", ""))

    ttk.Label(frame, text="Device").grid(row=0, column=2, sticky="w")
    device_var = tk.StringVar(value=settings.config.device)
    device_entry = ttk.Entry(frame, textvariable=device_var, width=12)
    device_entry.grid(row=0, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(device_entry, tips.get("device", ""))

    ttk.Label(frame, text="Lattice (WxH)").grid(row=1, column=0, sticky="w")
    width_var = tk.IntVar(value=settings.config.width)
    height_var = tk.IntVar(value=settings.config.height)
    width_entry = ttk.Entry(frame, textvariable=width_var, width=6)
    width_entry.grid(row=1, column=1, sticky="w")
    height_entry = ttk.Entry(frame, textvariable=height_var, width=6)
    height_entry.grid(row=1, column=1, sticky="e")
    attach_tooltip(width_entry, tips.get("width", ""))
    attach_tooltip(height_entry, tips.get("height", ""))

    ttk.Label(frame, text="Seed").grid(row=1, column=2, sticky="w")
    seed_var = tk.IntVar(value=settings.seed)
    seed_entry = ttk.Entry(frame, textvariable=seed_var, width=12)
    seed_entry.grid(row=1, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(seed_entry, tips.get("ui.seed", tips.get("seed", "")))

    dynamics_frame = ttk.Frame(frame)
    dynamics_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=(4, 0))
    dynamics = settings.config.dynamics
    ttk.Label(dynamics_frame, text="Dyn a,b,k,g,t").grid(row=0, column=0, sticky="w")
    alpha_var = tk.DoubleVar(value=float(dynamics.alpha))
    beta_var = tk.DoubleVar(value=float(dynamics.beta))
    kappa_var = tk.DoubleVar(value=float(dynamics.kappa))
    gamma_var = tk.DoubleVar(value=float(dynamics.gamma))
    lambda_t_var = tk.DoubleVar(value=float(dynamics.lambda_t))
    alpha_entry = ttk.Entry(dynamics_frame, textvariable=alpha_var, width=7)
    alpha_entry.grid(row=0, column=1, sticky="w", padx=(6, 0))
    beta_entry = ttk.Entry(dynamics_frame, textvariable=beta_var, width=7)
    beta_entry.grid(row=0, column=2, sticky="w", padx=(6, 0))
    kappa_entry = ttk.Entry(dynamics_frame, textvariable=kappa_var, width=7)
    kappa_entry.grid(row=0, column=3, sticky="w", padx=(6, 0))
    gamma_entry = ttk.Entry(dynamics_frame, textvariable=gamma_var, width=7)
    gamma_entry.grid(row=0, column=4, sticky="w", padx=(6, 0))
    lambda_t_entry = ttk.Entry(dynamics_frame, textvariable=lambda_t_var, width=7)
    lambda_t_entry.grid(row=0, column=5, sticky="w", padx=(6, 12))
    attach_tooltip(alpha_entry, tips.get("dynamics.alpha", ""))
    attach_tooltip(beta_entry, tips.get("dynamics.beta", ""))
    attach_tooltip(kappa_entry, tips.get("dynamics.kappa", ""))
    attach_tooltip(gamma_entry, tips.get("dynamics.gamma", ""))
    attach_tooltip(lambda_t_entry, tips.get("dynamics.lambda_t", ""))
    ttk.Label(dynamics_frame, text="Boundary").grid(row=0, column=6, sticky="w")
    boundary_var = tk.StringVar(value=str(settings.config.boundary))
    boundary_box = ttk.Combobox(dynamics_frame, textvariable=boundary_var, values=["periodic", "open"], width=9)
    boundary_box.grid(row=0, column=7, sticky="w", padx=(6, 0))
    attach_tooltip(boundary_box, tips.get("boundary", ""))

    ttk.Label(frame, text="Ticks/step").grid(row=6, column=0, sticky="w")
    ticks_var = tk.IntVar(value=settings.ticks_per_step)
    ticks_entry = ttk.Entry(frame, textvariable=ticks_var, width=8)
    ticks_entry.grid(row=6, column=1, sticky="w")
    attach_tooltip(ticks_entry, tips.get("ui.ticks_per_step", tips.get("ticks_per_step", "")))

    ttk.Label(frame, text="Interval (ms)").grid(row=6, column=2, sticky="w")
    interval_var = tk.IntVar(value=settings.tick_interval_ms)
    interval_entry = ttk.Entry(frame, textvariable=interval_var, width=12)
    interval_entry.grid(row=6, column=3, sticky="w", padx=(6, 12))
    attach_tooltip(interval_entry, tips.get("ui.tick_interval_ms", tips.get("tick_interval_ms", "")))

    return {
        "backend_var": backend_var,
        "device_var": device_var,
        "width_var": width_var,
        "height_var": height_var,
        "boundary_var": boundary_var,
        "alpha_var": alpha_var,
        "beta_var": beta_var,
        "kappa_var": kappa_var,
        "gamma_var": gamma_var,
        "lambda_t_var": lambda_t_var,
        "seed_var": seed_var,
        "ticks_var": ticks_var,
        "interval_var": interval_var,
    }


__all__ = ["add_runtime_controls"]
