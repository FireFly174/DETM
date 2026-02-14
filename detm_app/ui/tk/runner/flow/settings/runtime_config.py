"""Runtime config assembly helpers for Tk settings flow."""

from __future__ import annotations

from typing import Any

from detm.runtime.config import DETMConfig
from detm_app.ui.tk.runner.flow.controls.model import TkControlVars


def build_runtime_config(*, settings: Any, controls: TkControlVars) -> DETMConfig:
    base = settings.config.to_dict()
    dynamics_cfg = dict(base.get("dynamics", {}))
    dynamics_cfg.update(
        {
            "alpha": float(controls.alpha_var.get()),
            "beta": float(controls.beta_var.get()),
            "kappa": float(controls.kappa_var.get()),
            "gamma": float(controls.gamma_var.get()),
            "lambda_t": float(controls.lambda_t_var.get()),
        }
    )
    return DETMConfig.from_dict(
        {
            **base,
            "backend": controls.backend_var.get().strip() or settings.config.backend,
            "device": controls.device_var.get().strip() or settings.config.device,
            "width": int(controls.width_var.get()),
            "height": int(controls.height_var.get()),
            "boundary": controls.boundary_var.get().strip() or settings.config.boundary,
            "dynamics": dynamics_cfg,
        }
    )


__all__ = ["build_runtime_config"]
