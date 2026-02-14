"""Tk runner compatibility wrapper.

Canonical implementation lives in `detm_app.ui.tk.runner.launcher`.
"""

from detm_app.ui.tk.runner.launcher import DetmTkRunner, UiRunSettings, launch_tk_ui

__all__ = ["DetmTkRunner", "UiRunSettings", "launch_tk_ui"]
