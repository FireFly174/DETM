"""Tk UI adapters."""

from detm_app.ui.tk.panel import DetmVizPanel, VizFrame
from detm_app.ui.tk.runner import DetmTkRunner, UiRunSettings, launch_tk_ui
from detm_app.config.tooltips import load_tooltips_from_config_default
from detm_app.ui.tk.tooltips import Tooltip, attach_tooltip

__all__ = [
    "DetmTkRunner",
    "DetmVizPanel",
    "Tooltip",
    "UiRunSettings",
    "VizFrame",
    "attach_tooltip",
    "launch_tk_ui",
    "load_tooltips_from_config_default",
]
