# core/engine.py
from __future__ import annotations
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class Engine:
    def __init__(self, model, diag, viz=None, logger=None, interval_ms: int = 60):
        self.model = model
        self.diag = diag
        self.viz = viz
        self.logger = logger

        self.speed = 25
        self.speed_min = 1
        self.speed_max = 50
        self.paused = True

        self._interval_ms = interval_ms
        self.anim = None

        # Connect UI only if we actually have a visualizer/figure
        if self.viz is not None:
            if not hasattr(self.viz, "fig"):
                raise AttributeError("viz object must have .fig attribute")
            self.viz.fig.canvas.mpl_connect("key_press_event", self.on_key)

            # Animation only makes sense in viz mode
            self.anim = FuncAnimation(
                self.viz.fig,
                self._frame,
                interval=interval_ms,
                blit=False,
                cache_frame_data=False,
            )

    def on_key(self, event):
        k = event.key
        if k in (" ", "space"):
            self.paused = not self.paused
        elif k in ("[", "-", "down"):
            self.speed = max(self.speed_min, self.speed - 1)
        elif k in ("]", "=", "up"):
            self.speed = min(self.speed_max, self.speed + 1)
        elif k in ("r", "R"):
            self.speed = 1
            self.paused = False
        elif k in ("p", "P"):
            if self.logger is not None and self.viz is not None:
                path = self.logger.save_figure(self.viz.fig, step_tag=f"t{int(self.model.st.t_global)}")
                print(f"[saved] {path}")
        elif k in ("l", "L"):
            if self.diag is not None:
                # Diagnostics supports force=True in your project
                self.diag.log_row(force=True)
                print("[log] forced row")
        elif k in ("n", "N"):
            # new segment
            if self.logger is not None:
                self.logger.bump_segment(t_global=self.model.st.t_global)
                print(f"[segment] segment_id={self.logger.segment_id} at t_global={self.model.st.t_global}")
    def _step_sim(self, n_steps: int = 1):
        # 1) шагаем физику n_steps раз
        for _ in range(int(n_steps)):
            self.model.step()
            # E = self.model.st.E
            # Jx = self.model.st.Jx
            # print("tg", self.model.st.t_global,
            #       "E[min,max,std]", float(E.min()), float(E.max()), float(E.std()),
            #       "Jnorm", float(np.max(np.hypot(Jx, self.model.st.Jy))))

        # 2) если модель умеет sync (torch->numpy mirror) — делаем один раз на кадр
        if hasattr(self.model, "sync"):
            self.model.sync()

        # 3) диагностику тоже делаем один раз на кадр
        if self.diag is not None:
            self.diag.update()

            # 4) запись полей (один раз на кадр)
        if self.logger is not None:
            try:
                tg = float(getattr(self.model.st, "t_global", float("nan")))
                # либо точечно E:
                if hasattr(self.logger, "record_E"):
                    self.logger.record_E(self.model.st.E, t_global=tg)
                # либо сразу набор полей:
                if hasattr(self.logger, "record_fields_from_state"):
                    self.logger.record_fields_from_state(self.model.st)
            except Exception as e:
                print("[engine] field record failed:", repr(e))

    # def _step_sim(self, n_steps: int = 1):
    #     """Advance simulation by n_steps with diagnostics + optional field logging."""
    #     for _ in range(int(n_steps)):
    #         self.model.step()
    #         if self.diag is not None:
    #             self.diag.update()
    #         # 2) если модель умеет sync (torch->numpy mirror) — делаем один раз на кадр
    #         if hasattr(self.model, "sync"):
    #             self.model.sync()
    #         # --- field history logging (E[t,:,:]) ---
    #         if self.logger is not None and hasattr(self.logger, "record_E"):
    #             try:
    #                 tg = float(getattr(self.model.st, "t_global", float("nan")))
    #                 self.logger.record_E(self.model.st.E, t_global=tg)
    #             except Exception as e:
    #                 print("[engine] record_E failed:", repr(e))

    def _frame(self, _):
        try:
            if not self.paused:
                self._step_sim(self.speed)

            if self.viz is not None:
                return self.viz.update(speed=self.speed, paused=self.paused)
            return None
        except Exception as e:
            print("[engine] EXCEPTION in _frame:", repr(e))
            raise

    def run(self, max_steps: int | None = None):
        """
        Run engine.
        - If viz is present: interactive matplotlib loop.
        - If viz is None: headless loop for batch runs.
        """
        try:
            if self.viz is None:
                # Headless batch mode
                if max_steps is None:
                    raise ValueError("max_steps must be provided in headless (batch) mode")
                for _ in range(int(max_steps)):
                    self._step_sim(1)
                return

            # Visualization mode
            plt.tight_layout()
            plt.show()

        finally:
            if self.logger is not None:
                self.logger.close()
