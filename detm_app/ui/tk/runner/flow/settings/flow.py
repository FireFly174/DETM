"""Settings/config flow for Tk runner launcher."""

from __future__ import annotations

from typing import Any

from detm.runtime.config import DETMConfig
from detm_app.ui.tk.runner.flow.controls.model import TkControlVars
from detm_app.ui.tk.runner.flow.settings.apply import apply_runtime_settings, read_invariant_streams
from detm_app.ui.tk.runner.flow.settings.runtime_config import build_runtime_config


class TkSettingsFlow:
    def __init__(self, *, settings: Any, runner: Any, controls: TkControlVars) -> None:
        self._settings = settings
        self._runner = runner
        self._controls = controls

    def build_config(self) -> DETMConfig:
        return build_runtime_config(settings=self._settings, controls=self._controls)

    def read_invariant_streams(self) -> str:
        return read_invariant_streams(controls=self._controls)

    def apply(self, reset: bool) -> None:
        apply_runtime_settings(settings=self._settings, runner=self._runner, controls=self._controls, reset=reset)


__all__ = ["TkSettingsFlow"]
