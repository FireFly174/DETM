"""Runtime config assembly helpers for Tk settings flow."""

from __future__ import annotations

from typing import Any

from detm.runtime.config import DETMConfig
from detm_app.ui.tk.runner.flow.controls.model import TkControlVars


def _parse_runtime_event_types(raw: object) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    if text == "*":
        return ["*"]
    out: list[str] = []
    for chunk in text.split(","):
        token = str(chunk).strip()
        if token:
            out.append(token)
    return out


def build_runtime_config(*, settings: Any, controls: TkControlVars) -> DETMConfig:
    base = settings.config.to_dict()
    dynamics_cfg = dict(base.get("dynamics", {}))
    level_policy_cfg = dict(base.get("level_policy", {}))
    dynamics_cfg.update(
        {
            "alpha": float(controls.alpha_var.get()),
            "beta": float(controls.beta_var.get()),
            "kappa": float(controls.kappa_var.get()),
            "gamma": float(controls.gamma_var.get()),
            "lambda_t": float(controls.lambda_t_var.get()),
        }
    )
    level_policy_cfg.update(
        {
            "allow_refinement": bool(controls.learn_refinement_var.get()),
            "runtime_adaptive_signal_event_types": _parse_runtime_event_types(
                controls.learn_runtime_events_var.get()
            ),
            "runtime_adaptive_hold_ticks": max(0, int(controls.learn_adaptive_hold_var.get())),
            "anti_goodhart_enabled": bool(controls.learn_anti_goodhart_var.get()),
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
            "level_policy": level_policy_cfg,
        }
    )


__all__ = ["build_runtime_config"]
