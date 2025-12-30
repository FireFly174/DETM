# viz/visualizer.py
import numpy as np
import matplotlib.pyplot as plt


class Visualizer:
    def __init__(self, st, diag, viz_cfg, diag_cfg):
        self.st = st
        # display mode:
        # 1 = absolute E
        # 2 = dE = E - mean(E)
        # 3 = grad magnitude |∇E|
        self.display_mode = 1

        # deps
        self.diag = diag
        self.viz_cfg = viz_cfg
        self.diag_cfg = diag_cfg

        # --- quiver controls ---
        # quiver_step:
        #   >0  -> draw quiver on subgrid
        #   <=0 -> disable quiver
        self.q_step = int(getattr(viz_cfg, "quiver_step", 1))
        self.q_scale = float(getattr(viz_cfg, "quiver_scale", 10.0))
        # explicit toggle
        self.show_quiver = bool(getattr(viz_cfg, "show_quiver", True))

        self.auto_clim = bool(getattr(viz_cfg, "auto_clim", True))
        self.hist_bins = int(getattr(viz_cfg, "hist_bins", 25))

        # SINGLE figure
        self.fig = plt.figure(figsize=(12, 7))
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

        # gs = self.fig.add_gridspec(
        #     2, 3,
        #     height_ratios=[2.5, 1.0],
        #     width_ratios=[2.0, 1.0, 1.0]
        # )

        gs = self.fig.add_gridspec(
            3, 3,
            height_ratios=[2.5, 1.0, 0.35],
            width_ratios=[2.0, 1.0, 1.0]
        )
        self.ax_status = self.fig.add_subplot(gs[2, :])
        self.ax_status.axis("off")
        self.ax_main = self.fig.add_subplot(gs[0, 0])
        self.ax_hist = self.fig.add_subplot(gs[0, 1])
        self.ax_T = self.fig.add_subplot(gs[0, 2])
        self.ax_freeze = self.fig.add_subplot(gs[1, 0])
        self.ax_a3 = self.fig.add_subplot(gs[1, 1:])

        self.im = self.ax_main.imshow(st.E, origin="lower", interpolation="nearest")
        self.ax_main.set_title("E field")

        # Create quiver only if enabled
        self.qv = None
        self._maybe_create_quiver()

        self.sc = self.ax_main.scatter([], [], s=[], marker="o")

        self.ax_hist.set_title("E histogram")
        self._hist_inited = False
        self._hist_edges = np.linspace(0.0, 1.0, self.hist_bins + 1)
        self._hist_bars = None

        self.ax_T.set_title("T(t) and P(t)")
        self.line_T, = self.ax_T.plot([], [], lw=1.5, label="T(t)")

        self.ax_P = self.ax_T.twinx()
        self.line_P, = self.ax_P.plot([], [], lw=1.2, linestyle="--", label="P(t)")
        self.line_A, = self.ax_P.plot([], [], lw=1.0, alpha=0.7, linestyle=":", label="A(t)")

        self.ax_T.legend(loc="upper left")
        self.ax_P.legend(loc="upper right")

        self.ax_freeze.set_title("freeze stats")
        self.line_freeze_mean, = self.ax_freeze.plot([], [], lw=1.5, label="freeze_mean")
        self.line_locked, = self.ax_freeze.plot([], [], lw=1.5, label="locked_frac")
        self.ax_freeze.legend(loc="upper right")

        self.ax_a3.set_title("A3 radial coherence (PLV / Var)")
        self.line_a3_plv, = self.ax_a3.plot([], [], lw=1.5, label="PLV(r)")
        self.line_a3_var, = self.ax_a3.plot([], [], lw=1.5, label="Var(r)")
        self.ax_a3.legend(loc="upper right")

        self.status_text = self.ax_status.text(
            0.01, 0.5, "",
            transform=self.ax_status.transAxes,
            ha="left", va="center",
            color="w", fontsize=9,
            bbox=dict(facecolor="black", alpha=0.35, edgecolor="none", pad=2.0)
        )

        self.fig.tight_layout()

    # -----------------------
    # Quiver helpers
    # -----------------------
    def _quiver_enabled(self) -> bool:
        return bool(self.show_quiver) and int(self.q_step) > 0

    def _maybe_create_quiver(self):
        """Create quiver if enabled; otherwise ensure it's removed."""
        # remove old if exists
        if self.qv is not None:
            try:
                self.qv.remove()
            except Exception:
                pass
            self.qv = None

        if not self._quiver_enabled():
            return

        st = self.st
        step = int(self.q_step)
        # note: mesh in display coords (x=col, y=row)
        Y, X = np.mgrid[0:st.N:step, 0:st.N:step]
        self.qv = self.ax_main.quiver(
            X, Y,
            st.Jx[::step, ::step],
            st.Jy[::step, ::step],
            scale=self.q_scale
        )

    def _update_quiver(self):
        """Update quiver U,V if it exists and enabled."""
        if self.qv is None or not self._quiver_enabled():
            return
        st = self.st
        step = int(self.q_step)

        # Normalize to avoid tiny/huge arrows; keep direction field.
        norm = float(np.max(np.hypot(st.Jx, st.Jy)))
        if not np.isfinite(norm) or norm <= 0.0:
            norm = 1.0
        self.qv.set_UVC(
            st.Jx[::step, ::step] / norm,
            st.Jy[::step, ::step] / norm
        )

    # -----------------------
    # Other helpers
    # -----------------------
    def _update_hist(self):
        E = self.st.E.ravel()
        counts, _ = np.histogram(E, bins=self._hist_edges)
        counts = counts.astype(float)

        if not self._hist_inited:
            centers = 0.5 * (self._hist_edges[:-1] + self._hist_edges[1:])
            width = (self._hist_edges[1] - self._hist_edges[0]) * 0.9
            self._hist_bars = self.ax_hist.bar(centers, counts, width=width)
            self.ax_hist.set_xlim(0.0, 1.0)
            self._hist_inited = True
        else:
            for rect, h in zip(self._hist_bars, counts):
                rect.set_height(float(h))

        ymax = float(np.max(counts)) if len(counts) else 1.0
        if ymax < 1.0:
            ymax = 1.0
        self.ax_hist.set_ylim(0.0, ymax * 1.05)

    def _on_key(self, event):
        if event.key == "1":
            self.display_mode = 1
        elif event.key == "2":
            self.display_mode = 2
        elif event.key == "3":
            self.display_mode = 3
        elif event.key == "v":
            # toggle quiver on/off
            self.show_quiver = not self.show_quiver
            self._maybe_create_quiver()

    def update(self, speed=1, paused=False):
        st = self.st
        diag = self.diag

        # --- main image (mode switch) ---
        E = st.E

        if self.display_mode == 1:
            Z = E
            mode_name = "E"
        elif self.display_mode == 2:
            Z = E - float(np.mean(E))
            mode_name = "dE"
        else:
            gy, gx = np.gradient(E)
            Z = np.hypot(gx, gy)
            mode_name = "|gradE|"

        self.im.set_data(Z)

        Emin = float(np.min(E))
        Emax = float(np.max(E))
        Erng = Emax - Emin
        Estd = float(np.std(E))

        if self.auto_clim:
            vmin = float(np.min(Z))
            vmax = float(np.max(Z))
            if vmax - vmin < 1e-12:
                eps = 1e-6 if abs(vmin) < 1e-3 else 1e-3 * abs(vmin)
                vmax = vmin + eps
            self.im.set_clim(vmin, vmax)

        # --- quiver update (only if enabled) ---
        self._update_quiver()

        # --- anchors scatter ---
        anchors = getattr(diag, "last_anchors", []) or []
        if len(anchors) > 0:
            pts = np.array([a[0] for a in anchors], dtype=float)
            sizes = np.array([60.0 + 240.0 * float(a[1]) for a in anchors], dtype=float)
            if pts.ndim == 2 and pts.shape[1] == 2:
                ys, xs = pts[:, 0], pts[:, 1]
                self.sc.set_offsets(np.c_[xs, ys])
                self.sc.set_sizes(sizes)
            else:
                self.sc.set_offsets(np.empty((0, 2)))
                self.sc.set_sizes(np.empty((0,), dtype=float))
        else:
            self.sc.set_offsets(np.empty((0, 2)))
            self.sc.set_sizes(np.empty((0,), dtype=float))

        # histogram
        self._update_hist()

        # DEBUG status
        tau_mean = float(np.mean(st.tau)) if hasattr(st, "tau") else float("nan")

        A_last = np.nan
        Aw_min = np.nan
        Aw_max = np.nan
        if hasattr(diag, "A_buf") and len(diag.A_buf) > 0:
            aarr = np.asarray(diag.A_buf, float)
            A_last = float(aarr[-1])
            if np.isfinite(aarr).any():
                Aw_min = float(np.nanmin(aarr))
                Aw_max = float(np.nanmax(aarr))

        T_last = np.nan
        if hasattr(diag, "T_buf") and len(diag.T_buf) > 0:
            T_last = float(np.asarray(diag.T_buf, float)[-1])

        P_last = np.nan
        if hasattr(diag, "P_buf") and len(diag.P_buf) > 0:
            P_last = float(np.asarray(diag.P_buf, float)[-1])

        Pmin = np.nan
        Pmax = np.nan
        if hasattr(diag, "P_buf") and len(diag.P_buf) > 5:
            parr = np.asarray(diag.P_buf, float)
            if np.isfinite(parr).any():
                Pmin = float(np.nanmin(parr))
                Pmax = float(np.nanmax(parr))

        n_peaks = 0
        if hasattr(diag, "_last_peaks") and diag._last_peaks is not None:
            try:
                n_peaks = int(len(diag._last_peaks))
            except Exception:
                n_peaks = 0

        q_state = "ON" if self._quiver_enabled() else "OFF"
        self.status_text.set_text(
            f"[1/2/3 mode={mode_name}]  speed={speed} paused={paused} tau_mean={tau_mean:.3f}  quiver={q_state}\n"
            f"E[min,max]={Emin:.3e},{Emax:.3e}  std={Estd:.3e}  range={Erng:.3e}\n"
            f"A_last={A_last:.3e}  T_last={T_last if np.isfinite(T_last) else np.nan}  peaks={n_peaks}\n"
            f"P_last={P_last:.3e}  P[min,max]=[{Pmin:.3e},{Pmax:.3e}]"
        )

        # --- T(t) (ALIGN lengths!) ---
        t_buf = np.asarray(list(getattr(diag, "t_buf", [])), float)
        T_buf = np.asarray(list(getattr(diag, "T_buf", [])), float)
        P_buf = np.asarray(list(getattr(diag, "P_buf", [])), float)
        A_buf = np.asarray(list(getattr(diag, "A_buf", [])), float)

        L = min(len(t_buf), len(T_buf), len(P_buf), len(A_buf))
        if L >= 2:
            tt = t_buf[-L:]
            TT = T_buf[-L:]
            PP = P_buf[-L:]
            AA = A_buf[-L:]

            # 1) T(t)
            mT = np.isfinite(tt) & np.isfinite(TT)
            if mT.sum() >= 2:
                self.line_T.set_data(tt[mT], TT[mT])
                xmin = float(np.min(tt[mT]))
                xmax = float(np.max(tt[mT]))
                if abs(xmax - xmin) < 1e-12:
                    xmax = xmin + 1.0
                self.ax_T.set_xlim(xmin, xmax)

                ymin = float(np.min(TT[mT]))
                ymax = float(np.max(TT[mT]))
                if abs(ymax - ymin) < 1e-12:
                    ymax = ymin + 1.0
                self.ax_T.set_ylim(
                    ymin - 0.05 * (ymax - ymin),
                    ymax + 0.05 * (ymax - ymin),
                )
            else:
                self.line_T.set_data([], [])

            # 2) P(t)
            mP = np.isfinite(tt) & np.isfinite(PP)
            if mP.sum() >= 2:
                self.line_P.set_data(tt[mP], PP[mP])
                pmin = float(np.min(PP[mP]))
                pmax = float(np.max(PP[mP]))
                if abs(pmax - pmin) < 1e-12:
                    pmax = pmin + 1e-6
                self.ax_P.set_ylim(
                    pmin - 0.05 * (pmax - pmin),
                    pmax + 0.05 * (pmax - pmin),
                )
            else:
                self.line_P.set_data([], [])

            # 3) A(t) — on right axis; do not rescale ylim by A
            mA = np.isfinite(tt) & np.isfinite(AA)
            if mA.sum() >= 2:
                self.line_A.set_data(tt[mA], AA[mA])
            else:
                self.line_A.set_data([], [])

            if (not mT.any()) and np.isfinite(tt).any():
                xmin = float(np.nanmin(tt))
                xmax = float(np.nanmax(tt))
                if abs(xmax - xmin) < 1e-12:
                    xmax = xmin + 1.0
                self.ax_T.set_xlim(xmin, xmax)
        else:
            self.line_T.set_data([], [])
            self.line_P.set_data([], [])
            self.line_A.set_data([], [])

        # --- freeze stats (ALIGN lengths + safe ymax) ---
        fm = np.asarray(list(getattr(diag, "freeze_mean_buf", [])), float)
        lf = np.asarray(list(getattr(diag, "locked_frac_buf", [])), float)
        L2 = min(len(t_buf), len(fm), len(lf))
        if L2 >= 2:
            tt2 = t_buf[-L2:]
            fm2 = fm[-L2:]
            lf2 = lf[-L2:]
            self.line_freeze_mean.set_data(tt2, fm2)
            self.line_locked.set_data(tt2, lf2)

            xmin = float(np.nanmin(tt2)) if np.isfinite(tt2).any() else 0.0
            xmax = float(np.nanmax(tt2)) if np.isfinite(tt2).any() else 1.0
            if abs(xmax - xmin) < 1e-12:
                xmax = xmin + 1.0
            self.ax_freeze.set_xlim(xmin, xmax)

            vals = np.array([np.nanmax(fm2), np.nanmax(lf2)], dtype=float)
            if not np.isfinite(vals).any():
                ymax = 1.0
            else:
                ymax = float(np.nanmax(np.append(vals[np.isfinite(vals)], 1.0)))
            self.ax_freeze.set_ylim(0.0, ymax * 1.05)
        else:
            self.line_freeze_mean.set_data([], [])
            self.line_locked.set_data([], [])
            self.ax_freeze.set_ylim(0.0, 1.0)

        # --- A3 (optional) ---
        r = getattr(diag, "a3_r_centers", None)
        plv = getattr(diag, "a3_plv_profile", None)
        var = getattr(diag, "a3_var_profile", None)
        if r is not None and plv is not None and var is not None:
            r = np.asarray(r, float)
            plv = np.asarray(plv, float)
            var = np.asarray(var, float)
            if len(r) > 1:
                self.line_a3_plv.set_data(r, plv)
                self.line_a3_var.set_data(r, var)
        else:
            self.line_a3_plv.set_data([], [])
            self.line_a3_var.set_data([], [])

        artists = [
            self.im,
            self.sc,
            self.line_T,
            self.line_P,
            self.line_A,
            self.line_freeze_mean,
            self.line_locked,
            self.line_a3_plv,
            self.line_a3_var,
            self.status_text,
        ]
        # include quiver only if it exists
        if self.qv is not None:
            artists.insert(1, self.qv)

        return tuple(artists)
