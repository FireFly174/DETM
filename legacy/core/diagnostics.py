# core/diagnostics.py
from __future__ import annotations

import numpy as np
from collections import deque

from utils.geometry import detect_line
from utils.signal import phase_from_peaks, local_phase_via_quadrature


class Diagnostics:
    def __init__(self, st, cfg, logger=None):
        self.st = st
        self.cfg = cfg
        self.logger = logger

        W = int(cfg.W)

        self.t_buf = deque(maxlen=W)
        self.A_buf = deque(maxlen=W)
        self.P_buf = deque(maxlen=W)  # сигнал для периода (локальный)
        self.tau_mean_buf = deque(maxlen=W)

        self.xline_buf = deque(maxlen=W)
        self.Eobj_buf = deque(maxlen=W)
        self.Sobj_buf = deque(maxlen=W)
        self.mu_bar_buf = deque(maxlen=W)

        self.phi_buf = deque(maxlen=W)
        self.T_buf = deque(maxlen=W)

        # viz contract: last_anchors must be [((y,x), w), ...]
        self.last_anchors = []
        self.best_anchor_xy_buf = deque(maxlen=W)

        # probes for freeze stats
        self.probe_pts = None
        self.probe_bufs = None

        self.freeze_mean_buf = deque(maxlen=W)
        self.freeze_min_buf = deque(maxlen=W)
        self.locked_frac_buf = deque(maxlen=W)

        # A3 placeholders (viz-safe)
        self.a3_r_centers = None
        self.a3_plv_profile = None
        self.a3_var_profile = None

        # internal
        self._frame = 0
        self._last_peaks = []
        self._last_logged_frame = -10**9

        # seed buffers to avoid empty access
        self.best_anchor_xy_buf.append((-1, -1))
        self.T_buf.append(np.nan)
        self.phi_buf.append(np.nan)
        self.freeze_mean_buf.append(np.nan)
        self.freeze_min_buf.append(np.nan)
        self.locked_frac_buf.append(np.nan)
        self.xline_buf.append(np.nan)

    def _init_probes_if_needed(self, best_ij):
        if self.probe_pts is not None and self.probe_bufs is not None:
            return

        step = int(self.cfg.probe_step)
        x0 = int(self.cfg.probe_x_from)
        x1 = int(self.cfg.probe_x_to)
        x1 = min(x1, self.st.N - 1)

        bi, bj = int(best_ij[0]), int(best_ij[1])
        # vertical band at column bj
        pts = []
        for i in range(x0, x1 + 1, step):
            pts.append((i, bj))
        self.probe_pts = pts
        self.probe_bufs = [deque(maxlen=int(self.cfg.W)) for _ in pts]

    def _maybe_log(self):
        if self.logger is None:
            return
        log_every = int(getattr(self.cfg, "log_every", 0))
        if log_every <= 0:
            return
        if (self._frame - self._last_logged_frame) < log_every:
            return
        self._last_logged_frame = self._frame
        self.log_row(force=True)  # <-- ВОТ ЭТО ДОБАВЬ

    def log_row(self, force: bool = False):
        """
        Записать одну строку в timeseries.
        `force=True` нужен для совместимости с Engine/batch.
        """
        if self.logger is None:
            return

        n_peaks = 0
        try:
            n_peaks = int(len(self._last_peaks)) if self._last_peaks is not None else 0
        except Exception:
            n_peaks = 0

        row = dict(
            t_global=float(getattr(self.st, "t_global", self._frame)),

            # то, что рисуется на графике T/P/A
            A=float(self.A_buf[-1]) if len(self.A_buf) else np.nan,
            T=float(self.T_buf[-1]) if len(self.T_buf) else np.nan,
            P=float(self.P_buf[-1]) if len(self.P_buf) else np.nan,  # <-- ДОБАВИТЬ
            n_peaks=n_peaks,  # <-- ДОБАВИТЬ

            # остальная диагностика
            x_line=float(self.xline_buf[-1]) if len(self.xline_buf) else np.nan,
            E_obj=float(self.Eobj_buf[-1]) if len(self.Eobj_buf) else np.nan,
            S_obj=float(self.Sobj_buf[-1]) if len(self.Sobj_buf) else np.nan,
            tau_mean=float(self.tau_mean_buf[-1]) if len(self.tau_mean_buf) else np.nan,
            mu_bar=float(self.mu_bar_buf[-1]) if len(self.mu_bar_buf) else np.nan,
            freeze_mean=float(self.freeze_mean_buf[-1]) if len(self.freeze_mean_buf) else np.nan,
            locked_frac=float(self.locked_frac_buf[-1]) if len(self.locked_frac_buf) else np.nan,
        )
        self.logger.write_row(row)

    def update(self, diag_stride: int = 1):

        self._frame += 1
        st = self.st
        t = float(getattr(st, "t_global", self._frame))

        # cheap metrics
        tau_mean = float(np.mean(st.tau)) if hasattr(st, "tau") else np.nan
        A = float(np.sqrt(np.mean(st.Jx**2 + st.Jy**2)))

        mu_bar = float(getattr(st, "mu_bar", np.nan))

        # object metrics: compute from detected line mask / band
        E_obj = np.nan
        S_obj = np.nan
        # line detect (robust)
        E_level = float(getattr(st, "E_level", np.nan))
        mask, x_line = None, None
        try:
            mask, x_line = detect_line(st.E, E_level, p_top=float(self.cfg.line_top_p), delta=self.cfg.line_delta)
        except TypeError:
            try:
                mask, x_line = detect_line(st.E, E_level)
            except Exception:
                mask, x_line = None, None
        # --- compute object metrics ---
        if isinstance(mask, np.ndarray) and mask.any():
            # object = high-energy mask
            E_obj = float(np.mean(st.E[mask]))
            # st.S существует и заполняется в model.step()
            S_obj = float(np.mean(st.S[mask])) if hasattr(st, "S") else np.nan
        else:
            E_obj = np.nan
            S_obj = np.nan

        # optionally persist to state for other modules
        st.E_obj = E_obj
        st.S_obj = S_obj
        self.t_buf.append(t)
        self.tau_mean_buf.append(tau_mean)
        self.A_buf.append(A)
        self.Eobj_buf.append(E_obj)
        self.Sobj_buf.append(S_obj)
        self.mu_bar_buf.append(mu_bar)
        self.xline_buf.append(float(x_line) if x_line is not None else np.nan)

        # anchors (for viz)
        self.last_anchors = []
        best_ij = self.best_anchor_xy_buf[-1] if len(self.best_anchor_xy_buf) else (-1, -1)
        if isinstance(mask, np.ndarray) and mask.any():
            wmap = st.E * mask
            iy, ix = np.unravel_index(int(np.argmax(wmap)), wmap.shape)
            best_ij = (int(iy), int(ix))
            self.last_anchors = [((int(iy), int(ix)), 1.0)]
        self.best_anchor_xy_buf.append(best_ij)
        # локальная проба в самой точке якоря (или рядом, если якорь -1)
        pi, pj = best_ij
        E = st.E
        N = st.N

        if pi < 0 or pj < 0:
            pi, pj = N // 2, N // 2

        r_in = 2
        r_out = 5  # кольцо 2..4

        vals = []
        for di in range(-r_out, r_out + 1):
            for dj in range(-r_out, r_out + 1):
                rr = abs(di) + abs(dj)  # "манхэттен" радиус проще и быстрее
                if rr < r_in or rr >= r_out:
                    continue
                ii = (pi + di) % N
                jj = (pj + dj) % N
                vals.append(float(E[ii, jj]))

        if len(vals) >= 6:
            P = float(np.std(vals))  # ключ: std на кольце
        else:
            P = float(E[pi, pj])

        self.P_buf.append(P)
        # probes
        self._init_probes_if_needed(best_ij)
        if self.probe_pts is not None and self.probe_bufs is not None:
            for k, (i, j) in enumerate(self.probe_pts):
                self.probe_bufs[k].append(float(st.E[i, j]))

        # heavy stride
        if diag_stride is not None and int(diag_stride) > 1:
            if (self._frame % int(diag_stride)) != 0:
                self._maybe_log()
                return

        # --- period from signal: локальная проба у якоря ---
        if len(self.P_buf) >= int(self.cfg.Wmin):
            t_arr = np.asarray(self.t_buf, float)
            sig = np.asarray(self.P_buf, float)

            phi, T_inst, peaks = phase_from_peaks(
                sig, t_arr,
                min_period=int(self.cfg.peak_min_period),
                max_period=int(self.cfg.peak_max_period),
                smooth_win=int(self.cfg.peak_smooth_win),
                prominence=float(self.cfg.peak_prominence),
            )
            self._last_peaks = peaks if peaks is not None else []

            if phi is None or T_inst is None or not np.isfinite(T_inst[-1]):
                self.phi_buf.append(np.nan)
                self.T_buf.append(np.nan)
            else:
                self.phi_buf.append(float(phi[-1]) if np.isfinite(phi[-1]) else np.nan)
                self.T_buf.append(float(T_inst[-1]))
        else:
            self.phi_buf.append(np.nan)
            self.T_buf.append(np.nan)

        # --- freeze stats (optional; stays NaN until enough phi and probes) ---
        self._update_freeze()

        # log
        self._maybe_log()

    def _update_freeze(self):
        if self.probe_pts is None or self.probe_bufs is None:
            self.freeze_mean_buf.append(np.nan)
            self.freeze_min_buf.append(np.nan)
            self.locked_frac_buf.append(np.nan)
            return

        win = int(self.cfg.quad_win)
        phi_g = np.asarray(list(self.phi_buf), float)
        if phi_g.size < win or not np.isfinite(phi_g[-1]):
            self.freeze_mean_buf.append(np.nan)
            self.freeze_min_buf.append(np.nan)
            self.locked_frac_buf.append(np.nan)
            return
        phi_g = phi_g[-win:]

        vars_ = []
        for buf in self.probe_bufs:
            sig = np.asarray(list(buf), float)
            if sig.size < win:
                continue
            sig = sig[-win:]
            _, plv, var = local_phase_via_quadrature(sig, phi_g, win=win)
            if np.isfinite(var):
                vars_.append(float(var))

        if len(vars_) == 0:
            self.freeze_mean_buf.append(np.nan)
            self.freeze_min_buf.append(np.nan)
            self.locked_frac_buf.append(np.nan)
            return

        v = np.asarray(vars_, float)
        self.freeze_mean_buf.append(float(np.mean(v)))
        self.freeze_min_buf.append(float(np.min(v)))
        self.locked_frac_buf.append(float(np.mean(v <= float(self.cfg.freeze_thr))))
