"""Runtime action flow for Tk runner launcher."""

from __future__ import annotations

from typing import Any, Callable


class TkRuntimeActionFlow:
    def __init__(
        self,
        *,
        root: Any,
        settings: Any,
        runner: Any,
        status_var: Any,
        ui_mode_var: Any,
        interactive_buttons_frame: Any,
        batch_flow: Any,
        viz_flow: Any,
        apply_settings: Callable[[bool], None],
        show_viz_view: Callable[[str], None],
    ) -> None:
        self._root = root
        self._settings = settings
        self._runner = runner
        self._status_var = status_var
        self._ui_mode_var = ui_mode_var
        self._interactive_buttons_frame = interactive_buttons_frame
        self._batch_flow = batch_flow
        self._viz_flow = viz_flow
        self._apply_settings = apply_settings
        self._show_viz_view = show_viz_view

    def update_status(self) -> None:
        state = self._runner.state
        signature = self._runner.last_observables
        dynamics = self._settings.config.dynamics
        learning = self._runner.learning_status_compact(max_len=120)
        requested_backend = f"{self._settings.config.backend}/{self._settings.config.device}"
        runtime_backend = (
            str(self._runner.runtime_backend_label())
            if hasattr(self._runner, "runtime_backend_label")
            else str(requested_backend)
        )
        backend_text = runtime_backend
        if runtime_backend != requested_backend:
            backend_text = f"{runtime_backend} (requested={requested_backend})"
        self._status_var.set(
            f"tick={state.step_count}  sig0..3={signature[:4]}  "
            f"backend={backend_text}  "
            f"boundary={self._settings.config.boundary}  a,b,k,g,t="
            f"[{dynamics.alpha:.3g},{dynamics.beta:.3g},{dynamics.kappa:.3g},{dynamics.gamma:.3g},{dynamics.lambda_t:.3g}]"
            f"  {learning}"
        )

    def _tick(self) -> None:
        if self._runner.is_running():
            self._runner.step_once()
            self.update_status()
            self._viz_flow.update_embedded()
            self._viz_flow.update_tcp()
            self._root.after(max(1, self._settings.tick_interval_ms), self._tick)

    def on_reset(self) -> None:
        self._apply_settings(True)
        self.update_status()
        self._viz_flow.update_embedded(force=True)
        self._viz_flow.update_tcp()

    def on_step(self) -> None:
        self._apply_settings(False)
        self._runner.step_once()
        self.update_status()
        self._viz_flow.update_embedded(force=True)
        self._viz_flow.update_tcp()

    def on_run_toggle(self) -> None:
        self._apply_settings(False)
        if self._runner.is_running():
            self._runner.stop()
        else:
            self._runner.start()
            self._tick()

    def on_mode_change(self, *_args: object) -> None:
        mode = str(self._ui_mode_var.get()).strip().lower()
        if mode == "batch":
            self._runner.stop()
            self._interactive_buttons_frame.grid_remove()
            self._batch_flow.frame.grid()
            self._show_viz_view("log")
        else:
            self._batch_flow.frame.grid_remove()
            self._interactive_buttons_frame.grid()
            self._show_viz_view("viz")
            self._viz_flow.update_embedded(force=True)
            self._viz_flow.update_tcp()

    def on_close(self) -> None:
        self._batch_flow.close()
        self._viz_flow.close()
        self._runner.close()
        self._root.destroy()


__all__ = ["TkRuntimeActionFlow"]
